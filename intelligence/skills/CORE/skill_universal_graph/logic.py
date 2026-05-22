import asyncio
import logging
import os
import sys

# Thêm đường dẫn tới services để import orchestrator
try:
    from core.utils.engine import engine
except ImportError:
    pass, "..", "..", "..")))
from services.ai_brain.knowledge_graph import get_universal_graph

logger = logging.getLogger(__name__)

async def execute(directories: list[str] = None, obsidian_vault: str = None) -> dict:
    """
    Thực thi đồng bộ đồ thị tri thức vạn vật.
    
    Args:
        directories: Danh sách thư mục cần quét. Mặc định là các thư mục cốt lõi.
        obsidian_vault: Đường dẫn xuất Obsidian.
    """
    try:
        graph = get_universal_graph()
        
        if not directories:
            # Mặc định quét các vùng tri thức cốt lõi
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            directories = [
                os.path.join(base, "core"),
                os.path.join(base, "services"),
                os.path.join(base, "agents"),
                os.path.join(base, "intelligence"),
            ]
            
        if not obsidian_vault:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            obsidian_vault = os.path.join(base, "JKAI_Universal_Brain")

        stats = await graph.build_and_sync(directories, obsidian_vault=obsidian_vault)
        return {
            "status": "success",
            "message": "Đồ thị nhất thể đã được đồng bộ hóa thành công.",
            "data": stats
        }
    except Exception as e:
        logger.error(f"UniversalGraph execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # Test nhanh
    logging.basicConfig(level=logging.INFO)
    asyncio.run(execute())
