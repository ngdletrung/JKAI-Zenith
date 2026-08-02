import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [BackupScheduler]: %(message)s")
logger = logging.getLogger("BackupScheduler")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.backup_database import backup_postgres, backup_qdrant_collections

def main():
    interval_hours = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    logger.info(f"🔄 [BACKUP-SCHEDULER-INIT]: Dịch vụ sao lưu tự động định kỳ mỗi {interval_hours} giờ khởi chạy...")
    
    while True:
        try:
            logger.info("🐘 [CRON-TRIGGER]: Bắt đầu tiến trình sao lưu PostgreSQL & Qdrant...")
            backup_postgres()
            backup_qdrant_collections()
            logger.info(f"✅ [CRON-SUCCESS]: Hoàn tất sao lưu. Chờ {interval_hours} giờ cho chu kỳ tiếp theo.")
        except Exception as e:
            logger.error(f"❌ [CRON-ERR] Lỗi sao lưu: {e}")
            
        time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    main()
