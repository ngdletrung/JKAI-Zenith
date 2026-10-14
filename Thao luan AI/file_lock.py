import os
import re
import sys
import json
import time
import hashlib
import threading
import contextlib
from datetime import datetime
from pathlib import Path

LOCK_TIMEOUT = 30.0
BUSY_MAX_AGE_SECONDS = 30.0
POLL_INTERVAL = 0.05
MAX_DISCUSSION_LINES = 300
MAX_DISCUSSION_BYTES = 40 * 1024  # 40 KB

_thread_local = threading.local()

_TURN_BEGIN_RE = re.compile(r"<!--\s*TURN_BEGIN\b", re.DOTALL)
_TURN_END_FULL_RE = re.compile(r"<!--\s*TURN_END\s*\n(.*?)\n\s*-->", re.DOTALL)
_TURN_END_OPEN_RE = re.compile(r"<!--\s*TURN_END\b", re.DOTALL)


def _get_lock_counts():
    if not hasattr(_thread_local, "locks"):
        _thread_local.locks = {}
    return _thread_local.locks


@contextlib.contextmanager
def file_lock(filepath, timeout=LOCK_TIMEOUT):
    """
    Cross-platform re-entrant file lock using a dedicated lockfile (.lock).
    Supports re-entrancy within the same thread and atomic exclusion across processes/threads.
    """
    canonical_path = str(Path(filepath).resolve())
    lock_path = Path(f"{canonical_path}.lock")
    locks = _get_lock_counts()

    # Re-entrant support: if current thread already holds the lock, just increment depth
    if locks.get(canonical_path, 0) > 0:
        locks[canonical_path] += 1
        try:
            yield
        finally:
            locks[canonical_path] -= 1
        return

    start_time = time.time()
    fd = None

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(
                fd,
                f"PID:{os.getpid()} TID:{threading.get_ident()} TIME:{time.time()}\n".encode("utf-8"),
            )
            break
        except FileExistsError:
            try:
                mtime = lock_path.stat().st_mtime
                if time.time() - mtime > 60:
                    try:
                        lock_path.unlink()
                        continue
                    except Exception:
                        pass
            except Exception:
                pass

            if time.time() - start_time >= timeout:
                raise TimeoutError(f"Không thể khóa tệp {filepath} trong {timeout} giây.")
            time.sleep(POLL_INTERVAL)

    locks[canonical_path] = 1
    try:
        yield
    finally:
        locks[canonical_path] = 0
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        try:
            if lock_path.exists():
                lock_path.unlink()
        except Exception:
            pass


def is_file_busy(filepath, max_age_seconds: float = BUSY_MAX_AGE_SECONDS) -> bool:
    """
    Checks if a target file is currently being written by checking:
    1. Does a .tmp file exist and was modified within max_age_seconds (default 30.0s)?
    2. Does a .lock file exist and was modified within max_age_seconds (default 30.0s)?
    """
    target = Path(filepath)
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    canonical_path = str(target.resolve())
    lock_path = Path(f"{canonical_path}.lock")
    now = time.time()

    if tmp_path.exists():
        try:
            if now - tmp_path.stat().st_mtime < max_age_seconds:
                return True
        except Exception:
            pass

    if lock_path.exists():
        try:
            if now - lock_path.stat().st_mtime < max_age_seconds:
                return True
        except Exception:
            pass

    return False


def compute_turn_content_hash(body: str) -> str:
    """
    Computes deterministic 16-char SHA-256 hex digest of normalized Turn Block body.
    """
    normalized = (body or "").strip().replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def has_incomplete_turn_block(content: str) -> bool:
    """
    Detects partial/interrupted Turn Block writes in Noi dung thao luan.md:
    - More <!-- TURN_BEGIN markers than closed <!-- TURN_END ... --> blocks.
    - An unclosed <!-- TURN_END marker without closing -->.
    - A <!-- TURN_BEGIN marker appearing after the last closed <!-- TURN_END ... -->.
    """
    if not content:
        return False
    begin_matches = list(_TURN_BEGIN_RE.finditer(content))
    end_full_matches = list(_TURN_END_FULL_RE.finditer(content))
    end_open_matches = list(_TURN_END_OPEN_RE.finditer(content))

    if len(begin_matches) != len(end_full_matches):
        return True
    if len(end_open_matches) != len(end_full_matches):
        return True
    if begin_matches and end_full_matches:
        if begin_matches[-1].start() > end_full_matches[-1].start():
            return True
    return False


def atomic_write(filepath, content: str, encoding: str = "utf-8"):
    """
    Atomic write pattern: writes to .tmp file first, flushes, fsyncs, then atomically
    renames using os.replace().
    Guarantees no half-written or corrupted files during concurrent reads.
    """
    target = Path(filepath)
    tmp_path = target.with_suffix(target.suffix + ".tmp")

    with file_lock(filepath):
        with open(tmp_path, "w", encoding=encoding, newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)


def append_turn_block_atomic(filepath, turn_block_text: str, encoding: str = "utf-8"):
    """
    Atomically appends a complete Turn Block to Noi dung thao luan.md under file_lock.
    Refuses to write if turn_block_text itself is an incomplete Turn Block.
    """
    if has_incomplete_turn_block(turn_block_text):
        raise ValueError("Turn Block không hoàn chỉnh (thiếu TURN_BEGIN hoặc TURN_END đóng).")
    target = Path(filepath)
    with file_lock(str(target)):
        existing = target.read_text(encoding=encoding) if target.exists() else ""
        if has_incomplete_turn_block(existing):
            raise RuntimeError("Tệp thảo luận hiện đang chứa Turn Block ghi dở; từ chối ghi đè.")
        sep = "\n\n---\n\n" if existing.strip() and not existing.rstrip().endswith("---") else "\n\n"
        updated = existing.rstrip() + sep + turn_block_text.strip() + "\n"
        atomic_write(str(target), updated, encoding=encoding)


