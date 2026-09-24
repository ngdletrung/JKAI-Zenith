# -*- coding: utf-8 -*-
"""
tests/test_h2_model_identity_honesty.py
H2 — Model Identity Honesty Test Suite

Spec (Opencode Turn 70):
  - System prompt MUST contain the actual model name injected from runtime.
  - System prompt MUST contain actual tool list from runtime.
  - System prompt MUST NOT allow "ràng buộc bảo mật" fabrication when no rule prohibits.
  - Test render prompt contains correct model name from config.
  - Grep prompt template: ban string "ràng buộc bảo mật" as a hardcoded excuse.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain")))

from prompt_engine.master_prompt_architect import MasterPromptArchitect


class TestH2IdentityBlock(unittest.TestCase):
    """Tests for _build_identity_block method (unit)."""

    def setUp(self):
        self.architect = MasterPromptArchitect()

    def test_identity_block_contains_model_name(self):
        """H2: identity block must contain the injected model name."""
        block = self.architect._build_identity_block(
            active_model="qwen2.5:3b",
            available_tools=None,
        )
        self.assertIn("qwen2.5:3b", block, msg=f"Model name not found in identity block: {block}")

    def test_identity_block_contains_tool_list(self):
        """H2: identity block must list provided tools."""
        tools = ["read_file", "write_file", "grep_search"]
        block = self.architect._build_identity_block(
            active_model="gemma3:4b",
            available_tools=tools,
        )
        for tool in tools:
            self.assertIn(tool, block, msg=f"Tool '{tool}' not found in identity block: {block}")

    def test_identity_block_empty_tool_list_says_no_tools(self):
        """H2: explicit empty tool list → should say no tools available."""
        block = self.architect._build_identity_block(
            active_model="qwen2.5-coder:3b",
            available_tools=[],
        )
        self.assertIn("No external tools", block, msg=f"Empty tool list not handled: {block}")

    def test_identity_block_no_model_no_tools_still_has_mandate(self):
        """H2: even with no model/tools, honesty mandate must appear."""
        block = self.architect._build_identity_block(
            active_model="",
            available_tools=None,
        )
        # Identity mandate is always present
        self.assertIn("IDENTITY HONESTY MANDATE", block, msg=f"Honesty mandate missing: {block}")

    def test_identity_block_forbids_ràng_buộc_bảo_mật_claim(self):
        """H2: identity block must explicitly forbid fabricated security constraint claim."""
        block = self.architect._build_identity_block(
            active_model="qwen2.5:3b",
            available_tools=["read_file"],
        )
        self.assertIn(
            "ràng buộc bảo mật",
            block,
            msg="Honesty mandate must explicitly mention and forbid 'ràng buộc bảo mật'"
        )
        # Verify it's in a PROHIBITION context (not a permission)
        mandate_lower = block.lower()
        self.assertIn("do not claim", mandate_lower,
                      msg="Block must say 'Do NOT claim' for security constraint fabrication")

    def test_no_model_injected_returns_empty_or_only_mandate(self):
        """H2: with no runtime info, block still has the mandate (not empty string)."""
        block = self.architect._build_identity_block(active_model="", available_tools=None)
        # Should not be empty (mandate is always there)
        self.assertTrue(len(block) > 0, msg="Identity block should not be empty (mandate must be present)")


class TestH2SystemPromptInjection(unittest.TestCase):
    """Tests that build_master_system_prompt correctly injects identity into rendered prompts."""

    def setUp(self):
        from core.guardrails.rules_loader import invalidate_cache
        invalidate_cache()
        self.architect = MasterPromptArchitect()

    def test_mid_prompt_contains_injected_model_name(self):
        """H2: MID variant system prompt must contain runtime model name."""
        prompt = self.architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            prompt_variant="MID",
            active_model="qwen2.5:3b",
        )
        self.assertIn(
            "qwen2.5:3b", prompt,
            msg=f"Runtime model name not found in MID prompt. Got:\n{prompt[:500]}"
        )

    def test_full_prompt_contains_injected_model_name(self):
        """H2: FULL variant system prompt must contain runtime model name."""
        prompt = self.architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            prompt_variant="FULL",
            active_model="gemma3:12b",
        )
        self.assertIn(
            "gemma3:12b", prompt,
            msg=f"Runtime model name not found in FULL prompt. Got:\n{prompt[:500]}"
        )

    def test_lean_prompt_contains_injected_model_name(self):
        """H2: LEAN variant system prompt must contain runtime model name."""
        prompt = self.architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            prompt_variant="LEAN",
            active_model="qwen2.5-coder:3b",
        )
        self.assertIn(
            "qwen2.5-coder:3b", prompt,
            msg=f"Runtime model name not found in LEAN prompt. Got:\n{prompt[:500]}"
        )

    def test_mid_prompt_contains_tools_when_injected(self):
        """H2: MID variant must include tool list when provided."""
        tools = ["read_file", "grep_search", "write_to_file"]
        prompt = self.architect.build_master_system_prompt(
            role="EXECUTOR",
            task_type="CODING",
            prompt_variant="MID",
            active_model="qwen2.5-coder:3b",
            available_tools=tools,
        )
        for tool in tools:
            self.assertIn(tool, prompt, msg=f"Tool '{tool}' not found in MID prompt")

    def test_prompt_contains_honesty_mandate_always(self):
        """H2: honesty mandate must always appear in all variants."""
        for variant in ["LEAN", "MID", "FULL"]:
            with self.subTest(variant=variant):
                prompt = self.architect.build_master_system_prompt(
                    role="RECEPTIONIST",
                    task_type="CHAT",
                    prompt_variant=variant,
                    active_model="qwen2.5:3b",
                )
                self.assertIn(
                    "IDENTITY HONESTY MANDATE", prompt,
                    msg=f"Honesty mandate missing in {variant} variant"
                )

    def test_no_active_model_does_not_inject_empty_string(self):
        """H2: when active_model is empty, prompt should NOT contain 'Active inference model:' line."""
        prompt = self.architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            prompt_variant="MID",
            active_model="",
        )
        self.assertNotIn(
            "Active inference model:",
            prompt,
            msg="Empty model name should not inject 'Active inference model:' line"
        )

    def test_different_models_produce_different_prompts(self):
        """H2: two different model names must produce different system prompts."""
        prompt_a = self.architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            prompt_variant="MID",
            active_model="qwen2.5:3b",
        )
        prompt_b = self.architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            prompt_variant="MID",
            active_model="gemma3:12b",
        )
        self.assertNotEqual(
            prompt_a, prompt_b,
            msg="Prompts with different active_model should differ"
        )


class TestH2SecurityConstraintBan(unittest.TestCase):
    """
    H2: Verify no hardcoded "ràng buộc bảo mật" excuse exists in prompt templates.
    This is a static analysis test (grep the source files).
    """

    def _get_prompt_engine_dir(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain", "prompt_engine"))
        return base

    def test_no_hardcoded_security_constraint_excuse_in_prompt_files(self):
        """H2: 'ràng buộc bảo mật' must NOT appear as a hardcoded excuse in prompt_engine source."""
        prompt_dir = self._get_prompt_engine_dir()
        violations = []
        if os.path.isdir(prompt_dir):
            for fname in os.listdir(prompt_dir):
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(prompt_dir, fname)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        # Allow it ONLY in _build_identity_block where it's PROHIBITED
                        if "ràng buộc bảo mật" in line:
                            # Must be in a prohibition context (Do NOT / cấm / forbid)
                            line_lower = line.lower()
                            is_prohibition = any(
                                kw in line_lower for kw in
                                ["do not", "không được", "cấm", "forbid", "not claim", "not allowed"]
                            )
                            if not is_prohibition:
                                violations.append(f"{fname}:{lineno}: {line.rstrip()}")

        self.assertEqual(
            violations, [],
            msg=(
                "Hardcoded 'ràng buộc bảo mật' excuse found in prompt source "
                f"(must only appear in prohibition context):\n" + "\n".join(violations)
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
