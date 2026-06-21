import os
import re
import sys

# Ensure UTF-8 output thưa Master
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

TARGET_DIR = r"D:\Docker\JKAI\intelligence"
PATTERNS = [
    re.compile(r".*_[a-f0-9]{8}\.md$", re.IGNORECASE),
    re.compile(r".*\.bak$", re.IGNORECASE)
]

def purge_stale_files():
    print(f"[MASS-PURGE] Starting purge in: {TARGET_DIR}")
    purged_count = 0
    
    for root, dirs, files in os.walk(TARGET_DIR):
        for file in files:
            is_stale = any(pattern.match(file) for pattern in PATTERNS)
            if is_stale:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    # We print a generic message to avoid encoding issues with complex paths if reconfigure fails
                    purged_count += 1
                except Exception as e:
                    pass
                    
    print(f"\n[PURGE COMPLETE]")
    print(f"Purged {purged_count} stale files successfully thưa Master.")

if __name__ == "__main__":
    purge_stale_files()
