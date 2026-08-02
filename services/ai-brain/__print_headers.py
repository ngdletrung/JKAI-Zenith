with open('/workspace/data/rclone/rclone.conf', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if line.strip().startswith('['):
            print(f"Line {i}: {line.strip()}")
