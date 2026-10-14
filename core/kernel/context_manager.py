#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/kernel/context_manager.py
🧠 Token-Aware Context Manager & Sliding Window Pruner for JKAI Zenith.
Ensures System Prompt + .jkairules.json stay strictly pinned at context top,
while pruning and compressing middle execution logs to fit LLM context windows (num_ctx).
Bịt kín lỗ hổng P0.1: Cô lập không gian Session/Mission, chống rò rỉ bộ nhớ mutable.
"""

import hashlib
import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ContextManager")

_VOLATILE_PREFIX_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "ISO_TIMESTAMP",
        re.compile(r"\b20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"),
    ),
    (
        "UNIX_EPOCH_TS",
        re.compile(
            r"\b(?:timestamp|epoch|now_ms|time_ms|created_at)\s*[:=]\s*\d{9,13}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "DYNAMIC_CLOCK_TIME",
        re.compile(
            r"\b(?:current_time|local_time|wall_clock|gio_hien_tai|system\s+clock)\s*[:=]\s*\d{1,2}:\d{2}(?::\d{2})?",
            re.IGNORECASE,
        ),
    ),
    (
        "UUID_OR_TRACE_ID",
        re.compile(
            r"(?:\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
            r"|\b(?:nonce|request_id|trace_id)\s*[:=]\s*[A-Za-z0-9_-]{6,}\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "MUTABLE_TASK_OR_HW_STATE",
        re.compile(
            r"\b(?:task_state|current_step|step_counter|retry_count|loop_iteration|cpu_load_pct|free_vram_mb)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
    ),
    (
        "EPHEMERAL_SANDBOX_OR_TMP_PATH",
        re.compile(
            r"(?:\.zenith[/\\]worktrees[/\\][A-Za-z0-9_-]+|/tmp/jkai_[A-Za-z0-9_-]+)",
            re.IGNORECASE,
        ),
    ),
]


def inspect_system_prefix_cache_alignment(
    system_prompt: str,
    prefix_window_chars: int = 600,
) -> Dict[str, Any]:
    """
    [Slice 3.1 - Giai đoạn 1.2: CacheAligner-flag (học Headroom)]:
    Kiểm tra tiền tố system trước mỗi call để phát hiện nội dung volatile
    (timestamp, epoch, UUID/trace_id, task_state, đường dẫn sandbox tạm)
    lọt lên đầu prompt làm vỡ KV-cache của Ollama/vLLM.
    """
    head = str(system_prompt or "")[: max(64, int(prefix_window_chars))]
    reasons: List[str] = []
    matches: List[str] = []

    for label, pattern in _VOLATILE_PREFIX_PATTERNS:
        m = pattern.search(head)
        if m:
            reasons.append(label)
            matches.append(m.group(0))

    volatile_flag = len(reasons) > 0
    return {
        "cache_aligned": not volatile_flag,
        "volatile_flag": volatile_flag,
        "reasons": reasons,
        "offending_matches": matches,
        "recommendation": (
            "Move volatile timestamps/state/trace IDs to the trailing user/tool suffix so index-0 system prefix stays KV-cache aligned."
            if volatile_flag
            else "System prefix is static and KV-cache aligned."
        ),
    }


class ContextManager:
    """
    Context Window Governor for Local LLMs (Ollama / Qwen / Llama).
    Prevents token budget overflow and context drift.
    Includes Ephemeral Session Scope management (P0.1) and KV Prefix Stability Telemetry (Slice 2.3).
    """
    def __init__(self, max_token_budget: int = 8192, reserved_output_tokens: int = 1524):
        self.max_token_budget = int(os.getenv("JKAI_MAX_CONTEXT_TOKENS", max_token_budget))
        self.reserved_output_tokens = reserved_output_tokens
        self.effective_input_budget = self.max_token_budget - self.reserved_output_tokens
        self._session_scopes: Dict[str, Dict[str, Any]] = {}

    def get_session_scope(self, session_id: str) -> Dict[str, Any]:
        """Truy xuất không gian dữ liệu cô lập của session/mission."""
        if session_id not in self._session_scopes:
            self._session_scopes[session_id] = {
                "created_at": os.times().elapsed if hasattr(os, "times") else 0.0,
                "token_usage": 0,
                "metadata": {},
                "kv_prefix": {
                    "prefix_sha256": "",
                    "pinned_prefix_tokens": 0,
                    "dynamic_suffix_tokens": 0,
                    "total_turns": 0,
                    "prefix_hits": 0,
                    "warm_turn_hit_rate": 0.0,
                    "overall_hit_rate": 0.0,
                    "cache_aligner_clean": True,
                    "volatile_flags": [],
                },
            }
        return self._session_scopes[session_id]

    def clear_session_scope(self, session_id: str) -> None:
        """P0.1 Ephemeral Scope: Tiêu hủy không gian ngữ cảnh khi session kết thúc."""
        if session_id in self._session_scopes:
            del self._session_scopes[session_id]
            logger.info("🧹 [CONTEXT-MANAGER] Cleared session scope '%s'", session_id)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator (approx 3.5 chars per token for EN/VI + code)."""
        if not text:
            return 0
        return max(1, len(text) // 3)

    @staticmethod
    def _compute_prefix_sha256(system_msgs: List[Dict[str, str]], rules_json: Optional[str] = None) -> str:
        canonical_payload = {
            "system_messages": [
                {"role": str(m.get("role", "system")), "content": str(m.get("content", ""))}
                for m in system_msgs
            ],
            "rules_json": str(rules_json or ""),
        }
        serialized = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def record_kv_prefix_telemetry(
        self,
        session_id: str,
        system_msgs: List[Dict[str, str]],
        rules_json: Optional[str],
        pinned_prefix_tokens: int,
        dynamic_suffix_tokens: int,
    ) -> Dict[str, Any]:
        scope = self.get_session_scope(session_id)
        kv = scope.setdefault(
            "kv_prefix",
            {
                "prefix_sha256": "",
                "pinned_prefix_tokens": 0,
                "dynamic_suffix_tokens": 0,
                "total_turns": 0,
                "prefix_hits": 0,
                "warm_turn_hit_rate": 0.0,
                "overall_hit_rate": 0.0,
                "cache_aligner_clean": True,
                "volatile_flags": [],
            },
        )
        combined_sys = "\n".join(str(m.get("content", "")) for m in system_msgs)
        align_check = inspect_system_prefix_cache_alignment(combined_sys)

        new_sha = self._compute_prefix_sha256(system_msgs, rules_json=rules_json)
        prev_sha = kv.get("prefix_sha256", "")
        total_turns = int(kv.get("total_turns", 0)) + 1
        prefix_hits = int(kv.get("prefix_hits", 0))
        is_hit = bool(prev_sha and prev_sha == new_sha)
        if is_hit:
            prefix_hits += 1

        warm_turns = max(0, total_turns - 1)
        warm_hit_rate = round(prefix_hits / warm_turns, 4) if warm_turns > 0 else 1.0
        overall_hit_rate = round(prefix_hits / total_turns, 4)

        kv.update(
            {
                "prefix_sha256": new_sha,
                "pinned_prefix_tokens": int(pinned_prefix_tokens),
                "dynamic_suffix_tokens": int(dynamic_suffix_tokens),
                "total_turns": total_turns,
                "prefix_hits": prefix_hits,
                "last_turn_prefix_hit": is_hit,
                "warm_turn_hit_rate": warm_hit_rate,
                "overall_hit_rate": overall_hit_rate,
                "cache_aligner_clean": bool(align_check["cache_aligned"]),
                "volatile_flags": list(align_check["reasons"]),
            }
        )
        return dict(kv)

    def get_kv_prefix_telemetry(self, session_id: str) -> Dict[str, Any]:
        scope = self.get_session_scope(session_id)
        return dict(scope.get("kv_prefix", {}))

    def prune_messages(
        self,
        messages: List[Dict[str, str]],
        rules_json: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Prunes conversation messages while strictly preserving:
        1. System Prompt (Index 0)
        2. Injected Rules & Guardrails
        3. Most recent user & assistant interactions
        Middle turns are truncated or compressed.
        """
        if not messages:
            return []

        # Calculate budget allocated for system prompt & rules
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        system_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in system_msgs)
        rules_tokens = self.estimate_tokens(rules_json) if rules_json else 0
        
        pinned_tokens = system_tokens + rules_tokens
        available_history_budget = self.effective_input_budget - pinned_tokens

        if available_history_budget <= 500:
            logger.warning("⚠️ [CONTEXT-PRUNER] Token budget tight (%s tokens left for history). Aggressive pruning activated.", available_history_budget)
            # Keep only the last user turn if budget is extremely tight
            other_msgs = other_msgs[-2:] if len(other_msgs) >= 2 else other_msgs

        current_tokens = 0
        pruned_history: List[Dict[str, str]] = []

        # Iterate backwards from newest messages to fit within budget
        for msg in reversed(other_msgs):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            if current_tokens + msg_tokens <= available_history_budget:
                pruned_history.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Store full execution output in StreamBufferStore before compressing message
                if msg.get("role") in ["tool", "system"] or "Traceback" in msg.get("content", ""):
                    content = msg.get("content", "")
                    stream_marker = ""
                    try:
                        from core.utils.stream_buffer_store import store_stream
                        s_env = store_stream(
                            content=content,
                            source_tool="context_pruner",
                            task_id=str(session_id or "sys"),
                            preview_chars=300,
                        )
                        stream_marker = (
                            f" | stream_id={s_env['stream_id']} | total_lines={s_env['total_lines']} "
                            f"(use read_stream_window or search_in_stream to recover middle lines)"
                        )
                    except Exception:
                        stream_marker = ""
                    truncated_content = (
                        content[:300]
                        + f"\n...[OUTPUT TRUNCATED BY JKAI CONTEXT MANAGER{stream_marker}]...\n"
                        + content[-300:]
                    )
                    truncated_tokens = self.estimate_tokens(truncated_content)
                    if current_tokens + truncated_tokens <= available_history_budget:
                        pruned_history.insert(0, {"role": msg["role"], "content": truncated_content})
                        current_tokens += truncated_tokens

        total_est = pinned_tokens + current_tokens
        if session_id:
            scope = self.get_session_scope(session_id)
            scope["token_usage"] = total_est
            self.record_kv_prefix_telemetry(
                session_id=session_id,
                system_msgs=system_msgs,
                rules_json=rules_json,
                pinned_prefix_tokens=pinned_tokens,
                dynamic_suffix_tokens=current_tokens,
            )

        logger.info(
            "✂️ [CONTEXT-PRUNER] Context pruned: %s -> %s messages | Est. Tokens: %s/%s",
            len(messages), len(system_msgs) + len(pruned_history), total_est, self.max_token_budget
        )
        return system_msgs + pruned_history


context_manager = ContextManager()

