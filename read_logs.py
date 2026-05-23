import json

log_paths = [
    r"C:\Users\AdminPC-MMO\.gemini\antigravity\brain\288afd9c-0c78-4634-a77b-ea65623922c1\.system_generated\logs\transcript.jsonl",
    r"C:\Users\AdminPC-MMO\.gemini\antigravity\brain\3520ab2f-3b62-4611-9341-f2911be8ee46\.system_generated\logs\transcript.jsonl"
]

with open("d:\\Docker\\N8N\\log_summary.txt", "w", encoding="utf-8") as out:
    for path in log_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("type") in ["USER_INPUT", "PLANNER_RESPONSE"]:
                        content = data.get("content", "")
                        # Chỉ lấy những tin nhắn có liên quan đến các sửa đổi, hoặc tin nhắn của user
                        if data.get("source") == "USER_EXPLICIT" or any(kw in content.lower() for kw in ["đã sửa", "cập nhật", "cải tiến", "thay đổi", "tối ưu"]):
                            out.write(f"[{data.get('created_at')}] {data.get('source')}: {content[:300].replace(chr(10), ' ')}\n")
        except Exception as e:
            out.write(f"Error reading {path}: {e}\n")
