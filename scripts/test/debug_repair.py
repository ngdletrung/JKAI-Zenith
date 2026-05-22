import os

def fix_text(text):
    result = ""
    pending_bytes = bytearray()
    for char in text:
        try:
            pending_bytes.extend(char.encode('cp1252'))
        except UnicodeEncodeError:
            if pending_bytes:
                try:
                    result += pending_bytes.decode('utf-8')
                except:
                    result += pending_bytes.decode('cp1252', errors='replace')
                pending_bytes = bytearray()
            result += char
    if pending_bytes:
        try:
            result += pending_bytes.decode('utf-8')
        except:
            result += pending_bytes.decode('cp1252', errors='replace')
    return result

def fix_file(path):
    with open(path, 'rb') as f:
        content = f.read()
    text = content.decode('utf-8', errors='replace')
    fixed = fix_text(text)
    if fixed != text:
        print(f"Repairing: {path}")
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(fixed)
        return True
    return False

if __name__ == "__main__":
    target = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + '/services/ai-brain'
    count = 0
    for root, _, files in os.walk(target):
        for file in files:
            if file.endswith('.py'):
                if fix_file(os.path.join(root, file)):
                    count += 1
    print(f"Repaired {count} files in {target}")
