"""
core/os/cognition/fast_governor.py
Fast Execution Governor & Capability Token Grant Gate.

Enforces:
- Decision != Authorization: LLM ActionIntent is just a proposal until Governor issues a CapabilityGrant.
- Scoped Sandboxing: Grants only minimal required capabilities (e.g. FILE_CREATE without raw OS execution).
- Destructive Command Interception.
"""

import hashlib
import os
import re
import time
from typing import Set
from core.os.cognition.fast_schemas import (
    ActionIntent,
    CapabilityGrant,
    TaskDomain,
    MutationScope,
)

FORBIDDEN_MUTATIONS = [
    r"rm\s+-rf\s+/",
    r"drop\s+database",
    r"truncate\s+table",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\{ :\|:& \};:",
]


class FastGovernor:
    """Lightweight deterministic governor for the FAST pipeline."""

    def __init__(self, sandbox_root: str = "d:/Docker/JKAI/files/Output"):
        self.sandbox_root = sandbox_root

    def evaluate_intent(self, intent: ActionIntent) -> CapabilityGrant:
        grant_id = f"grant_{hashlib.sha256(f'{intent.intent_id}:{time.time()}'.encode()).hexdigest()[:12]}"
        
        # 1. Check for catastrophic destructive patterns in parameters
        params_str = str(intent.parameters)
        for pattern in FORBIDDEN_MUTATIONS:
            if re.search(pattern, params_str, re.IGNORECASE):
                return CapabilityGrant(
                    grant_id=grant_id,
                    intent_id=intent.intent_id,
                    allowed=False,
                    granted_capabilities=set(),
                    denied_capabilities={"ALL"},
                    reason=f"SECURITY_DENIAL: Forbidden destructive pattern matched '{pattern}'"
                )

        granted: Set[str] = set()
        denied: Set[str] = set()

        # 2. Domain-specific capability allocation
        if intent.target_domain == TaskDomain.OFFICE:
            granted.add("OFFICE_SUITE")
            granted.add("FILE_CREATE")
            granted.add("SANDBOX_WRITE")
            denied.add("RAW_OS_SHELL")
            denied.add("NETWORK_RAW_SOCKET")
        elif intent.target_domain == TaskDomain.CODE:
            granted.add("FILE_READ")
            granted.add("FILE_WRITE")
            granted.add("SANDBOX_EXECUTE")
            denied.add("SYSTEM_CONFIG_OVERWRITE")
        elif intent.target_domain == TaskDomain.RESEARCH:
            granted.add("WEB_SEARCH")
            granted.add("URL_FETCH")
            granted.add("VECTOR_RAG_WRITE")
            denied.add("FILE_DELETE")
        else:
            granted.add("GENERAL_READ")

        return CapabilityGrant(
            grant_id=grant_id,
            intent_id=intent.intent_id,
            allowed=True,
            granted_capabilities=granted,
            denied_capabilities=denied,
            sandbox_path=self.sandbox_root,
            reason="AUTHORIZED_MINIMAL_CAPABILITY"
        )


fast_governor = FastGovernor()
