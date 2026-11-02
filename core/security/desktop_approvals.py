# -*- coding: utf-8 -*-
"""
core/security/desktop_approvals.py
[D4: PENDING DESKTOP APPROVALS]

Shared store for live desktop mutation requests awaiting the Master's Ed25519
approval. The host agent writes a PENDING record; only
`scripts/master_desktop_approve.py` (Master-invoked, holding the private key)
may sign and execute it.

Records never authorize anything by themselves: the mutation server still
verifies the one-time lease and the Master approval envelope independently.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

import core.config  # noqa: F401  # loads .env before the settings below are read

APPROVALS_KEY = os.getenv("JKAI_DESKTOP_APPROVALS_KEY", "jkai:desktop:approvals")
APPROVAL_TTL_SECONDS = float(os.getenv("JKAI_DESKTOP_APPROVAL_TTL", "300"))
RECEIPTS_STREAM = os.getenv("JKAI_DESKTOP_RECEIPTS_STREAM", "jkai:desktop:receipts")

# role -> (url_env, password_env, user_env, default_user, password_alias_env)
ROLE_ENV = {
    "agent": ("JKAI_DESKTOP_REDIS_URL", "JKAI_DESKTOP_REDIS_PASSWORD",
              "JKAI_DESKTOP_REDIS_USER", "jkai-desktop", "JKAI_DESKTOP_AGENT_PASSWORD"),
    "tools": ("JKAI_DESKTOP_TOOL_REDIS_URL", "JKAI_DESKTOP_TOOL_REDIS_PASSWORD",
              "JKAI_DESKTOP_TOOL_REDIS_USER", "jkai-desktop-tool", "JKAI_DESKTOP_TOOL_PASSWORD"),
    "master": ("JKAI_DESKTOP_MASTER_REDIS_URL", "JKAI_DESKTOP_MASTER_REDIS_PASSWORD",
               "JKAI_DESKTOP_MASTER_REDIS_USER", "jkai-desktop-master", "JKAI_DESKTOP_MASTER_PASSWORD"),
}


def _docker_runtime() -> bool:
    try:
        from core.config import IS_DOCKER

        return bool(IS_DOCKER)
    except Exception:
        return os.path.exists("/.dockerenv")


def _require_dedicated() -> bool:
    return os.getenv("JKAI_DESKTOP_REQUIRE_DEDICATED", "0").strip().lower() in {
        "1", "true", "yes", "on"}


def desktop_redis_config(role: str = "agent", strict: Optional[bool] = None) -> Dict[str, Any]:
    """Resolve a role to connection settings without touching the network.

    `dedicated` is False when the role falls back to the shared admin
    credential; callers must report that instead of pretending it is scoped.
    With `JKAI_DESKTOP_REQUIRE_DEDICATED=1` (or `strict=True`) the fallback
    raises instead of silently widening privileges.
    """
    if role not in ROLE_ENV:
        raise ValueError(f"unknown desktop redis role: {role}")
    require = _require_dedicated() if strict is None else strict
    url_env, pass_env, user_env, default_user, alias_env = ROLE_ENV[role]
    own_url = os.getenv(url_env, "").strip()
    password = os.getenv(pass_env, "").strip() or os.getenv(alias_env, "").strip()
    username = os.getenv(user_env, "").strip() or default_user
    host = os.getenv("JKAI_DESKTOP_REDIS_HOST") or ("redis-ai" if _docker_runtime() else "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))

    if own_url:
        return {"role": role, "mode": "url", "url": own_url, "username": username,
                "dedicated": True}
    if password:
        return {"role": role, "mode": "direct", "host": host, "port": port,
                "username": username, "password": password, "dedicated": True}
    if require:
        raise RuntimeError(
            f"desktop redis role '{role}' is not dedicated: set {url_env} or {pass_env}; "
            "JKAI_DESKTOP_REQUIRE_DEDICATED=1 forbids the shared Redis credential")
    if _docker_runtime():
        shared_url = os.getenv("REDIS_URL", "").strip()
        if shared_url:
            return {"role": role, "mode": "url", "url": shared_url, "username": None,
                    "dedicated": False}
    return {"role": role, "mode": "direct", "host": host, "port": port,
            "username": None, "password": os.getenv("REDIS_PASSWORD") or None,
            "dedicated": False}


def redis_role_status(role: str = "agent") -> Dict[str, Any]:
    required = _require_dedicated()
    config = desktop_redis_config(role, strict=False)
    return {"role": role, "dedicated": config["dedicated"], "mode": config["mode"],
            "username": config.get("username"), "dedicated_required": required,
            "ok": config["dedicated"] or not required}


def desktop_redis_client(role: str = "agent", socket_timeout: float = 5,
                         socket_connect_timeout: float = 3):
    import redis

    config = desktop_redis_config(role)
    if config["mode"] == "url":
        return redis.Redis.from_url(
            config["url"], socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout, decode_responses=True,
        )
    return redis.Redis(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=config["password"],
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        decode_responses=True,
    )


def canonical_digest(record: Dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_CLAIM_LUA = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then return nil end
local rec = cjson.decode(raw)
if rec['status'] ~= 'PENDING_APPROVAL' then return nil end
rec['status'] = ARGV[2]
rec['claimed_at'] = tonumber(ARGV[3])
rec['claimed_by'] = ARGV[4]
if ARGV[5] ~= '' then rec['session_id'] = ARGV[5] end
local encoded = cjson.encode(rec)
redis.call('HSET', KEYS[1], ARGV[1], encoded)
return encoded
"""


