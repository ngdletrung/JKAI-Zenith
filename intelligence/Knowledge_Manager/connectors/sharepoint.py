import os
import hashlib
import time
import json
from urllib.parse import urlparse
from typing import List, Optional

import requests

from .base import ConnectionBase, FileRecord

SUPPORTED_EXTS = {
    ".md", ".txt", ".pdf", ".docx", ".csv", ".json", ".yaml", ".toml",
    ".py", ".js", ".ts", ".html", ".css", ".sh", ".xlsx", ".doc",
}

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
CONNECTIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "connections.json")
DEFAULT_CLIENT_ID = "1950a258-227b-4e31-a9cf-717495945fc2"


class SharePointConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.auth_type = config.get("auth_type", "oauth")
        self.tenant = config.get("tenant_id", "") or "organizations"
        self.client_id = config.get("client_id", "") or DEFAULT_CLIENT_ID
        self.client_secret = config.get("client_secret", "")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.site_url = config.get("site_url", "").rstrip("/")
        self.folder_path = config.get("folder_path", "").strip("/")
        self._token = None
        self._token_expiry = 0
        self._site_id = None

    def _update_connections_file(self):
        try:
            if os.path.exists(CONNECTIONS_PATH):
                with open(CONNECTIONS_PATH, "r", encoding="utf-8") as f:
                    conns = json.load(f)
                for c in conns:
                    if c.get("id") == self.connection_id:
                        c["config"] = self.config
                        break
                with open(CONNECTIONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(conns, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _get_token(self) -> Optional[str]:
        now = time.time()
        if self._token and self._token_expiry > now + 60:
            return self._token

        refresh_token = self.config.get("refresh_token", "")
        access_token = self.config.get("access_token", "")
        tenant = self.tenant or "organizations"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        cid = self.client_id

        # Strategy 1: refresh_token (from Device Code flow)
        if refresh_token:
            try:
                resp = requests.post(token_url, data={
                    "grant_type": "refresh_token",
                    "client_id": cid,
                    "refresh_token": refresh_token,
                    "scope": "https://graph.microsoft.com/.default",
                }, timeout=15)
                if resp.status_code == 200:
                    body = resp.json()
                    self._token = body["access_token"]
                    self._token_expiry = now + body.get("expires_in", 3600)
                    if body.get("refresh_token"):
                        self.config["refresh_token"] = body["refresh_token"]
                        self._update_connections_file()
                    return self._token
            except Exception:
                pass

        # Strategy 2: stored access_token
        if access_token:
            self._token = access_token
            self._token_expiry = now + 3600
            return self._token

        # Strategy 3: ROPC (Basic Auth)
        if self.auth_type == "basic" and self.username and self.password:
            try:
                resp = requests.post(token_url, data={
                    "grant_type": "password",
                    "client_id": cid,
                    "username": self.username,
                    "password": self.password,
                    "scope": "https://graph.microsoft.com/.default",
                }, timeout=15)
                if resp.status_code == 200:
                    body = resp.json()
                    self._token = body["access_token"]
                    self._token_expiry = now + body.get("expires_in", 3600)
                    if body.get("refresh_token"):
                        self.config["refresh_token"] = body["refresh_token"]
                        self._update_connections_file()
                    return self._token
            except Exception:
                pass

        # Strategy 4: client_credentials (OAuth app registration)
        if self.client_secret:
            try:
                resp = requests.post(token_url, data={
                    "grant_type": "client_credentials",
                    "client_id": cid,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                }, timeout=15)
                if resp.status_code == 200:
                    body = resp.json()
                    self._token = body["access_token"]
                    self._token_expiry = now + body.get("expires_in", 3600)
                    return self._token
            except Exception:
                pass

        return None

    def _graph_get(self, path: str) -> Optional[dict]:
        token = self._get_token()
        if not token:
            return None
        try:
            resp = requests.get(
                f"{GRAPH_BASE}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def _resolve_site_id(self) -> Optional[str]:
        if self._site_id:
            return self._site_id
        if not self.site_url:
            return None
        parsed = urlparse(self.site_url)
        hostname = parsed.hostname or ""
        site_path = parsed.path.strip("/")
        if hostname.endswith(".sharepoint.com"):
            path = f"/sites/{hostname}:/{site_path}" if site_path else f"/sites/{hostname}"
        else:
            path = f"/sites/{hostname}:/{site_path}" if site_path else f"/sites/{hostname}"
        result = self._graph_get(path)
        if result and result.get("id"):
            self._site_id = result["id"]
            return self._site_id
        return None

    def list_files(self) -> List[FileRecord]:
        site_id = self._resolve_site_id()
        if not site_id:
            return []

        drives_resp = self._graph_get(f"/sites/{site_id}/drives")
        if not drives_resp:
            return []
        drives = drives_resp.get("value", [])
        if not drives:
            return []
        drive_id = drives[0]["id"]

        if self.folder_path:
            items_path = f"/drives/{drive_id}/root:/{self.folder_path}:/children"
        else:
            items_path = f"/drives/{drive_id}/root/children"

        result = self._graph_get(f"{items_path}?$top=200")
        if not result:
            return []

        records = []
        for item in result.get("value", []):
            name = item.get("name", "")
            ext = os.path.splitext(name)[1].lower()
            if ext not in SUPPORTED_EXTS:
                continue
            if item.get("folder") or item.get("package"):
                continue

            download_url = item.get("@microsoft.graph.downloadUrl") or ""
            size = item.get("size", 0)
            mtime_str = item.get("lastModifiedDateTime", "")
            mtime = 0
            if mtime_str:
                try:
                    mtime = time.mktime(time.strptime(mtime_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"))
                except Exception:
                    mtime = time.time()

            eTag = item.get("eTag", "")
            checksum = hashlib.sha256(eTag.encode()).hexdigest() if eTag else hashlib.md5(name.encode()).hexdigest()

            records.append(FileRecord(
                rel_path=name,
                abs_path=download_url,
                file_type=ext,
                checksum=checksum,
                file_size=size,
                mtime=mtime,
            ))
        return records

    def read_file(self, rel_path: str) -> Optional[str]:
        if rel_path.startswith("http"):
            try:
                resp = requests.get(rel_path, timeout=30)
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                pass

        site_id = self._resolve_site_id()
        if not site_id:
            return None
        token = self._get_token()
        if not token:
            return None

        drives_resp = self._graph_get(f"/sites/{site_id}/drives")
        if not drives_resp:
            return None
        drives = drives_resp.get("value", [])
        if not drives:
            return None
        drive_id = drives[0]["id"]

        try:
            content_path = f"/drives/{drive_id}/root:/{self.folder_path}/{rel_path}:/content" if self.folder_path else f"/drives/{drive_id}/root:/{rel_path}:/content"
            resp = requests.get(
                f"{GRAPH_BASE}{content_path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return None

    def read_file_bytes(self, rel_path: str) -> Optional[bytes]:
        if rel_path.startswith("http"):
            try:
                resp = requests.get(rel_path, timeout=30)
                if resp.status_code == 200:
                    return resp.content
            except Exception:
                pass

        site_id = self._resolve_site_id()
        if not site_id:
            return None
        token = self._get_token()
        if not token:
            return None

        drives_resp = self._graph_get(f"/sites/{site_id}/drives")
        if not drives_resp:
            return None
        drives = drives_resp.get("value", [])
        if not drives:
            return None
        drive_id = drives[0]["id"]

        try:
            content_path = f"/drives/{drive_id}/root:/{self.folder_path}/{rel_path}:/content" if self.folder_path else f"/drives/{drive_id}/root:/{rel_path}:/content"
            resp = requests.get(
                f"{GRAPH_BASE}{content_path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    def get_metadata(self, rel_path: str) -> dict:
        site_id = self._resolve_site_id()
        if not site_id:
            return {}
        drives_resp = self._graph_get(f"/sites/{site_id}/drives")
        if not drives_resp:
            return {}
        drives = drives_resp.get("value", [])
        if not drives:
            return {}
        drive_id = drives[0]["id"]
        meta_path = f"/drives/{drive_id}/root:/{self.folder_path}/{rel_path}" if self.folder_path else f"/drives/{drive_id}/root:/{rel_path}"
        result = self._graph_get(meta_path)
        if not result:
            return {}
        return {
            "size": result.get("size", 0),
            "mtime": result.get("lastModifiedDateTime", ""),
            "created": result.get("createdDateTime", ""),
            "id": result.get("id", ""),
            "web_url": result.get("webUrl", ""),
        }
