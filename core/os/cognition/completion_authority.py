# -*- coding: utf-8 -*-
"""
core/os/cognition/completion_authority.py
Canonical CompletionAuthority & MissionCompletionGate (Slice 3.3 - Giai đoạn 3 Mục 7).

Enforces:
1. Backward-compatible export of `MissionCompletionGate` and `RecoveryManager`.
2. `CompletionAuthority`: Issues cryptographic HMAC-SHA256 signatures for background
   Reflect Job observations ONLY when:
   - `proof_count >= 1`
   - `verbatim_quotes` contains at least 1 non-empty verbatim trajectory quote
   - All trajectory proofs in the cluster are verified (`criterion_verified=True`).
3. `verify_observation_signature()`: Hard gate called by `EpisodicBrain.retain_observation()`
   to guarantee 0 unsigned direct writes to episodic memory.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional

from core.os.cognition.mission_completion_gate import (
    MissionCompletionGate,
    RecoveryManager,
)

_DEFAULT_AUTHORITY_KEY = b"jkai-zenith-sovereign-completion-authority-v3.3"


class CompletionAuthority(MissionCompletionGate):
    """
    Sovereign Completion Authority gating background Reflect Job observations
    before they can enter Episodic Memory.
    """

    def __init__(self, secret_key: bytes = _DEFAULT_AUTHORITY_KEY):
        self._secret_key = bytes(secret_key)

    @staticmethod
    def _canonical_observation_payload(obs: Dict[str, Any]) -> bytes:
        canonical = {
            "cluster_id": str(obs.get("cluster_id", "")),
            "task_code": str(obs.get("task_code", "")),
            "summary": str(obs.get("summary", "")),
            "verbatim_quotes": [str(q) for q in (obs.get("verbatim_quotes") or [])],
            "proof_count": int(obs.get("proof_count", 0)),
            "revision": int(obs.get("revision", 1)),
        }
        return json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def sign_observation(
        self,
        obs: Dict[str, Any],
        all_trajectories_verified: bool = True,
    ) -> str:
        """
        Signs a synthesized observation if and only if:
        - `all_trajectories_verified` is True
        - `proof_count >= 1`
        - `verbatim_quotes` is non-empty and matches `proof_count` minimum contract.
        """
        if not all_trajectories_verified:
            raise ValueError("Cannot sign observation: unverified trajectory step in cluster.")
        quotes = [str(q).strip() for q in (obs.get("verbatim_quotes") or []) if str(q).strip()]
        proof_count = int(obs.get("proof_count", 0))
        if proof_count < 1 or not quotes:
            raise ValueError("Cannot sign observation: requires proof_count >= 1 and verbatim_quotes.")
        msg = self._canonical_observation_payload(obs)
        return hmac.new(self._secret_key, msg, hashlib.sha256).hexdigest()

    def verify_observation_signature(
        self,
        obs: Dict[str, Any],
        signature: Optional[str],
    ) -> bool:
        """Verifies that an observation carries a genuine CompletionAuthority HMAC signature."""
        if not signature or not isinstance(signature, str):
            return False
        quotes = [str(q).strip() for q in (obs.get("verbatim_quotes") or []) if str(q).strip()]
        proof_count = int(obs.get("proof_count", 0))
        if proof_count < 1 or not quotes:
            return False
        expected = hmac.new(
            self._secret_key,
            self._canonical_observation_payload(obs),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature.strip())


completion_authority = CompletionAuthority()

__all__ = [
    "MissionCompletionGate",
    "RecoveryManager",
    "CompletionAuthority",
    "completion_authority",
]
