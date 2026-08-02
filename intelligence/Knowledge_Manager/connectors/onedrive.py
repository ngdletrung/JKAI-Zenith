import os
import hashlib
import time
import json
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


class OneDriveConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.client_id = config.get("client_id", "") or DEFAULT_CLIENT_ID
        self.client_secret = config.get("client_secret", "")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.folder_path = config.get("folder_path", "/").strip("/")
        self.tenant = config.get("tenant", "") or config.get("tenant_id", "") or "common"
        self.auth_type = config.get("auth_type", "oauth")
        self._token = None
        self._token_expiry = 0

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
        token_url = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
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

        # Strategy 2: stored access_token (may be expired, but worth trying)
        if access_token:
            self._token = access_token
            self._token_expiry = now + 3600
            return self._token

        # Strategy 3: ROPC (Basic Auth, requires app password)
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

    def _build_drive_path(self, rel_path: str = "") -> str:
        if self.folder_path:
            base = f"/me/drive/root:/{self.folder_path}"
        else:
            base = "/me/drive/root"
        if rel_path:
            return f"{base}/{rel_path}"
        return base

    def list_files(self) -> List[FileRecord]:
        drive_path = self._build_drive_path()
        result = self._graph_get(f"{drive_path}:/children?$top=200")
        if not result:
            return []

        records = []
        items = result.get("value", [])
        for item in items:
            name = item.get("name", "")
            ext = os.path.splitext(name)[1].lower()
            if ext not in SUPPORTED_EXTS:
                continue
            is_folder = item.get("folder") is not None
            if is_folder:
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
            checksum = hashlib.md5((item.get("id", name) + str(mtime)).encode()).hexdigest()
            eTag = item.get("eTag", "")
            if eTag:
                checksum = hashlib.sha256(eTag.encode()).hexdigest()

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
        drive_path = self._build_drive_path(rel_path)
        token = self._get_token()
        if not token:
            return None
        try:
            resp = requests.get(
                f"{GRAPH_BASE}{drive_path}:/content",
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
        drive_path = self._build_drive_path(rel_path)
        token = self._get_token()
        if not token:
            return None
        try:
            resp = requests.get(
                f"{GRAPH_BASE}{drive_path}:/content",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    def get_metadata(self, rel_path: str) -> dict:
        drive_path = self._build_drive_path(rel_path)
        result = self._graph_get(drive_path)
        if not result:
            return {}
        return {
            "size": result.get("size", 0),
            "mtime": result.get("lastModifiedDateTime", ""),
            "created": result.get("createdDateTime", ""),
            "id": result.get("id", ""),
            "web_url": result.get("webUrl", ""),
        }
