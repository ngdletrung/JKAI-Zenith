import os
import sys

def fix_text(text):
    try:
        # Core logic: undo UTF-8 bytes misinterpreted as CP1252
        # This is the most common corruption pattern on Windows
        return text.encode('cp1252').decode('utf-8')
    except:
        result = ""
        for char in text:
            try:
                # Try to fix character by character for mixed files
                result += char.encode('cp1252').decode('utf-8')
            except:
                result += char
        return result

def should_fix(content_bytes):
    # Detect patterns of double-encoded UTF-8 Vietnamese/Emoji
    patterns = [
        b'\xc3\xb0\xc5\xb8', # ðŸ
        b'\xc3\xa2\xc5\xbe', # âž
        b'\xc3\x84\xc2\x90', # Ä‘
        b'\xc3\x84\xc2\x91', # Ä‘
        b'\xc3\xa1\xc2\xbb', # á»
        b'\xc3\x83\xc2\xa1', # Ã¡
        b'\xc3\x83\xc2\xaa', # Ãª
        b'\xc3\x83\xc2\xb4', # Ã´
        b'\xc3\x84\x49\xc3\xa1', # ÄIá
    ]
    return any(p in content_bytes for p in patterns)

def walk_and_repair(root_dir):
    repaired_count = 0
    for root, dirs, files in os.walk(root_dir):
        if any(d in root for d in ['.git', '__pycache__', 'node_modules', 'dist', 'tokenizer', 'data', 'venv']):
            continue
            
        for file in files:
            if not (file.endswith('.py') or file.endswith('.md') or file.endswith('.json')):
                continue
            
            if 'vocab.json' in file or 'merges.txt' in file:
                continue
                
            path = os.path.join(root, file)
            try:
                with open(path, 'rb') as f:
                    content = f.read()
                
                if should_fix(content):
                    text = content.decode('utf-8', errors='replace')
                    fixed = fix_text(text)
                    
                    if fixed != text:
                        print(f"Repairing: {path}")
                        with open(path, 'w', encoding='utf-8', newline='\n') as f:
                            f.write(fixed)
                        repaired_count += 1
            except Exception as e:
                # Use a safe print without emojis
                print(f"Error in {path}: {str(e)}")
    return repaired_count

if __name__ == "__main__":
    base_dir = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N")
    # Added all likely directories
    subdirs = ['services', 'shared', 'intelligence', 'core']
    
    total_repaired = 0
    for sd in subdirs:
        target = os.path.join(base_dir, sd)
        if os.path.exists(target):
            print(f"Scanning directory: {target}")
            total_repaired += walk_and_repair(target)
            
    print(f"Global Neural Repair Complete. Total files repaired: {total_repaired}")
