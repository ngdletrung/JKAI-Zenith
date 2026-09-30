# -*- coding: utf-8 -*-
"""
tests/test_two_party_hardening_100.py
Two-party closed-loop exam (examiner+auditor: Opencode, runtime: JKAI).
Sealed expectations: every expected value below was committed BEFORE the first run.
Covers session hardening: per-model envelope, soft budget, language anti-collision,
backend honesty, hub soak shape, guardrails scope/mutation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Envelope: rule_hardware.md section 2.6 structural invariants
# ---------------------------------------------------------------------------

def _parse_envelope_rows():
    text = (ROOT_DIR / "intelligence" / "rule_hardware.md").read_text(encoding="utf-8")
    section = text.split("2.6. Per-Model Processing Envelope")[1].split("\n---\n")[0]
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| :") or "Model" in line and "Native" in line:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) >= 4 and cols[1].isdigit() and cols[2].isdigit():
            rows.append({"model": cols[0], "native": int(cols[1]), "operational": int(cols[2])})
    return rows


class TestPerModelEnvelope:
    def test_envelope_operational_within_native(self):
        """Operational ctx must never exceed the model's native max ctx."""
        rows = _parse_envelope_rows()
        assert len(rows) >= 5, f"Envelope table too small: {len(rows)}"
        for r in rows:
            assert 0 < r["operational"] <= r["native"], r

    def test_envelope_declares_no_data_cap(self):
        """Local philosophy must be explicit in the SSoT file itself."""
        text = (ROOT_DIR / "intelligence" / "rule_hardware.md").read_text(encoding="utf-8")
        assert "không trần dữ liệu" in text


# ---------------------------------------------------------------------------
# Budget: local-first soft defaults
# ---------------------------------------------------------------------------

class TestSoftBudgetDefaults:
    def test_budget_defaults_soft_first(self):
        from core.governance.token_budget_guard import TokenBudgetConfig
        cfg = TokenBudgetConfig()
        assert cfg.abort_on_exceed is False
        assert cfg.max_invocations == 500
        assert cfg.max_total_tokens == 50000

    def test_budget_engine_kwarg_compatible(self):
        """Engine passes kwargs['max_total_tokens']; config must accept it and stay soft."""
        from core.governance.token_budget_guard import TokenBudgetGuard, TokenBudgetConfig
        guard = TokenBudgetGuard()
        mid = "two_party_engine_kwarg"
        try:
            cfg = TokenBudgetConfig(max_total_tokens=int(75000))
            rec, ledger = guard.record_usage(
                mission_id=mid, prompt_tokens=60000, completion_tokens=20000,
                custom_config=cfg)
            assert ledger.cumulative_total_tokens == 80000
            assert ledger.tripped is False
        finally:
            guard.reset(mid)

    def test_budget_2x_emits_telemetry_without_abort(self):
        from core.governance.token_budget_guard import TokenBudgetGuard, TokenBudgetConfig
        guard = TokenBudgetGuard()
        mid = "two_party_2x_probe"
        try:
            cfg = TokenBudgetConfig(max_total_tokens=1000, max_invocations=500)
            guard.record_usage(mission_id=mid, prompt_tokens=1500, completion_tokens=1000,
                               custom_config=cfg)
            ledger = guard.get_or_create_ledger(mid)
            assert ledger.cumulative_total_tokens == 2500
            assert ledger.tripped is False
        finally:
            guard.reset(mid)


# ---------------------------------------------------------------------------
# Language: structural anti-collision invariants
# ---------------------------------------------------------------------------

