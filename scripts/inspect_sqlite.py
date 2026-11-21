import sqlite3

conn = sqlite3.connect('instance/anti_matrix.db')
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
print("SQLite Database Inspection (instance/anti_matrix.db):")
for t in tables:
    count = cur.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]
    print(f"  Table: {t:25} -> {count} rows")
conn.close()
