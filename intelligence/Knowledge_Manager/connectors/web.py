import os
import hashlib
import time
from typing import List, Optional
from .base import ConnectionBase, FileRecord


class WebConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.base_url = config.get("url", "").rstrip("/")
        self.crawl_depth = config.get("depth", 0)

    def list_files(self) -> List[FileRecord]:
        if not self.base_url:
            return []
        try:
            import requests
            resp = requests.get(self.base_url, timeout=10)
            if resp.status_code != 200:
                return []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            links = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") or href.startswith("/"):
                    full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                    links.add(full_url)
            records = []
            for url in list(links)[:50]:
                url_hash = hashlib.md5(url.encode()).hexdigest()
                records.append(FileRecord(
                    rel_path=url_hash,
                    abs_path=url,
                    file_type=".html",
                    checksum=url_hash,
                    file_size=0,
                    mtime=time.time(),
                ))
            return records
        except Exception:
            return []

    def read_file(self, rel_path: str) -> Optional[str]:
        try:
            import requests
            resp = requests.get(rel_path, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return None

    def get_metadata(self, rel_path: str) -> dict:
        return {"url": rel_path, "fetched_at": time.time()}
