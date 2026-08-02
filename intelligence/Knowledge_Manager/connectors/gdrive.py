import os
import hashlib
import time
from urllib.parse import quote
from typing import List, Optional

import requests

from .base import ConnectionBase, FileRecord

SUPPORTED_EXTS = {
    ".md", ".txt", ".pdf", ".docx", ".csv", ".json", ".yaml", ".toml",
    ".py", ".js", ".ts", ".html", ".css", ".sh", ".xlsx", ".doc",
}

API_BASE = "https://www.googleapis.com/drive/v3"
OAUTH_TOKEN = "https://oauth2.googleapis.com/token"


class GDriveConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.access_token = config.get("access_token", "")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.refresh_token = config.get("refresh_token", "")
        self.folder_path = config.get("folder_path", "").strip("/")
        self._token = None
        self._token_expiry = 0

    def _ensure_token(self) -> Optional[str]:
        if self.access_token:
            return self.access_token
        if self._token and self._token_expiry > time.time() + 60:
            return self._token
        if self.refresh_token and self.client_id and self.client_secret:
            try:
                resp = requests.post(OAUTH_TOKEN, data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                }, timeout=15)
                if resp.status_code == 200:
                    body = resp.json()
                    self._token = body["access_token"]
                    self._token_expiry = time.time() + body.get("expires_in", 3600)
                    return self._token
            except Exception:
                pass
        return None

    def _api_get(self, path: str, params: dict = None) -> Optional[dict]:
        token = self._ensure_token()
        if not token:
            return None
        try:
            resp = requests.get(
                f"{API_BASE}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def _resolve_folder_id(self) -> Optional[str]:
        if not self.folder_path:
            return "root"
        try:
            q = f"name='{self.folder_path}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            result = self._api_get("/files", {"q": q, "pageSize": 1, "fields": "files(id)"})
            if result and result.get("files"):
                return result["files"][0]["id"]
        except Exception:
            pass
        return "root"

    def list_files(self) -> List[FileRecord]:
        folder_id = self._resolve_folder_id()
        if not folder_id:
            return []

        records = []
        page_token = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "pageSize": 100,
                "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,md5Checksum,webContentLink)",
            }
            if page_token:
                params["pageToken"] = page_token

            result = self._api_get("/files", params)
            if not result:
                break

            for item in result.get("files", []):
                name = item.get("name", "")
                ext = os.path.splitext(name)[1].lower()
                if ext not in SUPPORTED_EXTS:
                    continue
                if item.get("mimeType") == "application/vnd.google-apps.folder":
                    continue

                file_id = item["id"]
                size = int(item.get("size", 0))
                mtime_str = item.get("modifiedTime", "")
                mtime = 0
                if mtime_str:
                    try:
                        mtime = time.mktime(time.strptime(mtime_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"))
                    except Exception:
                        mtime = time.time()

                checksum = item.get("md5Checksum", "")
                if not checksum:
                    checksum = hashlib.md5(file_id.encode()).hexdigest()

                dl_url = item.get("webContentLink", "")
                records.append(FileRecord(
                    rel_path=name,
                    abs_path=dl_url,
                    file_type=ext,
                    checksum=checksum,
                    file_size=size,
                    mtime=mtime,
                ))

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return records

    def read_file(self, rel_path: str) -> Optional[str]:
        token = self._ensure_token()
        if not token:
            return None
        # rel_path is the file ID from list_files
        try:
            resp = requests.get(
                f"{API_BASE}/files/{quote(rel_path)}?alt=media",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return None

    def read_file_bytes(self, rel_path: str) -> Optional[bytes]:
        token = self._ensure_token()
        if not token:
            return None
        try:
            resp = requests.get(
                f"{API_BASE}/files/{quote(rel_path)}?alt=media",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    def get_metadata(self, rel_path: str) -> dict:
        token = self._ensure_token()
        if not token:
            return {}
        try:
            resp = requests.get(
                f"{API_BASE}/files/{quote(rel_path)}?fields=id,name,size,modifiedTime,createdTime,mimeType,webViewLink",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "id": data.get("id", ""),
                    "name": data.get("name", ""),
                    "size": int(data.get("size", 0)),
                    "mtime": data.get("modifiedTime", ""),
                    "created": data.get("createdTime", ""),
                    "mime_type": data.get("mimeType", ""),
                    "web_url": data.get("webViewLink", ""),
                }
        except Exception:
            pass
        return {}