class TestLanguageAntiCollision:
    def test_vi_en_marker_sets_disjoint(self):
        """VI markers and EN function words must share zero tokens (root cause of Turn 244)."""
        from core.cognitive_bus.backends import reflex_engine_backend as mod
        overlap = set(mod._VI_UNACCENTED_MARKERS) & set(mod._EN_FUNCTION_WORDS)
        assert not overlap, f"Collision tokens: {overlap}"

    def test_english_ops_battery_never_vietnamese(self):
        """English ops commands may route 'en' or abstain '*', but never 'vi'."""
        from core.cognitive_bus.backends.reflex_engine_backend import detect_language_bcp47
        battery = [
            "restart the service now", "show me the system logs", "open port 443",
            "enable the firewall", "disable user account", "check disk usage",
            "get status of nginx", "set timeout to thirty seconds", "restart it",
            "look at the metrics dashboard",
        ]
        for cmd in battery:
            got = detect_language_bcp47(cmd)
            assert got in ("en", "*"), f"{cmd!r} -> {got!r}"
            assert got != "vi", f"FALSE POSITIVE: {cmd!r} -> 'vi'"


# ---------------------------------------------------------------------------
# Backend honesty + determinism
# ---------------------------------------------------------------------------

class TestBackendHonesty:
    def test_predict_packet_reports_uncalibrated(self):
        from core.cognitive_bus.backends.reflex_engine_backend import ReflexEngineBackend
        from core.cognitive_bus.decision_substrate_adapter import DecisionPrimitive
        b = ReflexEngineBackend()
        b.load()
        pkt = b.predict(state={"q": "x"}, questions=[(DecisionPrimitive.BOOLEAN, "qq", None)])["qq"]
        assert pkt.metadata["calibration_state"] == "uncalibrated"

    def test_tournament_deterministic_across_calls(self):
        from core.cognitive_bus.backends.reflex_engine_backend import ReflexEngineBackend
        b = ReflexEngineBackend()
        b.load()
        cands = [f"skill_{i:02d}" for i in range(15)]
        r1, _ = b.predict_tournament({"q": "x"}, "pick", cands, group_size=12, top_k=3)
        r2, _ = b.predict_tournament({"q": "x"}, "pick", cands, group_size=12, top_k=3)
        assert [c for c, _ in r1] == [c for c, _ in r2]


# ---------------------------------------------------------------------------
# Hub soak shape + coercion
# ---------------------------------------------------------------------------

class TestHubSoakShape:
    def test_soak_telemetry_counters_are_nonnegative_ints(self):
        from core.cognitive_bus.reflex_hub import SovereignReflexHub
        hub = SovereignReflexHub()
        tele = hub.get_soak_telemetry()
        for key in ("total_cache_checks", "antonym_blocks", "cache_safe_passes"):
            assert isinstance(tele[key], int) and tele[key] >= 0, (key, tele.get(key))

    def test_string_candidate_coerced_with_default_score(self):
        from core.cognitive_bus.reflex_hub import SovereignReflexHub
        hub = SovereignReflexHub()
        res = hub.verify_cache_and_rerank("restart the nginx service", ["restart the nginx service"])
        assert isinstance(res, dict)
        assert res["best_candidate"]["score"] == 0.90


# ---------------------------------------------------------------------------
# Guardrails: scope + mutation tiers
# ---------------------------------------------------------------------------

class TestGuardrailTiers:
    def test_scope_validator_blocks_sensitive_paths(self):
        from core.guardrails.scope_validator import ScopeValidator
        assert ScopeValidator.validate_file_path("D:/Docker/JKAI/.env").allowed is False
        assert ScopeValidator.validate_file_path("C:/Windows/System32/cmd.exe").allowed is False
        assert ScopeValidator.validate_file_path(
            "D:/Docker/JKAI/intelligence/rule_hardware.md").allowed is True

    def test_mutation_guard_tier_separation(self):
        from core.guardrails.mutation_guard import MutationGuard, MutationType
        destructive = MutationGuard.evaluate_mutation("run_command", {"command": "rm -rf /"})
        assert destructive.mutation_type == MutationType.DESTRUCTIVE_MUTATION
        reader = MutationGuard.evaluate_mutation("list_dir", {"path": "."})
        assert reader.mutation_type == MutationType.READ_ONLY
        writer = MutationGuard.evaluate_mutation("write_to_file", {"path": "a.txt"})
        assert writer.mutation_type != MutationType.READ_ONLY
