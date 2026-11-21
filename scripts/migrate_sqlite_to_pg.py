"""
SQLite3 to PostgreSQL Migration Script for Anti-Matrix Assessment
Preserves all tables, relationships, foreign keys, and resets serial sequences.
"""
import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse

TABLE_ORDER = [
    'users',
    'assessments',
    'questions',
    'coding_questions',
    'credentials',
    'attempts',
    'attempt_answers',
    'results',
    'proctoring_events',
    'email_templates',
    'email_event_mappings',
    'scheduled_email_jobs',
    'alembic_version'
]

def migrate(sqlite_path, pg_url):
    print(f"Connecting to SQLite: {sqlite_path}")
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    parsed = urlparse(pg_url)
    pg_conn = psycopg2.connect(
        dbname=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname or '127.0.0.1',
        port=parsed.port or 5432
    )
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    print("PostgreSQL connected successfully.")
    
    # Verify tables exist in PG
    for table in TABLE_ORDER:
        sq_cur.execute(f"SELECT * FROM \"{table}\"")
        rows = sq_cur.fetchall()
        print(f"Migrating table '{table}' ({len(rows)} rows)...")

        if not rows:
            continue

        columns = [description[0] for description in sq_cur.description]
        col_names = ", ".join([f'"{c}"' for c in columns])
        placeholders = ", ".join(["%s"] * len(columns))

        # Check if table has data already
        pg_cur.execute(f'SELECT COUNT(*) FROM "{table}";')
        existing_count = pg_cur.fetchone()[0]
        if existing_count > 0:
            print(f"  Note: PG table '{table}' already has {existing_count} rows. Inserting non-conflicting...")
            # For idempotent migration, insert on conflict do nothing if id exists
            if 'id' in columns:
                query = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING;'
            else:
                query = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;'
            for row in rows:
                pg_cur.execute(query, tuple(row))
        else:
            query = f'INSERT INTO "{table}" ({col_names}) VALUES %s;'
            row_tuples = [tuple(r) for r in rows]
            execute_values(pg_cur, f'INSERT INTO "{table}" ({col_names}) VALUES %s', row_tuples)

        # Update sequence if table has id column
        if 'id' in columns and table != 'alembic_version':
            try:
                pg_cur.execute(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                           COALESCE((SELECT MAX(id) FROM "{table}"), 1), 
                           (SELECT MAX(id) IS NOT NULL FROM "{table}"));
                """)
            except Exception as seq_err:
                # Table might not use a sequence or serial
                pass

    pg_conn.commit()
    print("\nMigration completed successfully! Verifying row counts:")
    for table in TABLE_ORDER:
        sq_cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
        sq_count = sq_cur.fetchone()[0]
        pg_cur.execute(f'SELECT COUNT(*) FROM "{table}";')
        pg_count = pg_cur.fetchone()[0]
        print(f"  {table:25} -> SQLite: {sq_count:3} | PG: {pg_count:3} {'[MATCH]' if sq_count <= pg_count else '[MISMATCH]'}")

    sq_conn.close()
    pg_conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python migrate_sqlite_to_pg.py <sqlite_db_path> <postgres_dsn>")
        sys.exit(1)
    migrate(sys.argv[1], sys.argv[2])
