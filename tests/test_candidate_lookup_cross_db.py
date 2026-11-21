import pytest
import json
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InternalError, OperationalError
from models import db, User, Assessment, Credential
from services import (
    lookup_candidate,
    register_test_candidate,
    clear_test_candidates,
    verify_read_only_protection,
    find_candidate_by_id,
    find_or_sync_candidate_identity,
    create_candidate_credential
)

@pytest.fixture(autouse=True)
def cleanup_test_candidates():
    clear_test_candidates()
    yield
    clear_test_candidates()

def test_01_valid_candidate_id_returns_correct_name():
    """1. Valid Candidate ID returns correct candidate name."""
    register_test_candidate(
        candidate_id="AM-APP-000588",
        full_name="Adarsh Roy",
        email="royadarsh651@gmail.com",
        status="SHORTLISTED"
    )
    result = lookup_candidate("AM-APP-000588")
    assert result["success"] is True
    assert result["candidate"]["candidate_name"] == "Adarsh Roy"

def test_02_valid_candidate_id_returns_correct_email():
    """2. Valid Candidate ID returns correct candidate email."""
    register_test_candidate(
        candidate_id="AM-APP-000589",
        full_name="Praveen",
        email="praveenr2k25@gmail.com",
        status="SHORTLISTED"
    )
    result = lookup_candidate("AM-APP-000589")
    assert result["success"] is True
    assert result["candidate"]["candidate_email"] == "praveenr2k25@gmail.com"

def test_03_invalid_candidate_id_returns_not_found():
    """3. Invalid Candidate ID returns not-found response."""
    result = lookup_candidate("AM-APP-NONEXISTENT")
    assert result["success"] is False
    assert result["status_code"] == 404
    assert "Candidate not found" in result["message"]

def test_04_candidate_lookup_from_credential_manager(client, admin_user_id):
    """4. Candidate ID lookup works from the Credential Manager endpoint."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    register_test_candidate(
        candidate_id="AM-APP-000590",
        full_name="Rohit R",
        email="vrrohit2020@gmail.com",
        status="APPLIED"
    )

    res = client.get('/admin/candidates/lookup?candidate_id=AM-APP-000590')
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["candidate"]["candidate_id"] == "AM-APP-000590"
    assert data["candidate"]["full_name"] == "Rohit R"
    assert data["candidate"]["email"] == "vrrohit2020@gmail.com"
    assert data["candidate"]["source_system"] == "antimatrix_db"

def test_05_candidate_identity_stored_in_assessment_database(app):
    """5. Candidate identity is stored correctly in the assessment database."""
    with app.app_context():
        candidate_data = {
            "candidate_id": "AM-APP-000591",
            "candidate_name": "Satheesh Vm",
            "candidate_email": "satheeshvm230@gmail.com",
            "status": "APPLIED",
            "source_system": "antimatrix_db"
        }
        cand_user = find_or_sync_candidate_identity(candidate_data)
        db.session.commit()

        # Query assessment DB to verify persistence
        saved = User.query.filter_by(user_id="AM-APP-000591").first()
        assert saved is not None
        assert saved.full_name == "Satheesh Vm"
        assert saved.email == "satheeshvm230@gmail.com"
        assert saved.role == "CANDIDATE"
        assert saved.source_system == "antimatrix_db"

def test_06_assessment_assignment_works(client, admin_user_id, test_assessment_id):
    """6. Assessment assignment works."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    register_test_candidate(
        candidate_id="AM-APP-000592",
        full_name="Shreedharan R B",
        email="shreedharanrajaa05@gmail.com",
        status="APPLIED"
    )

    payload = {
        "candidate_id": "AM-APP-000592",
        "assessment_id": test_assessment_id
    }
    res = client.post('/admin/credentials/create',
                      data=json.dumps(payload),
                      content_type='application/json')
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["credential"]["assessment_title"] is not None

