import os
import sys
import hashlib
from pathlib import Path
import requests
from typing import List, Dict, Optional

# Import các thư viện với error handling
try:
    import pymupdf4llm
    import docx
    import markdown
except ImportError as e:
    print(f"Lỗi import: {e}")
    print("Chạy lệnh: pip install pymupdf4llm python-docx markdown")
    sys.exit(1)

# Lấy URL từ environment hoặc dùng mặc định
RAG_API = os.getenv("RAG_API_URL", "http://rag-service:8000/ingest/text")

def get_file_hash(file_path: Path) -> str:
    return hashlib.md5(file_path.read_bytes()).hexdigest()

def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    
    if suffix == ".pdf":
        # PyMuPDF4LLM cho Markdown chất lượng cao
        return pymupdf4llm.to_markdown(str(file_path))
    
    elif suffix in [".docx", ".doc"]:
        doc = docx.Document(file_path)
        return "\n\n".join([para.text for para in doc.paragraphs])
    
    elif suffix in [".md", ".markdown", ".txt"]:
        return file_path.read_text(encoding="utf-8")
    
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

def ingest_file(file_path: Path, metadata: Optional[Dict] = None):
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📄 Processing: {file_path.name}")
    
    try:
        content = extract_text(file_path)
        if not content.strip():
            print("⚠️  No content extracted")
            return False
        
        # Metadata tự động
        meta = {
            "filename": file_path.name,
            "file_type": file_path.suffix,
            "file_size": file_path.stat().st_size,
            "source_path": str(file_path),
            **(metadata or {})
        }
        
        payload = {
            "text": content,
            "metadata": meta
        }
        
        response = requests.post(RAG_API, json=payload, timeout=60)
        
        if response.status_code == 200:
            print(f"✅ Ingested successfully: {file_path.name} ({len(content)} chars)")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")
        return False

def ingest_folder(folder_path: str, recursive: bool = True, extensions: List[str] = None):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return
    
    if extensions is None:
        extensions = [".pdf", ".docx", ".md", ".markdown", ".txt"]
    
    pattern = "**/*" if recursive else "*"
    files = [f for f in folder.glob(pattern) if f.is_file() and f.suffix.lower() in extensions]
    
    print(f"🔍 Found {len(files)} files to ingest...")
    
    success = 0
    for file in files:
        if ingest_file(file):
            success += 1
    
    print(f"\n🎉 Hoàn tất! {success}/{len(files)} files ingested vào RAG.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <folder_or_file_path> [recursive]")
        sys.exit(1)
    
    path = sys.argv[1]
    recursive = len(sys.argv) > 2 and sys.argv[2].lower() in ["true", "1", "yes"]
    
    if Path(path).is_file():
        ingest_file(Path(path))
    else:
        ingest_folder(path, recursive=recursive)