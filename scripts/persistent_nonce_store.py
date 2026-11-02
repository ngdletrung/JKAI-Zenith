# -*- coding: utf-8 -*-
"""
scripts/persistent_nonce_store.py
Compatibility re-export. The single implementation now lives in
services/ai_desktop/nonce_store.py so the dispatcher and the IPC worker share
one anti-replay ledger instead of two divergent copies.
"""

from services.ai_desktop.nonce_store import DEFAULT_DB_PATH, PersistentNonceStore

__all__ = ["DEFAULT_DB_PATH", "PersistentNonceStore"]