def test_07_credential_generation_works(app, test_assessment_id):
    """7. Credential generation works with 48h expiry and secure hash."""
    with app.app_context():
        register_test_candidate(
            candidate_id="AM-APP-000593",
            full_name="Mohamed Mahathir",
            email="mahathirshaheen952@gmail.com",
            status="APPLIED"
        )

        cred, cand, raw_pwd, err = create_candidate_credential(
            candidate_id="AM-APP-000593",
            assessment_id=test_assessment_id
        )
        assert err is None
        assert cred is not None
        assert cred.status == "ACTIVE"
        assert cred.effective_status == "ACTIVE"
        assert cand.check_password(raw_pwd) is True
        # Verify 48 hours validity
        duration = cred.expires_at - cred.created_at
        assert abs(duration.total_seconds() - 48 * 3600) < 5

def test_08_email_workflow_uses_fetched_email(client, app, admin_user_id, test_assessment_id):
    """8. Email workflow uses the fetched email."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    register_test_candidate(
        candidate_id="AM-APP-000594",
        full_name="Kavya S",
        email="skavya192005@gmail.com",
        status="APPLIED"
    )

    res = client.post('/admin/credentials/create',
                      data=json.dumps({'candidate_id': 'AM-APP-000594', 'assessment_id': test_assessment_id}),
                      content_type='application/json')
    assert res.status_code == 200
    cred_id = res.get_json()["credential"]["id"]

    # Dispatch email
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        res_email = client.post(f'/admin/credentials/{cred_id}/send-email',
                                data=json.dumps({'resend': False}),
                                content_type='application/json')
        assert res_email.status_code == 200
        email_data = res_email.get_json()
        assert email_data["success"] is True
        assert email_data["recipient"] == "skavya192005@gmail.com"

def test_09_10_11_read_only_rejection_of_writes():
    """9, 10, 11: Source database rejects INSERT, UPDATE, DELETE in read-only mode."""
    # Test read-only engine with SQLite in-memory or mock
    # Create an engine configured in read-only mode
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE job_applications (id INTEGER PRIMARY KEY, full_name TEXT, email TEXT);"))
        conn.commit()

    # Reconnect with read-only query simulation / mock verifying handler
    with patch('services.candidate_lookup_service.get_readonly_engine') as mock_engine:
        # Mock engine that raises InternalError on writes (exact PostgreSQL error)
        mock_conn = MagicMock()
        def mock_execute(statement, *args, **kwargs):
            sql_str = str(statement).upper()
            if any(w in sql_str for w in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE']):
                raise InternalError("cannot execute in a read-only transaction", {}, None)
            return MagicMock()
        mock_conn.execute.side_effect = mock_execute
        mock_conn.__enter__.return_value = mock_conn
        mock_engine.return_value.connect.return_value = mock_conn

        report = verify_read_only_protection()
        assert report["insert_rejected"] is True
        assert report["update_rejected"] is True
        assert report["delete_rejected"] is True
        assert report["read_only_enforced"] is True

def test_14_application_continues_working_if_source_db_unavailable(client, app, admin_user_id, test_assessment_id):
    """14. Assessment application continues working independently if source database is temporarily unavailable."""
    with app.app_context():
        # First: candidate was previously fetched and identity exists in assessment DB
        cand = User(
            user_id="AM-APP-000595",
            username="am-app-000595",
            email="sarika8407@gmail.com",
            full_name="Sarika V",
            role="CANDIDATE",
            source_system="antimatrix_db",
            is_active=True
        )
        cand.set_password("SecureTempPass123!")
        db.session.add(cand)
        db.session.commit()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user_id)
        sess['_fresh'] = True

    # Simulate external source DB completely down (OperationalError / connection failure)
    with patch('services.candidate_lookup_service.get_readonly_engine', return_value=None):
        # 1. Lookup gracefully falls back to local snapshot
        res = client.get('/admin/candidates/lookup?candidate_id=AM-APP-000595')
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["candidate"]["full_name"] == "Sarika V"

        # 2. Generating credentials for the previously cached candidate continues to work
        res_cred = client.post('/admin/credentials/create',
                               data=json.dumps({'candidate_id': 'AM-APP-000595', 'assessment_id': test_assessment_id}),
                               content_type='application/json')
        assert res_cred.status_code == 200
        assert res_cred.get_json()["success"] is True
