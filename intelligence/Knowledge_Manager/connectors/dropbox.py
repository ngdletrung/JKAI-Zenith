import os
import hashlib
import time
from typing import List, Optional

import requests

from .base import ConnectionBase, FileRecord

SUPPORTED_EXTS = {
    ".md", ".txt", ".pdf", ".docx", ".csv", ".json", ".yaml", ".toml",
    ".py", ".js", ".ts", ".html", ".css", ".sh", ".xlsx", ".doc",
}

API_BASE = "https://api.dropboxapi.com/2"
CONTENT_BASE = "https://content.dropboxapi.com/2"


class DropboxConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.access_token = config.get("access_token", "")
        self.folder_path = config.get("folder_path", "/").strip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _api_post(self, url: str, json_body: dict) -> Optional[dict]:
        try:
            resp = requests.post(url, headers=self._headers(), json=json_body, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def list_files(self) -> List[FileRecord]:
        if not self.access_token:
            return []

        path = f"/{self.folder_path}" if self.folder_path else ""
        result = self._api_post(f"{API_BASE}/files/list_folder", {
            "path": path or None,
            "recursive": False,
            "limit": 200,
        })
        if not result:
            return []

        records = []
        for entry in result.get("entries", []):
            if entry.get(".tag") != "file":
                continue
            name = entry.get("name", "")
            ext = os.path.splitext(name)[1].lower()
            if ext not in SUPPORTED_EXTS:
                continue

            size = entry.get("size", 0)
            mtime_str = entry.get("server_modified", "")
            mtime = 0
            if mtime_str:
                try:
                    mtime = time.mktime(time.strptime(mtime_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"))
                except Exception:
                    mtime = time.time()

            content_hash = entry.get("content_hash", "")
            if not content_hash:
                content_hash = hashlib.md5(entry.get("id", name).encode()).hexdigest()

            records.append(FileRecord(
                rel_path=entry.get("path_lower", name),
                abs_path=entry.get("path_display", name),
                file_type=ext,
                checksum=content_hash,
                file_size=size,
                mtime=mtime,
            ))
        return records

    def read_file(self, rel_path: str) -> Optional[str]:
        if not self.access_token:
            return None
        try:
            resp = requests.post(
                f"{CONTENT_BASE}/files/download",
                headers={
                    **self._headers(),
                    "Dropbox-API-Arg": f'{{"path":"{rel_path}"}}',
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return None

    def read_file_bytes(self, rel_path: str) -> Optional[bytes]:
        if not self.access_token:
            return None
        try:
            resp = requests.post(
                f"{CONTENT_BASE}/files/download",
                headers={
                    **self._headers(),
                    "Dropbox-API-Arg": f'{{"path":"{rel_path}"}}',
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    def get_metadata(self, rel_path: str) -> dict:
        result = self._api_post(f"{API_BASE}/files/get_metadata", {"path": rel_path})
        if not result:
            return {}
        return {
            "name": result.get("name", ""),
            "path": result.get("path_display", ""),
            "size": result.get("size", 0),
            "mtime": result.get("server_modified", ""),
            "id": result.get("id", ""),
        }
