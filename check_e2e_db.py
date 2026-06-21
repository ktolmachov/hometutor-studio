import sqlite3
conn = sqlite3.connect('.e2e/user_state_e2e.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])

# Check app_kv table
try:
    kv = conn.execute("SELECT key, value FROM app_kv").fetchall()
    print('app_kv:', kv)
except Exception as e:
    print('app_kv error:', e)

conn.close()
