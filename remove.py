import sqlite3

ACTIVITY_DB = "activity.db"  # adjust path if needed

conn = sqlite3.connect(ACTIVITY_DB)
cur = conn.cursor()

tables_to_remove = ["users", "messages", "user_activity", "bottles", "bottle_views"]
for table in tables_to_remove:
    cur.execute(f"DROP TABLE IF EXISTS {table}")
    print(f"Dropped {table} if existed.")

conn.commit()
conn.close()
