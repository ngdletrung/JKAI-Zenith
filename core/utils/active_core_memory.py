# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/active_core_memory.py
# - Role: Active Self-Editing Core Memory Engine (Inspired by Letta / MemGPT)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call for reading — Disk-backed JSON memory blocks in .zenith/core_memory/.
# 2. In-Context Accessibility: Formats memory blocks into active system prompt context.
# 3. Dynamic Self-Editing: Allows LLM to update blocks via update_core_memory tool.
# -----------------------------------------------------------------------------

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("JKAI.ActiveCoreMemory")

CORE_MEMORY_DIR = Path(os.getenv("WORKSPACE_ROOT", "D:\\Docker\\JKAI")) / ".zenith" / "core_memory"


def _ensure_dir():
    try:
        CORE_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.debug(f"[CORE-MEMORY] Cannot create dir: {e}")


def _get_block_path(block_name: str) -> Path:
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", block_name.lower())
    return CORE_MEMORY_DIR / f"{safe_name}.json"


import re


def get_core_memory(block_name: str) -> str:
    """Read contents of a core memory block."""
    _ensure_dir()
    p = _get_block_path(block_name)
    if not p.exists():
        return ""
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("content", "")
    except Exception as e:
        logger.warning(f"[CORE-MEMORY-READ-ERR] {block_name}: {e}")
        return ""


CORE_MEMORY_MAX_CHARS = 1000

def update_core_memory(block_name: str, new_content: str) -> bool:
    """Update contents of a core memory block (capped at CORE_MEMORY_MAX_CHARS to prevent prompt bloat)."""
    if not block_name or not new_content:
        return False
    _ensure_dir()
    p = _get_block_path(block_name)
    try:
        trimmed = new_content.strip()[:CORE_MEMORY_MAX_CHARS]
        payload = {
            "block_name": block_name,
            "content": trimmed,
            "updated_at": os.getenv("CURRENT_TIME", "2026-08-02")
        }
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[CORE-MEMORY-UPDATE] Updated block '{block_name}' ({len(trimmed)} chars)")
        return True
    except Exception as e:
        logger.warning(f"[CORE-MEMORY-UPDATE-ERR] {block_name}: {e}")
        return False


def get_all_blocks_prompt() -> str:
    """Formats all active core memory blocks into system prompt text."""
    _ensure_dir()
    blocks = []
    try:
        for f in CORE_MEMORY_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                b_name = data.get("block_name", f.stem)
                b_content = data.get("content", "")
                if b_content:
                    blocks.append(f"<{b_name}>\n{b_content}\n</{b_name}>")
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[CORE-MEMORY-PROMPT-ERR] {e}")

    if not blocks:
        return ""
    return "<core_memory>\n" + "\n\n".join(blocks) + "\n</core_memory>"
