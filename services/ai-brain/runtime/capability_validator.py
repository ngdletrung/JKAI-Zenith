from dataclasses import dataclass
from typing import Tuple
import hashlib
import time

@dataclass(frozen=True)
class CapabilityToken:
    """
    🔐 Mã Báo Chủ Quyền (Signed Capability Token)
    Không thể làm giả bởi Planner hay Executor.
    """
    trace_id: str
    subject: str
    permissions: Tuple[str, ...]
    scope: Tuple[str, ...]
    issued_at: float
    expires_at: float
    signature: str

class CapabilityValidator:
    """Chuyên cấp phát và xác thực chữ ký (HMAC) cho Token."""
    def __init__(self, secret_key: str):
        self.secret = secret_key

    def _sign(self, trace_id: str, subject: str, expires_at: float) -> str:
        raw = f"{trace_id}:{subject}:{expires_at}:{self.secret}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def issue_token(self, trace_id: str, subject: str, permissions: list, scope: list, ttl: int = 600) -> CapabilityToken:
        now = time.time()
        expires = now + ttl
        sig = self._sign(trace_id, subject, expires)
        return CapabilityToken(
            trace_id=trace_id,
            subject=subject,
            permissions=tuple(permissions),
            scope=tuple(scope),
            issued_at=now,
            expires_at=expires,
            signature=sig
        )

    def verify(self, token: CapabilityToken) -> bool:
        if time.time() > token.expires_at:
            return False
        expected_sig = self._sign(token.trace_id, token.subject, token.expires_at)
        return token.signature == expected_sig