def read_locked(filepath, encoding: str = "utf-8") -> str:
    """Reads file under lock to ensure consistency."""
    with file_lock(filepath):
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()


def verify_and_archive_discussion(
    discussion_path,
    archive_path,
    pruned_content: str,
    turn_range: str,
    archive_content: str = None,
    manifest_path=None,
) -> dict:
    """
    P1-8 Safe Archive & Compaction with SHA-256 verification, duplicate guard, and rollback:
    1. Writes archive_content (or full current discussion) to archive_path atomically.
    2. Verifies archive_path exists on disk and SHA-256 matches expected hash.
    3. Verifies pruned_content obeys BOTH Hard Limits (< 300 lines AND < 40 KB) and has no incomplete blocks.
    4. Creates .bak of discussion_path, atomically writes pruned_content, and updates archive_manifest.json.
    5. Rolls back discussion_path from .bak if any post-write check fails.
    """
    disc_file = Path(discussion_path).resolve()
    arch_file = Path(archive_path).resolve()
    man_file = (
        Path(manifest_path).resolve()
        if manifest_path
        else disc_file.parent / "archive_manifest.json"
    )
    bak_file = disc_file.with_suffix(disc_file.suffix + ".bak")

    with file_lock(str(disc_file)):
        original_disc = disc_file.read_text(encoding="utf-8") if disc_file.exists() else ""
        content_to_archive = (archive_content if archive_content is not None else original_disc).replace("\r\n", "\n")
        if not content_to_archive.strip():
            raise ValueError("Nội dung lưu trữ (archive_content) rỗng.")

        # Validate pruned content BEFORE touching discussion file
        pruned_lines = pruned_content.splitlines()
        pruned_bytes = len(pruned_content.encode("utf-8"))
        if len(pruned_lines) >= MAX_DISCUSSION_LINES:
            raise ValueError(
                f"Bản cắt tỉa vi phạm trần {MAX_DISCUSSION_LINES} dòng ({len(pruned_lines)} dòng)."
            )
        if pruned_bytes >= MAX_DISCUSSION_BYTES:
            raise ValueError(
                f"Bản cắt tỉa vi phạm trần {MAX_DISCUSSION_BYTES} bytes ({pruned_bytes} bytes)."
            )
        if has_incomplete_turn_block(pruned_content):
            raise ValueError("Bản cắt tỉa chứa Turn Block không hoàn chỉnh.")

        expected_arch_sha = hashlib.sha256(content_to_archive.encode("utf-8")).hexdigest()

        # Check manifest for duplicate entry
        manifest = {"protocol_version": "2.3", "archives": []}
        if man_file.exists():
            try:
                manifest = json.loads(man_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        for entry in manifest.get("archives", []):
            if entry.get("archive_file") == arch_file.name and entry.get("sha256") == expected_arch_sha:
                break
        else:
            atomic_write(str(arch_file), content_to_archive, encoding="utf-8")

        # Verify archive on disk
        if not arch_file.exists():
            raise RuntimeError(f"Không tìm thấy tệp lưu trữ sau khi ghi: {arch_file}")
        disk_arch_text = arch_file.read_text(encoding="utf-8").replace("\r\n", "\n")
        disk_arch_bytes = disk_arch_text.encode("utf-8")
        disk_arch_sha = hashlib.sha256(disk_arch_bytes).hexdigest()
        if disk_arch_sha != expected_arch_sha:
            raise RuntimeError(
                f"Lỗi toàn vẹn SHA-256 tệp archive {arch_file.name}: kỳ vọng {expected_arch_sha}, thực tế {disk_arch_sha}"
            )

        # Backup current discussion file and write pruned content
        if original_disc:
            atomic_write(str(bak_file), original_disc, encoding="utf-8")

        try:
            atomic_write(str(disc_file), pruned_content, encoding="utf-8")
            verify_disc = disc_file.read_text(encoding="utf-8")
            if hashlib.sha256(verify_disc.encode("utf-8")).hexdigest() != hashlib.sha256(
                pruned_content.encode("utf-8")
            ).hexdigest():
                raise RuntimeError("Kiểm tra hash sau cắt tỉa thất bại.")
        except Exception as exc:
            if bak_file.exists():
                atomic_write(str(disc_file), bak_file.read_text(encoding="utf-8"), encoding="utf-8")
            raise RuntimeError(f"Cắt tỉa thất bại, đã rollback từ .bak: {exc}") from exc

        record = {
            "archive_file": arch_file.name,
            "turn_range": turn_range,
            "sha256": disk_arch_sha,
            "line_count": len(content_to_archive.splitlines()),
            "byte_size": len(disk_arch_bytes),
            "pruned_line_count": len(pruned_lines),
            "pruned_byte_size": pruned_bytes,
            "archived_at": datetime.now().isoformat(),
        }
        archives = [
            a for a in manifest.get("archives", []) if a.get("archive_file") != arch_file.name
        ]
        archives.append(record)
        manifest["archives"] = archives
        manifest["last_updated_at"] = datetime.now().isoformat()
        atomic_write(str(man_file), json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return record
