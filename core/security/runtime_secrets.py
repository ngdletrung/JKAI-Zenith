# -*- coding: utf-8 -*-
"""
core/security/runtime_secrets.py
[RUNTIME TRANSPORT SECRETS — JKAI TỰ SINH, MỘT CHỦ SỞ HỮU]

Token vận chuyển (WS stream + bearer của host_bridge 9997) KHÔNG cần Master gõ tay.
Module này là chủ sở hữu duy nhất:
  - sinh token khi chưa có (idempotent, có khóa chống race giữa host và container),
  - đọc token với thứ tự ưu tiên: process env > .env > data/runtime_secrets/runtime_tokens.env,
  - cache theo mtime để rotation được nhận ra mà không cần khởi động lại.

Ranh giới bảo mật:
  - KHÔNG sinh, KHÔNG ký, KHÔNG pin khóa Master Authority Ed25519. Khóa đó là
    trust anchor: pin công khai nằm ở config/security/master_public_keys.json và
    chỉ con người được quyết định.
  - Container chỉ đọc (/shared/runtime_secrets mount read-only); host_bridge là writer duy nhất.
  - Không bao giờ ghi log giá trị token, chỉ fingerprint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

RUNTIME_SECRETS_ENV = "JKAI_RUNTIME_SECRETS_FILE"
TOKEN_FILENAME = "runtime_tokens.env"
META_FILENAME = "runtime_tokens.json"
GENERATOR = "core/security/runtime_secrets.py v1"

TOKEN_BYTES = 48
MIN_TOKEN_LENGTH = 32
LEGACY_TOKENS = frozenset({"jkai_ws_read_only_stream_token_v3"})
TOKEN_KEYS = ("SATELLITE_WS_TOKEN", "SATELLITE_AUTH_TOKEN")

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_LOCK_SUFFIX = ".lock"
_LOCK_STALE_SECONDS = 15.0

_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, object] = {"path": None, "stamp": None, "data": {}}


# ─────────────────────────────────────────────
# Đường dẫn & parsing
# ─────────────────────────────────────────────
def candidate_paths() -> List[Path]:
    """Vị trí chứa file token. Biến JKAI_RUNTIME_SECRETS_FILE (nếu đặt) là quyết định duy nhất."""
    override = os.environ.get(RUNTIME_SECRETS_ENV, "").strip()
    if override:
        return [Path(override)]

    # Host: <repo>/data/runtime_secrets/...; Container: /shared/runtime_secrets/... (ro)
    # Tách khỏi data/secrets/ để KHÔNG bao giờ mount chung thư mục khóa Master vào container.
    candidates: List[Path] = [
        PACKAGE_ROOT / "data" / "runtime_secrets" / TOKEN_FILENAME,
        PACKAGE_ROOT / "runtime_secrets" / TOKEN_FILENAME,
        Path.cwd() / "data" / "runtime_secrets" / TOKEN_FILENAME,
    ]
    unique: List[Path] = []
    seen = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _default_write_path() -> Path:
    """Vị trí ghi được. Nếu không có, trả về file đang đọc — không bao giờ sinh token thứ hai."""
    candidates = candidate_paths()
    for path in candidates:
        if path.parent.is_dir() and os.access(path.parent, os.W_OK):
            return path
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def parse_env_text(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        values[key] = value.strip().strip("'").strip('"')
    return values


def read_secret_file(path: Path) -> Dict[str, str]:
    try:
        return parse_env_text(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def active_path() -> Optional[Path]:
    for path in candidate_paths():
        if path.exists():
            return path
    return None


def runtime_tokens() -> Dict[str, str]:
    """Đọc token từ file đầu tiên tồn tại; cache theo (mtime_ns, size)."""
    path = active_path()
    if path is None:
        return {}
    try:
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return {}

    with _CACHE_LOCK:
        if _CACHE["path"] == path and _CACHE["stamp"] == stamp:
            return dict(_CACHE["data"])  # type: ignore[arg-type]
        data = read_secret_file(path)
        _CACHE.update({"path": path, "stamp": stamp, "data": data})
        return dict(data)


def get_secret(name: str, default: str = "") -> str:
    """Env thắng file; trả default nếu không cấu hình ở đâu cả."""
    value = (os.environ.get(name) or "").strip()
    if value:
        return value
    return (runtime_tokens().get(name) or default).strip()


def fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def is_usable_token(token: str) -> bool:
    token = (token or "").strip()
    return len(token) >= MIN_TOKEN_LENGTH and token not in LEGACY_TOKENS


# ─────────────────────────────────────────────
# Sinh & ghi (chỉ host)
# ─────────────────────────────────────────────
def _write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _acquire_lock(lock_path: Path, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > _LOCK_STALE_SECONDS:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)
        except OSError:
            return False


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


def _collect_configured(
    process_env: Dict[str, str], dotenv_path: Optional[Path], previous: Dict[str, str]
) -> Tuple[Dict[str, str], Dict[str, str]]:
    dotenv = read_secret_file(dotenv_path) if dotenv_path else {}
    tokens: Dict[str, str] = {}
    sources: Dict[str, str] = {}
    for key in TOKEN_KEYS:
        from_env = (process_env.get(key) or "").strip()
        from_dotenv = (dotenv.get(key) or "").strip()
        from_file = (previous.get(key) or "").strip()
        if is_usable_token(from_env):
            tokens[key], sources[key] = from_env, "environment"
        elif is_usable_token(from_dotenv):
            tokens[key], sources[key] = from_dotenv, "dotenv"
        elif is_usable_token(from_file):
            tokens[key], sources[key] = from_file, "runtime_file"
        else:
            tokens[key], sources[key] = "", "missing"
    return tokens, sources


def _render_env_file(tokens: Dict[str, str]) -> str:
    lines = [
        "# Generated by core/security/runtime_secrets.py — KHÔNG commit (data/runtime_secrets/ đã gitignore).",
        f"# generated_at_utc={datetime.now(timezone.utc).isoformat()}",
        "# Consumers: scripts/host_bridge.py (9997) + host_satellite skills (bearer).",
    ]
    lines.extend(f"{key}={tokens[key]}" for key in TOKEN_KEYS)
    return "\n".join(lines) + "\n"


def _render_meta(tokens: Dict[str, str], sources: Dict[str, str], path: Path) -> str:
    meta = {
        "generator": GENERATOR,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "plaintext_file": path.name,
        "tokens": {
            key: {
                "source": sources[key],
                "length": len(tokens[key]),
                "fingerprint_sha256_16": fingerprint(tokens[key]),
            }
            for key in TOKEN_KEYS
        },
        "master_authority_key": "NOT_GENERATED (trust anchor, pin do Master quyết định)",
        "mutation_enabled": "unchanged",
    }
    return json.dumps(meta, ensure_ascii=False, indent=2) + "\n"


def _summary(tokens: Dict[str, str], sources: Dict[str, str]) -> Dict[str, Dict[str, object]]:
    return {
        key: {
            "source": sources[key],
            "length": len(tokens[key]),
            "fingerprint_sha256_16": fingerprint(tokens[key]) if tokens[key] else "",
        }
        for key in TOKEN_KEYS
    }


def _seed_previous(target: Path) -> Dict[str, str]:
    """Token đã có ở target; nếu thiếu thì mượn token đang hiệu lực (env/.env/file active)."""
    previous = read_secret_file(target)
    if all(is_usable_token(previous.get(key, "")) for key in TOKEN_KEYS):
        return previous
    active = runtime_tokens()
    return {**active, **{k: v for k, v in previous.items() if v}}


def ensure_runtime_tokens(
    path: Optional[Path] = None,
    dotenv_path: Optional[Path] = None,
    rotate: bool = False,
    process_env: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """
    Bảo đảm file token tồn tại và đủ mạnh. Idempotent, an toàn khi host + nhiều container
    cùng gọi: chỉ writer đầu tiên sinh token, các bên sau đọc lại file.
    """
    target = Path(path) if path else _default_write_path()
    env = dict(os.environ if process_env is None else process_env)

    if not target.parent.is_dir():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return {"ok": False, "status": "read_only", "path": str(target), "tokens": {}}
    if not os.access(target.parent, os.W_OK):
        # Container: /shared/runtime_secrets là read-only — chỉ đọc, không bao giờ tự sinh.
        current = read_secret_file(target)
        sources = {
            key: ("runtime_file" if is_usable_token(current.get(key, "")) else "missing")
            for key in TOKEN_KEYS
        }
        return {
            "ok": all(is_usable_token(current.get(key, "")) for key in TOKEN_KEYS),
            "status": "read_only",
            "path": str(target),
            "tokens": _summary({key: current.get(key, "") for key in TOKEN_KEYS}, sources),
        }

    lock_path = target.with_name(target.name + _LOCK_SUFFIX)
    if not _acquire_lock(lock_path):
        current = read_secret_file(target)
        if all(is_usable_token(current.get(key, "")) for key in TOKEN_KEYS):
            sources = {key: "runtime_file" for key in TOKEN_KEYS}
            return {
                "ok": True,
                "status": "lock_wait_fallback",
                "path": str(target),
                "tokens": _summary({k: current[k] for k in TOKEN_KEYS}, sources),
            }
        return {"ok": False, "status": "lock_timeout", "path": str(target), "tokens": {}}

    try:
        previous = _seed_previous(target)
        tokens, sources = _collect_configured(env, dotenv_path, previous)
        if rotate:
            for key in TOKEN_KEYS:
                if sources[key] in ("environment", "dotenv"):
                    # Đang được .env/process env ép giá trị: sinh token khác sẽ làm lệch hai đầu.
                    continue
                tokens[key] = secrets.token_urlsafe(TOKEN_BYTES)
                sources[key] = "rotated" if sources[key] == "runtime_file" else "generated"
        for key in TOKEN_KEYS:
            if not tokens[key]:
                tokens[key] = secrets.token_urlsafe(TOKEN_BYTES)
                sources[key] = "generated"

        rendered = _render_env_file(tokens)
        existed = target.exists()
        unchanged = existed and read_secret_file(target) == {k: tokens[k] for k in TOKEN_KEYS}
        _CACHE.update({"path": None, "stamp": None, "data": {}})
        if not unchanged:
            _write_private(target, rendered)
            _write_private(target.with_name(META_FILENAME), _render_meta(tokens, sources, target))
        return {
            "ok": True,
            "status": "unchanged" if unchanged else ("rotated" if rotate else "written"),
            "path": str(target),
            "tokens": _summary(tokens, sources),
        }
    finally:
        _release_lock(lock_path)


# ─────────────────────────────────────────────
# Xác thực bearer dùng chung
# ─────────────────────────────────────────────
def authorize_bearer(presented: str, expected: str) -> Tuple[bool, str]:
    """
    Fail-closed: chưa cấu hình token => từ chối mọi request bảo vệ (AUTH_NOT_CONFIGURED).
    So sánh hằng thời gian để tránh timing attack.
    """
    expected = (expected or "").strip()
    if not expected:
        return False, "AUTH_NOT_CONFIGURED"
    if not (presented or "").strip():
        return False, "AUTH_REQUIRED"
    if hmac.compare_digest(presented.strip().encode("utf-8"), expected.encode("utf-8")):
        return True, "AUTHORIZED"
    return False, "AUTH_INVALID"


def iter_token_fingerprints(tokens: Dict[str, str]) -> Iterable[Tuple[str, str]]:
    for key in TOKEN_KEYS:
        value = tokens.get(key, "")
        yield key, (fingerprint(value) if value else "")
