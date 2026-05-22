import asyncio
import os
import logging
import re
from typing import Dict, Optional, Set, List
from pathlib import Path

logger = logging.getLogger('PathLocker')

class PathLockRegistry:
    """
    🛡️ [HERMES-PATH-LOCK v2.0]: Cơ chế khóa đường dẫn thông minh.
    Hỗ trợ Subtree Locking và Destructive Detection.
    """
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._destructive_commands = {"rm", "mv", "git reset", "git clean", "truncate", "del", "erase"}

    def _normalize_path(self, raw_path: str) -> str:
        try:
            p = Path(raw_path).expanduser().absolute()
            return str(p)
        except:
            return raw_path

    def _is_destructive(self, command: str) -> bool:
        """Kiểm tra lệnh có tính chất hủy diệt không."""
        cmd_lower = command.lower()
        return any(dc in cmd_lower for dc in self._destructive_commands)

    async def acquire_locks(self, step: dict) -> List[asyncio.Lock]:
        """
        ⚔️ [LOCK-ACQUISITION]: Lấy danh sách các khóa cần thiết.
        Nếu là lệnh hủy diệt -> Khóa toàn bộ thư mục gốc.
        """
        paths = self.extract_paths_from_step(step)
        args = step.get("args", {}) or step.get("arguments", {})
        cmd = args.get("command", "") if isinstance(args, dict) else ""
        
        is_dest = self._is_destructive(cmd)
        target_locks = []

        async with self._global_lock:
            for p in paths:
                norm_p = self._normalize_path(p)
                # Nếu là lệnh hủy diệt, chúng ta khóa cả thư mục cha
                lock_path = str(Path(norm_p).parent) if is_dest else norm_p
                
                if lock_path not in self._locks:
                    self._locks[lock_path] = asyncio.Lock()
                target_locks.append(self._locks[lock_path])
                
        return target_locks

    def can_run_parallel(self, paths_a: Set[str], paths_b: Set[str]) -> bool:
        """
        🧠 [SUBTREE-PARALLELISM]: Kiểm tra xem hai bộ đường dẫn có thể chạy song song không.
        Nếu thuộc hai nhánh thư mục khác nhau hoàn toàn -> OK.
        """
        for pa in paths_a:
            norm_a = self._normalize_path(pa)
            for pb in paths_b:
                norm_b = self._normalize_path(pb)
                # Nếu một đường dẫn là cha của đường dẫn kia -> Xung đột
                if norm_a.startswith(norm_b) or norm_b.startswith(norm_a):
                    return False
        return True

    def extract_paths_from_step(self, step: dict) -> Set[str]:
        """Trích xuất các đường dẫn mục tiêu."""
        paths = set()
        args = step.get("args", {}) or step.get("arguments", {})
        if isinstance(args, str):
            try:
                import json
                args = json.loads(args)
            except:
                args = {}

        if not isinstance(args, dict):
            return paths

        for key in ["path", "file", "filename", "filepath", "directory", "cwd", "target_file", "target_path"]:
            val = args.get(key)
            if val and isinstance(val, str):
                paths.add(val)
        
        cmd = args.get("command", "")
        if cmd:
            # Heuristic tìm đường dẫn trong lệnh
            parts = re.findall(r'[a-zA-Z0-9_\-\./\\]+', cmd)
            for p in parts:
                if "/" in p or "\\" in p or "." in p:
                    # Chúng ta khóa cả các file tiềm năng
                    paths.add(p)

        return paths

path_lock_registry = PathLockRegistry()

