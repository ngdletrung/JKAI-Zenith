"""
Integration test suite for ShadowHarness hooks across production execution paths:
1. TriTierDecisionAdapter
2. LayeredVerificationGraph
3. MissionRuntime
"""

import json
import tempfile
import asyncio
from pathlib import Path
import pytest

from core.governance.shadow_harness import ShadowHarness, SCHEMA_VERSION
from core.cognitive_bus.decision_substrate_adapter import (
    TriTierDecisionAdapter,
    DecisionPrimitive
)
from core.verification.layered_verification_graph import LayeredVerificationGraph
from core.kernel.models import (
    MissionContext,
    MissionPlan,
    MissionNode
)
from core.kernel.mission_runtime import MissionRuntime


def test_tri_tier_adapter_shadow_recording():
    with tempfile.TemporaryDirectory() as tmp_dir:
        harness = ShadowHarness(telemetry_dir=tmp_dir)
        adapter = TriTierDecisionAdapter(enable_mock=True, shadow_harness=harness)

        state = {
            "query": "SELECT * FROM users WHERE active = 1",
            "api_key": "sk-secret-key-to-redact-9999",
            "context": "database_optimization"
        }
        batch = [
            (DecisionPrimitive.BOOLEAN, "is_read_only", None),
            (DecisionPrimitive.CHOICE, "risk_level", ["LOW", "MEDIUM", "HIGH"])
        ]

        verdict = adapter.evaluate_parallel_batch(state, batch)
        assert verdict is not None

        # Verify shadow telemetry record on disk
        files = list(Path(tmp_dir).glob("shadow_telemetry_*.jsonl"))
        assert len(files) == 1

        with open(files[0], "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f.readlines()]

        assert len(lines) == 1
        record = lines[0]
        assert record["schema_version"] == SCHEMA_VERSION
        assert record["sanitized_state"]["api_key"] == "[REDACTED_SECRET_FIELD]"
        assert "sk-secret-key" not in json.dumps(record)
        assert "is_read_only" in record["reflex_draft"]
        assert record["metadata"]["source"] == "TriTierDecisionAdapter"


def test_layered_verification_graph_shadow_recording():
    with tempfile.TemporaryDirectory() as tmp_dir:
        harness = ShadowHarness(telemetry_dir=tmp_dir)
        adapter = TriTierDecisionAdapter(enable_mock=True)
        graph = LayeredVerificationGraph(adapter=adapter, shadow_harness=harness)

        observation = {
            "artifact_path": "/tmp/output.json",
            "auth_token": "Bearer my_secret_token_abc123",
            "schema_version": "v1.2"
        }

        res = graph.verify_observation(observation)
        assert res is not None

        files = list(Path(tmp_dir).glob("shadow_telemetry_*.jsonl"))
        assert len(files) == 1

        with open(files[0], "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f.readlines()]

        assert len(lines) == 1
        record = lines[0]
        assert record["schema_version"] == SCHEMA_VERSION
        assert record["execution_receipt"]["overall_passed"] == res.overall_passed
        assert record["metadata"]["source"] == "LayeredVerificationGraph"
        assert "my_secret_token_abc123" not in json.dumps(record)


@pytest.mark.asyncio
async def test_mission_runtime_shadow_recording():
    with tempfile.TemporaryDirectory() as tmp_dir:
        telemetry_dir = Path(tmp_dir) / "telemetry"
        missions_dir = Path(tmp_dir) / "missions"
        
        harness = ShadowHarness(telemetry_dir=str(telemetry_dir))
        runtime = MissionRuntime(base_dir=str(missions_dir), shadow_harness=harness)

        ctx = MissionContext(
            goal="Verify shadow emission during node execution",
            constraints=["local_only"]
        )
        mission_id = runtime.submit_mission(ctx)

        node = MissionNode(
            id="node-1",
            name="read_code_test",
            capability="read_code",
            params={"path": "main.py"}
        )
        plan = MissionPlan(nodes={"node-1": node}, edges=[])


        async def dummy_executor(n, c):
            return {"echo": "hello shadow", "status": "ok"}

        success = await runtime.execute_mission(mission_id, plan, dummy_executor)
        assert success is True

        files = list(telemetry_dir.glob("shadow_telemetry_*.jsonl"))
        assert len(files) == 1

        with open(files[0], "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f.readlines()]

        assert len(lines) == 1
        record = lines[0]
        assert record["schema_version"] == SCHEMA_VERSION
        assert record["reflex_draft"]["node_id"] == "node-1"
        assert record["execution_receipt"]["status"] == "COMPLETED"
        assert record["metadata"]["mission_id"] == mission_id

