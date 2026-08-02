# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/state_checkpoint.py
# - Role: Lazy State Checkpointing & Resume System (SOTA 2026)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call — Disk-backed JSON persistence in workspace root.
# 2. Crash Recovery: Allows pipeline stages to resume from last checkpoint.
# 3. Memory Eviction: Automatically cleans up checkpoints upon mission completion.
# -----------------------------------------------------------------------------

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("JKAI.StateCheckpoint")

CHECKPOINT_DIR = Path(os.getenv("WORKSPACE_ROOT", "D:\\Docker\\JKAI")) / ".zenith" / "checkpoints"


def _ensure_dir():
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.debug(f"[CHECKPOINT] Cannot create dir: {e}")


def save_checkpoint(task_id: str, stage_name: str, state: Dict[str, Any]) -> bool:
    """Save serializable pipeline state to disk checkpoint."""
    if not task_id or task_id == "sys":
        return False

    _ensure_dir()
    ckpt_file = CHECKPOINT_DIR / f"{task_id}_{stage_name}.json"

    # Filter non-serializable objects (instances, locks, module refs)
    serializable_state = {}
    for k, v in state.items():
        if isinstance(v, (str, int, float, bool, list, dict, type(None))):
            serializable_state[k] = v

    try:
        ckpt_file.write_text(json.dumps(serializable_state, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug(f"[CHECKPOINT-SAVE] Task {task_id} @ {stage_name}")
        return True
    except Exception as e:
        logger.warning(f"[CHECKPOINT-SAVE-ERR] {stage_name}: {e}")
        return False


def load_checkpoint(task_id: str, stage_name: str) -> Optional[Dict[str, Any]]:
    """Load serializable pipeline state from disk checkpoint if present."""
    if not task_id or task_id == "sys":
        return None

    ckpt_file = CHECKPOINT_DIR / f"{task_id}_{stage_name}.json"
    if not ckpt_file.exists():
        return None

    try:
        data = json.loads(ckpt_file.read_text(encoding="utf-8"))
        logger.info(f"[CHECKPOINT-LOAD] Resumed task {task_id} from stage {stage_name}")
        return data
    except Exception as e:
        logger.warning(f"[CHECKPOINT-LOAD-ERR] {stage_name}: {e}")
        return None


def clear_checkpoints(task_id: str):
    """Remove all checkpoints for a completed task_id."""
    if not task_id or task_id == "sys":
        return

    _ensure_dir()
    try:
        for f in CHECKPOINT_DIR.glob(f"{task_id}_*.json"):
            try:
                f.unlink()
            except Exception:
                pass
        logger.debug(f"[CHECKPOINT-CLEAN] Cleared checkpoints for {task_id}")
    except Exception as e:
        logger.warning(f"[CHECKPOINT-CLEAN-ERR] {e}")
