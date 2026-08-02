import os
import hashlib
from typing import List, Optional
from .base import ConnectionBase, FileRecord

SUPPORTED_EXTS = {
    ".md", ".txt", ".pdf", ".docx", ".csv", ".json", ".yaml", ".toml",
    ".py", ".js", ".ts", ".html", ".css", ".sh", ".xlsx", ".doc",
}


class LocalFileConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.root_path = config.get("path", "")

    def _compute_checksum(self, filepath: str) -> str:
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def list_files(self) -> List[FileRecord]:
        results = []
        if not os.path.isdir(self.root_path):
            return results
        for root, _, files in os.walk(self.root_path):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTS:
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, self.root_path)
                stat = os.stat(filepath)
                results.append(FileRecord(
                    rel_path=rel_path,
                    abs_path=filepath,
                    file_type=ext,
                    checksum=self._compute_checksum(filepath),
                    file_size=stat.st_size,
                    mtime=stat.st_mtime,
                ))
        return results

    def read_file(self, rel_path: str) -> Optional[str]:
        full_path = os.path.join(self.root_path, rel_path)
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def read_file_bytes(self, rel_path: str) -> Optional[bytes]:
        full_path = os.path.join(self.root_path, rel_path)
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "rb") as f:
                return f.read()
        except Exception:
            return None

    def get_metadata(self, rel_path: str) -> dict:
        full_path = os.path.join(self.root_path, rel_path)
        try:
            stat = os.stat(full_path)
            return {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "ctime": stat.st_ctime,
            }
        except Exception:
            return {}
