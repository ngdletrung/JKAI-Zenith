import os
import sys
import time
import threading
import contextlib
from pathlib import Path

LOCK_TIMEOUT = 30.0
POLL_INTERVAL = 0.05

_thread_local = threading.local()

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
            os.write(fd, f"PID:{os.getpid()} TID:{threading.get_ident()} TIME:{time.time()}\n".encode("utf-8"))
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

def is_file_busy(filepath, max_age_seconds: float = 15.0) -> bool:
    """
    Checks if a target file is currently being written by checking:
    1. Does a .tmp file exist and was modified within max_age_seconds?
    2. Does a .lock file exist and was modified within max_age_seconds?
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

def atomic_write(filepath, content: str, encoding: str = "utf-8"):
    """
    Atomic write pattern: writes to .tmp file first, flushes, fsyncs, then atomically
    renames using os.replace().
    Guarantees no half-written or corrupted files during concurrent reads.
    """
    target = Path(filepath)
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    
    with file_lock(filepath):
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)

def read_locked(filepath, encoding: str = "utf-8") -> str:
    """Reads file under lock to ensure consistency."""
    with file_lock(filepath):
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()
