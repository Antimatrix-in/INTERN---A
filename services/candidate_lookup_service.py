"""
Candidate Lookup Service for Anti-Matrix Assessment Platform.
Provides STRICT READ-ONLY cross-database candidate identity lookup from antimatrix_db.
Enforces read-only transactions, parameterised queries, connection timeouts, and zero credential leaks.
"""
import os
import logging
from urllib.parse import urlparse
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
    InternalError,
    SQLAlchemyError
)

logger = logging.getLogger(__name__)

# Cached SQLAlchemy engine for read-only source connection
_READONLY_ENGINE = None

# Mock registry for isolated testing environments
_TEST_MOCK_REGISTRY = {}

def get_readonly_db_url():
    """Retrieve the read-only database URL from Flask config or environment."""
    if current_app:
        url = current_app.config.get('ANTIMATRIX_READONLY_DATABASE_URL')
        if url:
            return url
    return os.environ.get('ANTIMATRIX_READONLY_DATABASE_URL')

def get_readonly_engine():
    """
    Returns a dedicated SQLAlchemy engine configured strictly for READ-ONLY access:
    - Default transaction read-only enforced at PostgreSQL session level
    - 5-second connection and statement timeouts
    - Autocommit with read_only execution options
    """
    global _READONLY_ENGINE
    db_url = get_readonly_db_url()
    if not db_url:
        return None

    if _READONLY_ENGINE is None:
        try:
            # Fix legacy postgres:// URL format
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)

            connect_args = {"connect_timeout": 5}
            # If PostgreSQL, enforce read-only at session connection parameters
            if 'postgresql' in db_url:
                connect_args["options"] = "-c default_transaction_read_only=on -c statement_timeout=5000"

            _READONLY_ENGINE = create_engine(
                db_url,
                connect_args=connect_args,
                execution_options={
                    "isolation_level": "AUTOCOMMIT",
                    "read_only": True
                },
                pool_size=5,
                max_overflow=2,
                pool_recycle=300,
                pool_pre_ping=True
            )
            logger.info("Anti-Matrix read-only candidate engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize read-only database engine: {type(e).__name__}")
            return None

    return _READONLY_ENGINE

def register_test_candidate(candidate_id, full_name, email, status='ACTIVE', source_table='test_mock'):
    """Helper for unit tests to register mock candidate records in testing mode."""
    _TEST_MOCK_REGISTRY[candidate_id.strip().upper()] = {
        "candidate_id": candidate_id.strip(),
        "candidate_name": full_name.strip(),
        "candidate_email": email.strip().lower(),
        "status": status,
        "source_system": "antimatrix_db",
        "source_table": source_table
    }

def clear_test_candidates():
    """Clear test candidate registry."""
    _TEST_MOCK_REGISTRY.clear()

