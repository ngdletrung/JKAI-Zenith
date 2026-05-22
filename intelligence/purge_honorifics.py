import os
import re

def purge_honorifics(root_dir):
    """
    🧹 JKAI ZENITH: OMNI-PURGE SCRIPT
    Nhiệm vụ: Loại bỏ hậu ngữ lễ nghi khỏi toàn bộ mã nguồn và tài liệu.
    """
    patterns = [
        r'\s*thưa\s+Master[!]*',
        r'\s*thưa\s+Ngài[!]*',
        r'\s*thưa\s+master[!]*',
        r'\s*thưa\s+ngài[!]*'
    ]
    
    combined_pattern = re.compile('|'.join(patterns), re.IGNORECASE)
    
    files_cleaned = 0
    total_replaced = 0

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(('.py', '.md', '.json', '.yaml', '.yml', '.txt')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content, count = combined_pattern.subn('', content)
                    
                    if count > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_cleaned += 1
                        total_replaced += count
                        print(f"✅ Cleaned: {file_path} ({count} instances)")
                except Exception as e:
                    print(f"❌ Error in {file_path}: {e}")

    print(f"\n✨ [PURGE-COMPLETE]:")
    print(f"   - Tổng số tệp đã thanh tẩy: {files_cleaned}")
    print(f"   - Tổng số hậu ngữ đã xóa: {total_replaced}")

if __name__ == "__main__":
    purge_honorifics(r'd:\Docker\N8N\intelligence')
