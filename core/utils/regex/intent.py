"""
Intent detection patterns — re-exports from locale for convenience.
"""

from core.utils.regex.locale.vi_vn import (
    KNOWLEDGE_QUERY,
    ERROR_VI,
    AUDIT_VI,
    FIX_VI,
    SEARCH_NEWS,
    CHAT,
    SOCIAL_GREETING,
    IDENTITY_INQUIRY,
    CAPABILITIES_INQUIRY,
    BUILD,
    OPERATE,
    SINGLE_FILE_FIX,
    SMALL_SCOPE,
)

__all__ = [
    "KNOWLEDGE_QUERY", "ERROR_VI", "AUDIT_VI", "FIX_VI",
    "SEARCH_NEWS", "CHAT", "SOCIAL_GREETING",
    "IDENTITY_INQUIRY", "CAPABILITIES_INQUIRY",
    "BUILD", "OPERATE", "SINGLE_FILE_FIX", "SMALL_SCOPE",
]
