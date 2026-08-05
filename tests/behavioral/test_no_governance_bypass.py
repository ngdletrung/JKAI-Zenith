"""
JKAI ZENITH AI OS — TIER 2 BEHAVIORAL GOVERNANCE TEST SUITE
File: tests/behavioral/test_no_governance_bypass.py

Proves that no execution path can bypass Governance Policy Gates, Scope Boundaries, or Evidence Normalization.
"""

import pytest
from core.guardrails.mutation_guard import MutationGuard, MutationType
from core.guardrails.scope_validator import ScopeValidator
from core.guardrails.observation_normalizer import ObservationNormalizer


def test_no_governance_bypass_destructive_commands():
    """Verify destructive commands cannot bypass policy gate."""
    bypass_attempts = [
        ("run_command", {"command": "rm -rf /"}),
        ("run_command", {"command": "DROP DATABASE production"}),
        ("run_command", {"command": "systemctl stop firewall"}),
        ("run_command", {"command": "flush iptables production"}),
    ]
    for tool_name, params in bypass_attempts:
        res = MutationGuard.evaluate_mutation(tool_name, params)
        assert res.allowed is False, f"Bypass vulnerability detected for command: {params}"
        assert res.requires_policy_gate is True
        assert res.mutation_type == MutationType.DESTRUCTIVE_MUTATION


def test_no_governance_bypass_path_traversal():
    """Verify path traversal outside workspace is strictly blocked."""
    forbidden_targets = [
        "D:/Docker/JKAI/.env",
        "C:/Windows/System32/cmd.exe",
        "D:/Docker/JKAI/../../secret.txt"
    ]
    for target in forbidden_targets:
        res = ScopeValidator.validate_file_path(target)
        assert res.allowed is False, f"Path traversal bypass detected for: {target}"


def test_observation_normalization_integrity():
    """Verify tool observations contain evidence hashes."""
    obs = ObservationNormalizer.normalize(
        tool_id="replace_file_content",
        invocation_id="inv_999",
        raw_result={"stdout": "Replaced line 10", "stderr": ""},
        status="SUCCESS",
        changed_state={"file": "main.py", "lines_changed": 1}
    )
    assert obs.evidence_hash != ""
    assert obs.changed_state["file"] == "main.py"
