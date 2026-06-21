import requests
import os
import time
import logging
from core.utils import report_formatter as rf

logger = logging.getLogger("jkai.tools.sync")

def sync_nuclear():
    """
    Nuclear Sync: Chiến dịch đồng bộ toàn diện.
    """
    logger.info("[JKAI-NUCLEAR-SYNC] Bắt đầu Chuỗi phản ứng Đồng bộ...")
    
    BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai-brain:8000")
    RAG_URL = os.getenv("RAG_API_URL", "http://rag-service:8000")
    
    results = []

    # --- GIAI ĐOẠN 1: ĐỒNG HÓA ---
    try:
        logger.info("[STAGE 1] Đang kích hoạt Assimilator...")
        resp_assimilate = requests.post(f"{BRAIN_URL}/assimilate", timeout=300)
        if resp_assimilate.status_code == 200:
            data = resp_assimilate.json()
            results.append(f"✅ Đồng hóa: {data.get('msg', 'Hoàn tất')}")
        else:
            results.append(f"⚠️ Đồng hóa: Lỗi HTTP {resp_assimilate.status_code}")
    except Exception as e:
        results.append(f"❌ Đồng hóa: Thất bại ({str(e)})")

    # Nghỉ ngắn để hệ thống file ổn định
    time.sleep(2)

    # --- GIAI ĐOẠN 2: GHI NHỚ ---
    try:
        logger.info("[STAGE 2] Đang nạp tri thức vào Ma trận RAG...")
        resp_rag = requests.post(f"{RAG_URL}/ingest/intelligence", timeout=600)
        if resp_rag.status_code == 200:
            data = resp_rag.json()
            results.append(f"✅ Ghi nhớ: {data.get('message', 'Hoàn tất')}")
        else:
            results.append(f"⚠️ Ghi nhớ: Lỗi HTTP {resp_rag.status_code}")
    except Exception as e:
        results.append(f"❌ Ghi nhớ: Thất bại ({str(e)})")

    bullet_msg = rf.bullet(results)
    logger.info("[JKAI-NUCLEAR-SYNC] %s", bullet_msg)
    
    return {
        "status": "success" if "❌" not in "".join(results) else "partial_error",
        "message": rf.build([rf.section("Kết quả Đồng bộ Tri thức"), bullet_msg])
    }
