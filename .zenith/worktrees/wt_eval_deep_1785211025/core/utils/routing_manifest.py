from __future__ import annotations

import time
import hashlib
import hmac
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Union

# Giả định secret key cho việc ký (trong thực tế nên lấy từ biến môi trường)
_TOKEN_SECRET_KEY = b"zenith-zero-trust-secret-key-v1"

class ActionType(str, Enum):
    QUERY = "QUERY"
    EXECUTION = "EXECUTION"
    MODIFICATION = "MODIFICATION"
    SYSTEM_DESTRUCTIVE = "SYSTEM_DESTRUCTIVE"
    DATA_DESTRUCTIVE = "DATA_DESTRUCTIVE"
    NETWORK_DESTRUCTIVE = "NETWORK_DESTRUCTIVE"
    LEARNING = "LEARNING"
    SOCIAL = "SOCIAL"

@dataclass(frozen=True)
class RoutingManifest:
    """
    Hệ thần kinh định tuyến bất biến (Immutable Routing Manifest).
    Được tạo ra bởi Dispatcher, không được phép mutate bởi bất kỳ Node nào khác.
    """
    trace_id: str
    parent_trace_id: Optional[str]
    intent: str
    action_type: ActionType
    mode: str
    skill: Optional[str]
    confidence: float
    reasoning: str
    requires_planner: bool
    requires_memory: bool
    requires_llm: bool
    risk: str
    domain: str
    complexity: float
    telemetry: dict

@dataclass(frozen=True)
class CapabilityToken:
    """
    Zero-Trust Token cấp quyền cho Executor/Planner.
    Chứa chữ ký bảo mật để ngăn Agent tự "forge" token.
    """
    trace_id: str
    permissions: tuple[str, ...]
    sandbox_profile: str
    expires: float
    signature: str

    @classmethod
    def create(cls, trace_id: str, permissions: list[str], sandbox_profile: str, lifespan: float = 300.0) -> CapabilityToken:
        expires = time.time() + lifespan
        perm_str = ",".join(sorted(permissions))
        payload = f"{trace_id}:{perm_str}:{sandbox_profile}:{expires}"
        signature = hmac.new(_TOKEN_SECRET_KEY, payload.encode('utf-8'), hashlib.sha256).hexdigest()
        
        return cls(
            trace_id=trace_id,
            permissions=tuple(permissions),
            sandbox_profile=sandbox_profile,
            expires=expires,
            signature=signature
        )

    def verify(self) -> bool:
        if time.time() > self.expires:
            return False
        perm_str = ",".join(sorted(self.permissions))
        payload = f"{self.trace_id}:{perm_str}:{self.sandbox_profile}:{self.expires}"
        expected_sig = hmac.new(_TOKEN_SECRET_KEY, payload.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)
