import os
import sys
import hashlib
from pathlib import Path
import requests
from typing import List, Dict, Optional

# Các thư viện trích xuất tài liệu (được nạp lazily khi cần xử lý định dạng tương ứng)
try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None

try:
    import docx
except ImportError:
    docx = None

try:
    import markdown
except ImportError:
    markdown = None

# Lấy URL từ environment hoặc dùng mặc định
_base_url = os.getenv("RAG_API_URL", "http://rag-service:8000")
RAG_API = f"{_base_url.rstrip('/')}/ingest/text" if "/ingest/text" not in _base_url else _base_url

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
    
    elif suffix in [".pptx", ".ppt", ".xlsx", ".xls", ".html", ".htm", ".eml", ".csv"]:
        try:
            from unstructured.partition.auto import partition
            elements = partition(filename=str(file_path))
            return "\n\n".join([str(el) for el in elements])
        except Exception as e:
            raise ValueError(f"Lỗi trích xuất file qua unstructured: {e}")
    
def should_allow_ingest_file(file_path: Path | str) -> bool:
    """
    [P0.4]: Kiểm tra blocklist bảo vệ RAG Ingest:
    Chặn 100% tài liệu bí mật, sealed_C, .env, *.pem, credentials, certs khỏi RAG Ingest.
    """
    raw_str = str(file_path).replace("\\", "/").strip()
    low = raw_str.lower()

    # 1. Chặn các thư mục cấm (forbidden directories)
    forbidden_dirs = {
        "sealed_c",
        "sealed_exam",
        ".git",
        ".zenith",
        ".venv",
        "venv",
        "node_modules",
        "certs",
        "credentials",
        "__pycache__",
    }
    parts = [p.lower() for p in raw_str.split("/") if p]
    for p in parts:
        if p in forbidden_dirs:
            return False
        if p.startswith(".env"):
            return False

    # 2. Chặn các đoạn nhạy cảm (sensitive fragments)
    sensitive_fragments = (
        "sealed_c",
        "sealed_exam",
        ".env",
        ".pem",
        "secret",
        "credential",
        "private_key",
        "sovereign_exam",
    )
    for frag in sensitive_fragments:
        if frag in low:
            return False

    # 3. Chặn các phần mở rộng nguy hiểm
    suffix = Path(raw_str).suffix.lower()
    if suffix in [".pem", ".key", ".crt", ".pfx", ".p12"]:
        return False

    return True


def ingest_file(file_path: Path, metadata: Optional[Dict] = None):
    if not should_allow_ingest_file(file_path):
        print(f"🛑 [BLOCKED] File is in blocklist or sensitive: {file_path}")
        return False

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
        extensions = [".pdf", ".docx", ".md", ".markdown", ".txt", ".pptx", ".ppt", ".xlsx", ".xls", ".html", ".htm", ".eml", ".csv"]
    
    pattern = "**/*" if recursive else "*"
    files = [f for f in folder.glob(pattern) if f.is_file() and f.suffix.lower() in extensions and should_allow_ingest_file(f)]
    
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