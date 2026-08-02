import os
import json
import subprocess
from typing import List, Optional
from .base import ConnectionBase, FileRecord

RCLONE_CONFIG = os.getenv("RCLONE_CONFIG_PATH_CONTAINER", "/workspace/data/rclone/rclone.conf")

class RCloneConnector(ConnectionBase):
    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self.remote = config.get("remote", "")
        self.folder_path = config.get("folder_path", "").strip("/")
        
    def _run_rclone(self, args: List[str]) -> Optional[str]:
        cmd = ["rclone", f"--config={RCLONE_CONFIG}"] + args
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=30)
            if res.returncode == 0:
                return res.stdout.decode('utf-8', errors='replace')
            return None
        except Exception:
            return None

    def list_files(self) -> List[FileRecord]:
        if not self.remote:
            return []
        
        target = f"{self.remote}:"
        if self.folder_path:
            target = f"{self.remote}:{self.folder_path}"
            
        # Call rclone lsjson to get recursive file list
        out = self._run_rclone(["lsjson", "-R", target])
        if not out:
            return []
            
        records = []
        try:
            items = json.loads(out)
            for item in items:
                if item.get("IsDir"):
                    continue
                name = item.get("Name", "")
                rel_path = item.get("Path", "")
                # Create FileRecord
                records.append(FileRecord(
                    rel_path=rel_path,
                    abs_path=f"rclone://{self.remote}/{self.folder_path}/{rel_path}".replace("//", "/"),
                    file_size=item.get("Size", 0),
                    mtime=0
                ))
        except Exception:
            pass
        return records

    def read_file(self, rel_path: str) -> Optional[str]:
        if not self.remote:
            return None
        
        target = f"{self.remote}:{self.folder_path}/{rel_path}".replace("//", "/")
        out = self._run_rclone(["cat", target])
        return out

    def read_file_bytes(self, rel_path: str) -> Optional[bytes]:
        if not self.remote:
            return None
        target = f"{self.remote}:{self.folder_path}/{rel_path}".replace("//", "/")
        cmd = ["rclone", f"--config={RCLONE_CONFIG}", "cat", target]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=30)
            if res.returncode == 0:
                return res.stdout
            return None
        except Exception:
            return None

    def get_metadata(self, rel_path: str) -> dict:
        return {}
