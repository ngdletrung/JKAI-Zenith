import os
import json
import asyncio
import re
import logging
import sys

# 🌐 [TERMINAL-UNICODE-FIX]: Đảm bảo Terminal hiển thị được Emoji và Tiếng Việt thưa Master
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Thêm đường dẫn gốc vào sys.path để import được core thưa Master
sys.path.append(os.getcwd())

from core.utils.engine import engine
from core.utils.knowledge_brain import knowledge_brain
from core.qdrant_client import qdrant_client

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('IgniteKnowledge')

from core.config import settings

INTEL_DIR = settings.INTELLIGENCE_DIR

def extract_links(text):
    """Trích xuất các liên kết [[link]] để xây dựng bản đồ Graph thưa Master."""
    return re.findall(r'\[\[(.*?)\]\]', text)

async def ignite():
    """🚀 [IGNITION v2.1]: Cuộc tổng đại hành quân nạp tri thức chuẩn Elite thưa Master."""
    logger.info(f"🔥 [IGNITE]: Bắt đầu cuộc tổng đại hành quân vào Thánh địa `{INTEL_DIR}`...")
    
    await knowledge_brain.initialize()
    
    # 🧹 [PURGE]: Xóa bỏ các nơ-ron cũ bị lỗi thưa Master
    await qdrant_client.clear_collection(knowledge_brain.collection_name)
    await knowledge_brain.initialize()
    
    files_processed = 0
    chunks_indexed = 0
    
    # 📂 [TOTAL-ABSORPTION]: Nạp TOÀN BỘ tri thức thưa Master
    SUPPORTED_EXTS = {
        '.md', '.pdf', '.docx', '.xlsx', '.txt', '.csv',
        '.py', '.js', '.ts', '.html', '.css', '.sh', '.bat',
        '.json', '.jsonl', '.yaml', '.yml', '.toml', '.ini', '.xml'
    }
    
    for root, dirs, files in os.walk(INTEL_DIR):
        # 🛡️ [SECURITY-FILTER]: Loại bỏ các khu vực nhạy cảm hoặc rác thưa Master
        root_lower = root.lower()
        if any(x in root_lower for x in ["archive", ".git", "__pycache__", "node_modules", "protocols"]): 
            continue

        # Lấy category từ thư mục thưa Master
        category = os.path.basename(root)
        
        for file in files:
            # 🚫 [LOG-FILTER]: Không nạp nhật ký thưa Master
            if "log" in file.lower() or "tail" in file.lower(): continue
            
            ext = os.path.splitext(file)[1].lower()
            if ext not in SUPPORTED_EXTS: continue

            file_path = os.path.join(root, file)
            try:
                # 🧠 [UNIVERSAL-READ]: Dùng Converter chuyên dụng thưa Master
                from core.utils.converter import converter
                content = await converter.to_markdown(file_path)
                
                if not content or not content.strip(): continue
                
                # 🧩 [GRAPH-AWARENESS]: Trích xuất liên kết
                links = extract_links(content)
                
                # 🔪 Phân rã tri thức
                chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
                v_size = await engine.get_vector_size(knowledge_brain.embedder_role)
                
                # Tên nốt tri thức thưa Master
                note_name = os.path.splitext(file)[0]
                title = note_name.replace("_", " ").title()
                
                for i, chunk in enumerate(chunks):
                    # 🧬 [CONTEXT-INJECTION]: Gắn tiêu đề vào mỗi chunk thưa Master
                    header = f"--- [TÀI LIỆU: {note_name}] ---\n"
                    chunk_with_context = header + chunk
                    
                    embedding = await engine.get_embeddings(chunk_with_context)
                    if embedding:
                        # 💎 [METADATA-RICH]: Nạp đầy đủ thông tin định danh
                        await qdrant_client.upsert_intel(
                            text=chunk_with_context,
                            embedding=embedding,
                            metadata={
                                "path": file_path,
                                "rel_path": os.path.relpath(file_path, INTEL_DIR),
                                "filename": file,
                                "name": note_name,
                                "title": title,
                                "category": category,
                                "chunk_idx": i,
                                "links": links if i == 0 else []
                            },
                            collection=knowledge_brain.collection_name,
                            vector_size=v_size
                        )
                        chunks_indexed += 1
                
                files_processed += 1
                logger.info(f"✅ [INDEXED]: {note_name} ({category})")
                
            except Exception as e:
                logger.error(f"❌ [IGNITE-ERR]: Lỗi tại {file_path}: {e}")

    logger.info(f"✨ [IGNITE COMPLETE]: Đã nạp {files_processed} tệp tin và {chunks_indexed} mẩu tri thức chuẩn Elite thưa Master!")

if __name__ == "__main__":
    asyncio.run(ignite())
