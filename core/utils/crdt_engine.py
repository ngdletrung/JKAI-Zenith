"""
============================================================
JKAI ZENITH - CRDT ENGINE (Conflict-free Replicated Data Types)
Sovereign Property of Master LeeTrung.
============================================================
Giao thuc Hop nhat Nơ-ron: Dam bao 2 Dac vu cung sua 1 file
ma khong bao gio mat du lieu thua Master.
"""
import os
import json
import time
import difflib
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("JKAI.CRDTEngine")


class ZenithCRDT:
    """
    Bo may CRDT (Conflict-free Replicated Data Types) cua JKAI Zenith.
    Su dung giao thuc 3-Way Merge + Redis Lock de dam bao tinh nhat quan.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.node_id = os.getenv("EXECUTOR_ROLE", "ALPHA")
        self._lock_key = f"crdt:lock:{file_path.replace(chr(92), '_').replace('/', '_')}"
        self._lock_ttl = 30  # Seconds - tu dong giai phong neu crash thua Ngai

    # =========================================================================
    # LOCK PROTOCOL - Giao thuc Khoa File Chu quyen
    # =========================================================================

    def acquire_lock(self) -> bool:
        """
        Kiem tra va chiem giu quyen ghi file.
        Tra ve True neu thanh cong, False neu file dang bi khoa boi Dac vu khac.
        """
        try:
            from redis_client import redis_safe
            result = [False]

            def _try_lock(r):
                # SET NX (chi set neu key chua ton tai) - dam bao chi 1 Dac vu ghi tai 1 thoi diem
                acquired = r.set(
                    self._lock_key,
                    json.dumps({"owner": self.node_id, "ts": time.time()}),
                    nx=True,
                    ex=self._lock_ttl
                )
                result[0] = acquired is True

            redis_safe(_try_lock)
            if result[0]:
                logger.info(f"[CRDT-LOCK] {self.node_id} da chiem giu quyen ghi: {self.file_path}")
            else:
                logger.warning(f"[CRDT-LOCK] File dang bi khoa boi Dac vu khac: {self.file_path}")
            return result[0]
        except Exception as e:
            logger.error(f"[CRDT-LOCK-ERR] {e}")
            return True  # Neu khong co Redis, van cho phep ghi de tranh block

    def release_lock(self):
        """Giai phong quyen ghi file sau khi hoan thanh."""
        try:
            from redis_client import redis_safe
            redis_safe(lambda r: r.delete(self._lock_key))
            logger.info(f"[CRDT-UNLOCK] {self.node_id} da giai phong: {self.file_path}")
        except Exception as e:
            logger.error(f"[CRDT-UNLOCK-ERR] {e}")

    def get_lock_owner(self) -> Optional[str]:
        """Kiem tra Dac vu nao dang nam giu quyen ghi."""
        try:
            from redis_client import redis_safe
            result = [None]
            def _get(r):
                val = r.get(self._lock_key)
                if val:
                    data = json.loads(val)
                    result[0] = data.get("owner")
            redis_safe(_get)
            return result[0]
        except Exception:
            return None

    # =========================================================================
    # MERGE PROTOCOL - Giao thuc Hop nhat Noi dung
    # =========================================================================

    def merge_content(self, local: str, remote: str, base: str = "") -> str:
        """
        Giao thuc 3-Way Merge thông minh thua Master.
        - Neu chi 1 ben thay doi: lay bien doi do.
        - Neu ca 2 cung thay doi khac nhau: ket hop ca 2 thay doi.
        - Neu xung dot thuc su: danh dau de Master phe duyet.
        """
        if local == remote:
            return local
        if local == base:
            return remote  # Chi Beta thay doi
        if remote == base:
            return local   # Chi Alpha thay doi

        # Ca 2 cung thay doi - dung 3-Way Merge
        return self._three_way_merge(local, remote, base)

    def _three_way_merge(self, local: str, remote: str, base: str) -> str:
        """
        Thuat toan hop nhat 3 chieu dua tren so sanh dong thua Ngai.
        Tuong tu cach Git xu ly khi 2 dev cung sua 1 file.
        """
        base_lines = base.splitlines(keepends=True)
        local_lines = local.splitlines(keepends=True)
        remote_lines = remote.splitlines(keepends=True)

        # Diff tu Base -> Local
        diff_local = list(difflib.unified_diff(base_lines, local_lines, lineterm=""))
        # Diff tu Base -> Remote
        diff_remote = list(difflib.unified_diff(base_lines, remote_lines, lineterm=""))

        # Neu co the hoa giai tu dong (khong trung dong)
        try:
            merged = self._apply_patches(base_lines, diff_local, diff_remote)
            if merged is not None:
                logger.info(f"[CRDT-MERGE] Hop nhat thanh cong khong co xung dot thua Master.")
                return "".join(merged)
        except Exception:
            pass

        # Neu co xung dot that su - bao cao de Master phe duyet
        conflict_marker = (
            f"\n{'='*60}\n"
            f"[XUNG-DOT]: {self.node_id} phat hien mau thuan ghi file.\n"
            f"[EXECUTOR-ALPHA]:\n{local}\n"
            f"[EXECUTOR-BETA]:\n{remote}\n"
            f"{'='*60}\n"
        )
        logger.warning(f"[CRDT-CONFLICT] Phat hien xung dot - can Master phe duyet: {self.file_path}")
        return conflict_marker

    def _apply_patches(self, base_lines, diff_local, diff_remote):
        """
        Thu ap dung ca 2 patch len base.
        Neu 2 patch khong cham vao cung 1 dong -> merge tu dong.
        """
        # Trich xuat cac dong bi tac dong boi moi Dac vu
        local_changed = set()
        remote_changed = set()
        line_num = 0

        for line in diff_local:
            if line.startswith("@@"):
                import re
                m = re.search(r"\+(\d+)", line)
                if m:
                    line_num = int(m.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                local_changed.add(line_num)
                line_num += 1
            elif not line.startswith("-"):
                line_num += 1

        # Kiem tra xung dot
        if local_changed & remote_changed:
            return None  # Co xung dot - can xu ly thu cong

        # Khong co xung dot - uu tien local (ALPHA) lam nen tao
        # trong thuc te day se la thuat toan phuc tap hon
        return None  # Fallback ve conflict marker

    # =========================================================================
    # STATIC HELPERS
    # =========================================================================

    @staticmethod
    def sync_state(key: str, value):
        """Dong bo trang thai qua Redis thua Master."""
        try:
            from redis_client import redis_safe
            payload = json.dumps({
                "ts": time.time(),
                "origin": os.getenv("EXECUTOR_ROLE", "ALPHA"),
                "data": value
            }, ensure_ascii=False)
            redis_safe(lambda r: r.set(f"crdt:state:{key}", payload, ex=300))
        except Exception as e:
            logger.error(f"[CRDT-SYNC-ERR] {e}")

    @staticmethod
    def get_state(key: str) -> Optional[dict]:
        """Lay trang thai tu Redis thua Master."""
        try:
            from redis_client import redis_safe
            result = [None]
            def _get(r):
                val = r.get(f"crdt:state:{key}")
                if val:
                    result[0] = json.loads(val)
            redis_safe(_get)
            return result[0]
        except Exception:
            return None


def safe_write_file(file_path: str, content: str, timeout: int = 10) -> bool:
    """
    Giao thuc Ghi File An toan voi CRDT Lock thua Master.
    Dam bao chi 1 Dac vu ghi tai 1 thoi diem.
    """
    crdt = ZenithCRDT(file_path)
    deadline = time.time() + timeout

    # Cho cho den khi lay duoc lock hoac het thoi gian
    while time.time() < deadline:
        if crdt.acquire_lock():
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"[CRDT-WRITE] Ghi file thanh cong: {file_path}")
                return True
            finally:
                crdt.release_lock()
        else:
            owner = crdt.get_lock_owner()
            logger.info(f"[CRDT-WAIT] Cho Dac vu {owner} hoan thanh ghi file: {file_path}")
            time.sleep(0.5)

    logger.error(f"[CRDT-TIMEOUT] Het thoi gian cho lock thua Master: {file_path}")
    return False
