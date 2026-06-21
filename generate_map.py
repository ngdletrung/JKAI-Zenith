import asyncio
import os
import sys

# Configure UTF-8 encoding for Windows console to handle emojis safely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.append(r'D:\Docker\JKAI')
sys.path.append(r'D:\Docker\JKAI\services\ai-brain')

from knowledge_graph import get_universal_graph

async def main():
    print("🚀 Khởi động UniversalGraph cho JKAI Map...")
    g = get_universal_graph()
    
    # Ép UniversalGraph xuất dữ liệu ra thư mục riêng của JKAI
    custom_dir = r"D:\Docker\JKAI\JKAI_MAP"
    if not os.path.exists(custom_dir):
        os.makedirs(custom_dir)
        
    dirs = [
        r"D:\Docker\JKAI\core",
        r"D:\Docker\JKAI\services",
        r"D:\Docker\JKAI\intelligence",
        r"D:\Docker\JKAI\scripts"
    ]
    await g.build_and_sync(dirs, obsidian_vault=custom_dir)
    print(f"✅ Đã xuất bản đồ tại {custom_dir}")

if __name__ == "__main__":
    asyncio.run(main())