class PendingApprovalStore:
    def __init__(self, client=None) -> None:
        self._client = client

    def _redis(self):
        if self._client is None:
            self._client = desktop_redis_client()
        return self._client

    @property
    def client(self):
        """The client this store writes through (so receipts use the same role)."""
        return self._redis()

    def put(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        record.setdefault("created_at", time.time())
        record.setdefault("expires_at", record["created_at"] + APPROVAL_TTL_SECONDS)
        record.setdefault("status", "PENDING_APPROVAL")
        self._redis().hset(APPROVALS_KEY, record["request_id"],
                           json.dumps(record, ensure_ascii=False))
        self._redis().expire(APPROVALS_KEY, int(APPROVAL_TTL_SECONDS) + 60)
        return record

    def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        raw = self._redis().hget(APPROVALS_KEY, request_id)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def update(self, request_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        record = self.get(request_id)
        if record is None:
            return None
        record.update(fields)
        self._redis().hset(APPROVALS_KEY, request_id, json.dumps(record, ensure_ascii=False))
        return record

    def claim(self, request_id: str, claimed_by: str, session_id: str = "",
              status: str = "APPROVAL_IN_PROGRESS") -> Optional[Dict[str, Any]]:
        """Atomic PENDING -> IN_PROGRESS claim; only one approver may win."""
        raw = self._redis().eval(
            _CLAIM_LUA, 1, APPROVALS_KEY, request_id, status, str(time.time()), claimed_by, session_id or ""
        )
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def revert_claim(self, request_id: str, claimed_by: str) -> Optional[Dict[str, Any]]:
        """Return an unexecuted claim to PENDING_APPROVAL (only by its claimant)."""
        record = self.get(request_id)
        if record is None or record.get("status") != "APPROVAL_IN_PROGRESS":
            return record
        if record.get("claimed_by") != claimed_by:
            return record
        record.pop("claimed_at", None)
        record.pop("claimed_by", None)
        record["status"] = "PENDING_APPROVAL"
        self._redis().hset(APPROVALS_KEY, request_id, json.dumps(record, ensure_ascii=False))
        return record

    def list_all(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        raw = self._redis().hgetall(APPROVALS_KEY)
        records = []
        for value in raw.values():
            try:
                record = json.loads(value)
            except Exception:
                continue
            if not include_resolved and record.get("status") != "PENDING_APPROVAL":
                continue
            records.append(record)
        records.sort(key=lambda r: r.get("created_at", 0))
        return records


def publish_receipt(receipt: Dict[str, Any], client=None) -> Dict[str, Any]:
    redis = client or desktop_redis_client()
    redis.xadd(RECEIPTS_STREAM, {
        "request_id": str(receipt.get("request_id", "")),
        "kind": str(receipt.get("kind", "act")),
        "payload": json.dumps(receipt, ensure_ascii=False),
    }, maxlen=5000, approximate=True)
    return receipt