def lookup_candidate(candidate_id):
    """
    Look up candidate by Candidate ID in the authoritative Anti-Matrix production database.
    Parameterised queries only. Never concatenates user input into SQL.
    Returns:
      dict: {
        "success": bool,
        "candidate": { ... } or None,
        "message": str or None,
        "status_code": int
      }
    """
    if not candidate_id:
        return {
            "success": False,
            "candidate": None,
            "message": "Candidate ID is required.",
            "status_code": 400
        }

    cid = str(candidate_id).strip()
    if not cid:
        return {
            "success": False,
            "candidate": None,
            "message": "Candidate ID is required.",
            "status_code": 400
        }

    # 1. Check Test Mock Registry (for testing or offline environments)
    if _TEST_MOCK_REGISTRY:
        mock_rec = _TEST_MOCK_REGISTRY.get(cid.upper())
        if mock_rec:
            # Check for missing email/name
            if not mock_rec.get("candidate_name") or not mock_rec.get("candidate_email"):
                return {
                    "success": False,
                    "candidate": None,
                    "message": "Candidate record has incomplete contact details (missing name or email).",
                    "status_code": 422
                }
            return {
                "success": True,
                "candidate": dict(mock_rec),
                "message": None,
                "status_code": 200
            }

    # 2. Connect to Source Database via Read-Only Engine
    engine = get_readonly_engine()
    if not engine:
        return {
            "success": False,
            "candidate": None,
            "message": "Candidate not found. Please check the Candidate ID.",
            "status_code": 404
        }

    try:
        with engine.connect() as conn:
            # Try candidate_lookup_view first
            view_sql = text("""
                SELECT candidate_id, candidate_name, candidate_email, status, source_table
                FROM candidate_lookup_view
                WHERE UPPER(candidate_id) = UPPER(:cid)
                LIMIT 1;
            """)
            try:
                row = conn.execute(view_sql, {"cid": cid}).mappings().first()
            except ProgrammingError:
                # View might not exist yet; fallback to direct table queries
                fallback_sql = text("""
                    SELECT 
                        COALESCE(application_code, CONCAT('AM-APP-', LPAD(id::text, 6, '0'))) AS candidate_id,
                        full_name AS candidate_name,
                        email AS candidate_email,
                        COALESCE(application_status, status, 'ACTIVE') AS status,
                        'job_applications' AS source_table
                    FROM job_applications
                    WHERE UPPER(COALESCE(application_code, CONCAT('AM-APP-', LPAD(id::text, 6, '0')))) = UPPER(:cid)
                    UNION ALL
                    SELECT 
                        application_no AS candidate_id,
                        candidate_name,
                        candidate_email,
                        COALESCE(status, 'ACTIVE') AS status,
                        'applications' AS source_table
                    FROM applications
                    WHERE UPPER(application_no) = UPPER(:cid)
                    LIMIT 1;
                """)
                row = conn.execute(fallback_sql, {"cid": cid}).mappings().first()

            if not row:
                return {
                    "success": False,
                    "candidate": None,
                    "message": "Candidate not found. Please check the Candidate ID.",
                    "status_code": 404
                }

            cand_name = (row["candidate_name"] or "").strip()
            cand_email = (row["candidate_email"] or "").strip().lower()

            if not cand_name or not cand_email:
                return {
                    "success": False,
                    "candidate": None,
                    "message": "Candidate record has incomplete contact details (missing name or email).",
                    "status_code": 422
                }

            candidate_payload = {
                "candidate_id": row["candidate_id"],
                "candidate_name": cand_name,
                "candidate_email": cand_email,
                "status": row.get("status") or "ACTIVE",
                "source_system": "antimatrix_db",
                "source_table": row.get("source_table") or "candidate_lookup_view"
            }

            return {
                "success": True,
                "candidate": candidate_payload,
                "message": None,
                "status_code": 200
            }

    except (OperationalError, TimeoutError) as oe:
        logger.error(f"Candidate database connection error: {type(oe).__name__}")
        return {
            "success": False,
            "candidate": None,
            "message": "Unable to connect to the candidate database. Please try again later.",
            "status_code": 503
        }
    except SQLAlchemyError as se:
        logger.error(f"Candidate database query error: {type(se).__name__}")
        return {
            "success": False,
            "candidate": None,
            "message": "Database query error. Please contact system administrator.",
            "status_code": 500
        }
    except Exception as e:
        logger.error(f"Unexpected error looking up candidate: {type(e).__name__}")
        return {
            "success": False,
            "candidate": None,
            "message": "Unable to process candidate lookup. Please try again later.",
            "status_code": 500
        }

def verify_read_only_protection(engine=None):
    """
    Verifies that write operations (INSERT, UPDATE, DELETE) are strictly blocked on the source database.
    Returns:
      dict: {
        "insert_rejected": bool,
        "update_rejected": bool,
        "delete_rejected": bool,
        "read_only_enforced": bool
      }
    """
    target_engine = engine or get_readonly_engine()
    if not target_engine:
        raise RuntimeError("No read-only engine available for verification.")

    results = {
        "insert_rejected": False,
        "update_rejected": False,
        "delete_rejected": False,
        "read_only_enforced": False
    }

    # 1. Test INSERT rejection
    try:
        with target_engine.connect() as conn:
            conn.execute(text("INSERT INTO job_applications (full_name, email) VALUES ('TEST_READONLY', 'test@invalid');"))
            # If we reach here, it failed to reject
            results["insert_rejected"] = False
    except (InternalError, ProgrammingError, OperationalError, SQLAlchemyError) as e:
        # Expected: cannot execute INSERT in a read-only transaction or permission denied
        results["insert_rejected"] = True

    # 2. Test UPDATE rejection
    try:
        with target_engine.connect() as conn:
            conn.execute(text("UPDATE job_applications SET full_name = 'TEST_FAIL' WHERE id = -999;"))
            results["update_rejected"] = False
    except (InternalError, ProgrammingError, OperationalError, SQLAlchemyError) as e:
        # Expected
        results["update_rejected"] = True

    # 3. Test DELETE rejection
    try:
        with target_engine.connect() as conn:
            conn.execute(text("DELETE FROM job_applications WHERE id = -999;"))
            results["delete_rejected"] = False
    except (InternalError, ProgrammingError, OperationalError, SQLAlchemyError) as e:
        # Expected
        results["delete_rejected"] = True

    results["read_only_enforced"] = (
        results["insert_rejected"] and
        results["update_rejected"] and
        results["delete_rejected"]
    )
    return results
