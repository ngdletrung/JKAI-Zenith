import subprocess
import json

RCLONE_CONFIG = "/workspace/data/rclone/rclone.conf"
cmd = ["rclone", f"--config={RCLONE_CONFIG}", "lsjson", "SharePoint:Documents"]
try:
    res = subprocess.run(cmd, capture_output=True, timeout=20)
    if res.returncode == 0:
        items = json.loads(res.stdout.decode('utf-8'))
        print("=== Documents Subfolders ===")
        for item in items:
            if item.get('IsDir'):
                print(f"Dir: '{item.get('Name')}'")
            else:
                print(f"File: '{item.get('Name')}'")
    else:
        print("Error code:", res.returncode)
        print("Stderr:", res.stderr.decode('utf-8', errors='replace'))
except Exception as e:
    print("Error:", e)
