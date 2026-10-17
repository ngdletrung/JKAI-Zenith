# -*- coding: utf-8 -*-
"""
JKAI Canary Guard Subsystem.
Embeds virtual canary tokens without file-system/git modifications,
detects outbound canary leaks, and strips canaries from local outputs.
"""

import re
import uuid
from typing import Dict, Optional


class CanaryGuard:
    """
    Virtual Canary Token Manager.
    Prevents file modification conflicts by storing tokens in an in-memory
    registry mapped to internal repository file paths.
    """

    CANARY_PREFIX = "canary-jkai-"
    CANARY_REGEX = re.compile(r"canary-jkai-[a-f0-9\-]{36}")

    def __init__(self):
        # Maps file_path -> canary_token
        self._registry: Dict[str, str] = {}
        # Maps canary_token -> file_path
        self._reverse_registry: Dict[str, str] = {}

    def get_or_create_canary(self, file_path: str) -> str:
        """Retrieves or creates a deterministic unique canary token for an internal file."""
        normalized_path = file_path.replace("\\", "/").lower()
        if normalized_path not in self._registry:
            token = f"{self.CANARY_PREFIX}{str(uuid.uuid4())}"
            self._registry[normalized_path] = token
            self._reverse_registry[token] = normalized_path
        return self._registry[normalized_path]

    def inject_virtual_canary(self, file_path: str, content: str) -> str:
        """Injects a virtual canary token into a file's content in working memory."""
        token = self.get_or_create_canary(file_path)
        # Append as virtual metadata footer
        return f"{content}\n<!-- [CANARY_GUARD]: {token} -->"

    def scan(self, text: str) -> Optional[str]:
        """
        Scans outbound payload. If any active canary token is detected,
        returns the token string (indicating an exfiltration attempt).
        """
        if not text:
            return None
        matches = self.CANARY_REGEX.findall(text)
        for token in matches:
            if token in self._reverse_registry:
                return token
        return None

    def strip_canaries(self, text: str) -> str:
        """Strips virtual canary tokens and annotations from text for clean local output."""
        if not text:
            return ""
        # Remove complete canary comment lines
        cleaned = re.sub(
            r"\n?<!--\s*\[CANARY_GUARD\]:[^>]+-->", "", text, flags=re.IGNORECASE
        )
        # Remove any stray tokens
        cleaned = self.CANARY_REGEX.sub("", cleaned)
        return cleaned


canary_guard = CanaryGuard()
