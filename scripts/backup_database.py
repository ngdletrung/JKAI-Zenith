import os
import sys
import time
import subprocess
import httpx
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BACKUP_DIR = os.getenv("BACKUP_DIR", "D:\\Docker\\JKAI\\brain\\backups")

def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_postgres():
    """🐘 [BACKUP-POSTGRES]: Sao lưu cơ sở dữ liệu PostgreSQL."""
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"postgres_backup_{timestamp}.sql")
    
    print(f"🐘 [BACKUP]: Khởi tạo sao lưu PostgreSQL -> {backup_file}...")
    try:
        res = subprocess.run(
            ["docker", "exec", "postgres", "pg_dump", "-U", "n8n", "n8n"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if res.returncode == 0 and res.stdout:
            with open(backup_file, "w", encoding="utf-8") as f:
                f.write(res.stdout)
            print(f"✅ [POSTGRES-OK]: Tệp sao lưu đã tạo thành công ({os.path.getsize(backup_file)} bytes).")
            return backup_file
        else:
            print(f"⚠️ [POSTGRES-WARN]: pg_dump trả về mã lỗi hoặc không có dữ liệu: {res.stderr[:200]}")
            return None
    except Exception as e:
        print(f"❌ [POSTGRES-ERR]: Không thể thực thi pg_dump: {e}")
        return None

def backup_qdrant_collections():
    """🧠 [BACKUP-QDRANT]: Sao lưu bộ nhớ Vector Qdrant qua Snapshot API."""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    print(f"🧠 [BACKUP]: Gửi yêu cầu tạo Snapshot cho các Qdrant Collections tại {qdrant_url}...")
    
    collections = ["jkai_memory", "jkai_zenith_intel", "jkai_knowledge", "jkai_reasoning_bank"]
    results = {}
    
    with httpx.Client(timeout=30.0) as client:
        for col in collections:
            try:
                res = client.post(f"{qdrant_url}/collections/{col}/snapshots")
                if res.status_code == 200:
                    snap_data = res.json().get("result", {})
                    results[col] = snap_data.get("name", "OK")
                    print(f"  ✅ [QDRANT]: Collection `{col}` -> Snapshot `{results[col]}`")
                else:
                    results[col] = f"Error {res.status_code}"
            except Exception as e:
                results[col] = f"Failed: {e}"
                
    return results

def run_cron_scheduler(interval_hours: int = 24):
    """🔄 [CRON-SCHEDULER]: Vòng lặp sao lưu tự động định kỳ."""
    print(f"🔄 [CRON-SCHEDULER]: Kích hoạt lịch sao lưu tự động mỗi {interval_hours} giờ...")
    while True:
        backup_postgres()
        backup_qdrant_collections()
        time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cron":
        run_cron_scheduler(24)
    else:
        print("==========================================================")
        print("🛡️ [JKAI SOVEREIGN OS] - KHỞI TẠO TỰ ĐỘNG SAO LƯU DỮ LIỆU DỰ PHÒNG")
        print("==========================================================")
        
        t0 = time.time()
        pg_res = backup_postgres()
        qd_res = backup_qdrant_collections()
        
        duration = time.time() - t0
        print(f"\n🏁 [BACKUP-COMPLETE]: Hoàn tất chuỗi sao lưu trong {duration:.2f} giây.")
