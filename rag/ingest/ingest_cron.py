import os
import sys
from pathlib import Path
import time

# Thêm thư mục hiện tại vào path để import ingest
sys.path.insert(0, os.path.dirname(__file__))

from ingest import ingest_folder

if __name__ == "__main__":
    documents_folder = os.getenv("DOCUMENTS_FOLDER", "/storage/documents")
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting auto ingest from: {documents_folder}")
    
    # Kiểm tra thư mục tồn tại
    if not Path(documents_folder).exists():
        print(f"⚠️ Documents folder does not exist: {documents_folder}")
        print("Creating directory...")
        Path(documents_folder).mkdir(parents=True, exist_ok=True)
    
    ingest_folder(documents_folder, recursive=True)
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto ingest completed.")