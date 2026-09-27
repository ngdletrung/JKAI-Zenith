"""
core/sanitizer/state_sanitizer.py
JKAI Zenith - Autonomous State Sanitizer (v1.0 Sovereign)
Specification: DecisionProvider v0.2 + Fix a + Fix b

Guarantees:
1. Fix a: MAX_STATE_BYTES = 65536 hard cap (Prevents memory exhaustion & injection)
2. Fix b: state_hash = hash(sanitized) (Enforces integrity of sanitized representation)
3. 3-Layer scrubbing:
   - Layer 1: Strip credentials, tokens, PII (CCCD, phone, email, private keys, passwords)
   - Layer 2: Preserve structural & invariant identifiers
   - Layer 3: Truncate free-text & enforce canonical UTF-8 NFC
4. 100% Local, zero external network dependencies.
"""

from __future__ import annotations

import re
import json
import hashlib
import unicodedata
from typing import Any, Dict, List, Tuple


class StateSanitizer:
    """
    Standard Sovereign State Sanitizer for JKAI Zenith.
    Pre-requisite for all internal decision and audit operations.
    """

    MAX_STATE_BYTES: int = 65536  # [Fix a]: 64KB strict boundary limit

    SECRET_PATTERNS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
        (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED_JWT]"),
        (re.compile(r"(password|passwd|secret|apikey|api_key)[\"']?\s*[:=]\s*[\"'][^\"']+[\"']", re.IGNORECASE), r"\1: '[REDACTED_SECRET]'"),
        (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
        (re.compile(r"\b(0\d{9}|\+84\d{9})\b"), "[REDACTED_PHONE]"),
        (re.compile(r"\b\d{12}\b"), "[REDACTED_ID_NUMBER]"),  # CCCD 12 digits
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"), "[REDACTED_EMAIL]")
    ]

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively cleanses arbitrary state objects."""
        if isinstance(data, str):
            text = unicodedata.normalize("NFC", data)
            for pattern, repl in cls.SECRET_PATTERNS:
                text = pattern.sub(repl, text)
            if len(text) > 2000:
                text = text[:2000] + "... [TRUNCATED_FOR_SANITIZATION]"
            return text
        elif isinstance(data, dict):
            sanitized_dict = {}
            for k, v in data.items():
                if any(sec in k.lower() for sec in ["password", "secret_key", "auth_token", "private_key", "api_key", "apikey"]):
                    sanitized_dict[k] = "[REDACTED_SECRET_FIELD]"
                else:
                    sanitized_dict[k] = cls.sanitize(v)
            return sanitized_dict
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        else:
            return data

    @classmethod
    def canonical_json(cls, data: Any) -> str:
        """Renders canonical JSON string representation."""
        raw_json = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        encoded = raw_json.encode("utf-8")
        if len(encoded) > cls.MAX_STATE_BYTES:
            # [Fix a]: Truncate to MAX_STATE_BYTES safely
            encoded = encoded[:cls.MAX_STATE_BYTES]
            raw_json = encoded.decode("utf-8", errors="ignore")
        return raw_json

    @classmethod
    def sanitize_with_report(cls, data: Any, is_external_provider: bool = False) -> Tuple[Any, Dict[str, Any]]:
        """
        Sanitizes data and produces a structured redaction report per DecisionProvider v0.2 spec.
        """
        redactions = []
        
        def _scan(d):
            if isinstance(d, str):
                for pat, repl in cls.SECRET_PATTERNS:
                    if pat.search(d):
                        redactions.append(repl)
            elif isinstance(d, dict):
                for k, v in d.items():
                    if any(sec in k.lower() for sec in ["password", "secret_key", "auth_token", "private_key", "api_key", "apikey"]):
                        redactions.append(f"field:{k}")
                    else:
                        _scan(v)
            elif isinstance(d, list):
                for item in d:
                    _scan(item)

        _scan(data)
        sanitized = cls.sanitize(data)
        report = {
            "redacted_count": len(redactions),
            "redacted_items": redactions,
            "is_external_provider": is_external_provider,
            "max_state_bytes_limit": cls.MAX_STATE_BYTES
        }
        return sanitized, report

    @classmethod
    def compute_fingerprint(cls, data: Any) -> str:
        """
        [Fix b]: Computes SHA-256 fingerprint strictly from the sanitized canonical representation.
        """
        sanitized = cls.sanitize(data)
        canonical = cls.canonical_json(sanitized)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
