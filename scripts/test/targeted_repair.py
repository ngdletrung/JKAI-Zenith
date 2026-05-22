import os

def fix_text(text):
    result = ""
    pending_bytes = bytearray()
    
    for char in text:
        try:
            # Try to encode back to CP1252 byte
            b = char.encode('cp1252')
            pending_bytes.extend(b)
        except UnicodeEncodeError:
            # Non-CP1252 character (likely already correct UTF-8)
            if pending_bytes:
                try:
                    # Try to decode the accumulated bytes as UTF-8
                    result += pending_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    # If it's not valid UTF-8, keep as is (interpreted as CP1252)
                    result += pending_bytes.decode('cp1252', errors='replace')
                pending_bytes = bytearray()
            result += char
            
    if pending_bytes:
        try:
            result += pending_bytes.decode('utf-8')
        except UnicodeDecodeError:
            result += pending_bytes.decode('cp1252', errors='replace')
            
    return result

def fix_file(path):
    try:
        with open(path, 'rb') as f:
            content = f.read()
        
        # We assume the file is currently UTF-8
        text = content.decode('utf-8', errors='replace')
        fixed = fix_text(text)
        
        if fixed != text:
            print(f"Repairing: {path}")
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(fixed)
            return True
    except Exception as e:
        print(f"Error in {path}: {e}")
    return False

def run_repair():
    base_dir = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N")
    targets = [
        'services/ai-brain',
        'services/ai-executor',
        'services/ai-control-plane',
        'services/ai-browser',
        'services/ai-telegram',
        'services/tools/definitions',
        'services/mission-control/backend',
        'intelligence',
        'shared',
        'core'
    ]
    
    count = 0
    for target in targets:
        full_path = os.path.join(base_dir, target)
        if not os.path.exists(full_path):
            continue
            
        print(f"Scanning: {full_path}")
        if os.path.isfile(full_path):
            if fix_file(full_path): count += 1
        else:
            for root, _, files in os.walk(full_path):
                # Skip known bad dirs
                if any(d in root for d in ['.git', '__pycache__', 'node_modules', 'dist', 'tokenizer', 'data', 'venv']):
                    continue
                for file in files:
                    if file.endswith('.py') or file.endswith('.md'):
                        if fix_file(os.path.join(root, file)):
                            count += 1
    print(f"Done. Repaired {count} files.")

if __name__ == "__main__":
    run_repair()
