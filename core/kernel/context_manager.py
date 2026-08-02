#!/usr/bin/env python3
"""
🧠 Token-Aware Context Manager & Sliding Window Pruner for JKAI Zenith.
Ensures System Prompt + .jkairules.json stay strictly pinned at context top,
while pruning and compressing middle execution logs to fit LLM context windows (num_ctx).
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ContextManager")


class ContextManager:
    """
    Context Window Governor for Local LLMs (Ollama / Qwen / Llama).
    Prevents token budget overflow and context drift.
    """
    def __init__(self, max_token_budget: int = 8192, reserved_output_tokens: int = 1524):
        self.max_token_budget = int(os.getenv("JKAI_MAX_CONTEXT_TOKENS", max_token_budget))
        self.reserved_output_tokens = reserved_output_tokens
        self.effective_input_budget = self.max_token_budget - self.reserved_output_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator (approx 3.5 chars per token for EN/VI + code)."""
        if not text:
            return 0
        return max(1, len(text) // 3)

    def prune_messages(self, messages: List[Dict[str, str]], rules_json: Optional[str] = None) -> List[Dict[str, str]]:
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
            logger.warning(f"⚠️ [CONTEXT-PRUNER] Token budget tight ({available_history_budget} tokens left for history). Aggressive pruning activated.")
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
                # Truncate very long execution outputs if they are tool responses
                if msg.get("role") in ["tool", "system"] or "Traceback" in msg.get("content", ""):
                    content = msg.get("content", "")
                    truncated_content = content[:300] + "\n...[OUTPUT TRUNCATED BY JKAI CONTEXT MANAGER]...\n" + content[-300:]
                    truncated_tokens = self.estimate_tokens(truncated_content)
                    if current_tokens + truncated_tokens <= available_history_budget:
                        pruned_history.insert(0, {"role": msg["role"], "content": truncated_content})
                        current_tokens += truncated_tokens

        logger.info(f"✂️ [CONTEXT-PRUNER] Context pruned: {len(messages)} -> {len(system_msgs) + len(pruned_history)} messages | Est. Tokens: {pinned_tokens + current_tokens}/{self.max_token_budget}")
        return system_msgs + pruned_history


context_manager = ContextManager()
