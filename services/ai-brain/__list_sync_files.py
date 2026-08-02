import sqlite3

conn = sqlite3.connect("/workspace/intelligence/.ks_metadata.db")
conn.row_factory = sqlite3.Row

print("=== Non-Indexed SharePoint Files ===")
rows = conn.execute("SELECT rel_path, status, error_msg FROM files WHERE source_id='rclone_SharePoint' AND status != 'indexed'").fetchall()
print(f"Total non-indexed files: {len(rows)}")
for r in rows[:30]:
    print(f"Path: {r['rel_path']} | Status: {r['status']} | Error: {r['error_msg']}")
