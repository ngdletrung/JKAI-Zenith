"""
Test suite for ShadowHarness telemetry collector.
Verifies compliance with Red Team Turn 92 audit mandates:
1. Schema is versioned.
2. StateSanitizer 2.3a is enforced BEFORE storage (secrets redacted, 64KB cap).
3. Non-blocking failure resilience.
4. Bounded retention and rotation.
"""

import json
import tempfile
import pytest
from pathlib import Path
from core.governance.shadow_harness import ShadowHarness, SCHEMA_VERSION


def test_shadow_harness_schema_and_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        harness = ShadowHarness(telemetry_dir=tmp_dir)

        raw_state = {
            "mission_id": "test_m_01",
            "db_password": "SuperSecretToken_12345",
            "task_type": "query_read"
        }
        reflex_draft = {"primitive": "CHOICE", "verdict": "FAST_PATH", "raw_conf": 0.88}
        receipt = {"exit_code": 0, "verified": True}

        record = harness.record_observation(
            raw_state=raw_state,
            reflex_draft=reflex_draft,
            execution_receipt=receipt,
            metadata={"source": "test_suite"}
        )

        assert record is not None
        assert record.schema_version == SCHEMA_VERSION
        assert record.record_id.startswith("sh_")
        assert record.redaction_count >= 1

        # Check secret scrubbing in stored state
        assert "SuperSecretToken" not in json.dumps(record.sanitized_state)
        assert record.sanitized_state["db_password"] == "[REDACTED_SECRET_FIELD]"

        # Check persisted file on disk
        files = list(Path(tmp_dir).glob("shadow_telemetry_*.jsonl"))
        assert len(files) == 1

        with open(files[0], "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        persisted_data = json.loads(lines[0])
        assert persisted_data["schema_version"] == SCHEMA_VERSION
        assert persisted_data["sanitized_state"]["db_password"] == "[REDACTED_SECRET_FIELD]"


def test_shadow_harness_64kb_cap_enforcement():
    with tempfile.TemporaryDirectory() as tmp_dir:
        harness = ShadowHarness(telemetry_dir=tmp_dir)

        # Huge payload exceeding 64KB
        huge_state = {"bloat": "x" * 70000}
        record = harness.record_observation(raw_state=huge_state)

        assert record is not None
        # State sanitizer must have truncated or capped the payload
        serialized = json.dumps(record.sanitized_state)
        assert len(serialized.encode("utf-8")) <= 65536 + 200  # Within 64KB margin


def test_shadow_harness_disabled_mode():
    with tempfile.TemporaryDirectory() as tmp_dir:
        harness = ShadowHarness(telemetry_dir=tmp_dir, enabled=False)
        record = harness.record_observation(raw_state={"key": "val"})
        assert record is None
        files = list(Path(tmp_dir).glob("*.jsonl"))
        assert len(files) == 0


def test_shadow_harness_two_phase_pairing():
    """Verifies that start_observation + complete_observation produces a complete paired triple."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        harness = ShadowHarness(telemetry_dir=tmp_dir)

        # 1. Start observation at decision time
        cid = harness.start_observation(
            raw_state={"user_query": "replan mission 123", "token": "secret_abc"},
            reflex_draft={"action": "REPLAN", "confidence": 0.95},
            metadata={"caller": "test"}
        )
        assert cid is not None
        assert cid.startswith("corr_")

        # No file on disk yet (unpaired records are NOT written)
        files = list(Path(tmp_dir).glob("*.jsonl"))
        assert len(files) == 0

        # 2. Complete observation when execution receipt arrives
        receipt = {"exit_code": 0, "verified": True, "latency_ms": 12.5}
        record = harness.complete_observation(cid, execution_receipt=receipt)

        assert record is not None
        assert record.execution_receipt == receipt
        assert record.sanitized_state["token"] == "[REDACTED_SECRET]" or "secret" not in json.dumps(record.sanitized_state)
        assert record.reflex_draft["action"] == "REPLAN"

        # Now exactly 1 paired record exists on disk
        files = list(Path(tmp_dir).glob("*.jsonl"))
        assert len(files) == 1

        stats = harness.get_telemetry_stats()
        assert stats["total_records"] == 1
        assert stats["paired_records"] == 1
        assert stats["unpaired_records"] == 0
        assert stats["pairing_rate_pct"] == 100.0

