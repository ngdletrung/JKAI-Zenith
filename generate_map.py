import asyncio
import os
import sys

# Configure UTF-8 encoding for Windows console to handle emojis safely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.append(r'D:\Docker\N8N')
sys.path.append(r'D:\Docker\N8N\services\ai-brain')

from knowledge_graph import get_universal_graph

async def main():
    print("🚀 Khởi động UniversalGraph cho Antigravity Map...")
    g = get_universal_graph()
    
    # Ép UniversalGraph xuất dữ liệu ra thư mục riêng của Antigravity
    custom_dir = r"D:\Docker\N8N\ANTIGRAVITY_MAP"
    if not os.path.exists(custom_dir):
        os.makedirs(custom_dir)
        
    dirs = [
        r"D:\Docker\N8N\core",
        r"D:\Docker\N8N\services",
        r"D:\Docker\N8N\intelligence",
        r"D:\Docker\N8N\scripts"
    ]
    await g.build_and_sync(dirs, obsidian_vault=custom_dir)
    print(f"✅ Đã xuất bản đồ tại {custom_dir}")

if __name__ == "__main__":
    asyncio.run(main())
