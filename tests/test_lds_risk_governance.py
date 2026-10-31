# -*- coding: utf-8 -*-
"""
tests/test_lds_risk_governance.py
Enterprise Sovereign Runtime Governance Test Suite:
1. Cognithor 4-Tier Risk Classification
2. DIR Legal Decision State (LDS) 5 Pillars
3. SROS v2 Cryptographic Receipts & Ouroboros Replay Audit
4. Execution Integrity & Receipt Enforcement in Execution Path
5. Secret Management (Fail-Closed in Production & Environment Injection)
6. AGH Cross-Process File-Backed Concurrency Resource Leases
7. Meru OS Glass-Box Integer States
"""

import os
import sys
import time
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

from core.kernel.lds_risk_governance import (
    EnterpriseRuntimeGovernance,
    RiskTier,
    AgentStateCode,
    LDSVerdict,
    ExecutionReceipt,
    ResourceLeaseManager,
    _resolve_governance_secret,
)
from core.kernel.execution_integrity import (
    ExecutionIntegrityLayer,
    ExecutionDecision,
    ExecutionResult,
    DecisionOutcome,
)
from prompt_engine.task_contract import TaskContract, DecisionAuthority


class TestCognithorRiskTiering:
    """Kiểm tra phân loại rủi ro 4 cấp độ toán học."""

    def setup_method(self):
        self.gov = EnterpriseRuntimeGovernance()

    def test_green_observation_tools(self):
        for tool in ["view_file", "read_file", "list_dir", "grep_search", "search_web", "get_metrics"]:
            tier = self.gov.classify_risk(tool)
            assert tier == RiskTier.GREEN
            assert tier.label == "GREEN_LOW_RISK"

    def test_yellow_safe_mutation(self):
        tier = self.gov.classify_risk("write_to_file", {"TargetFile": "new_report.txt"})
        assert tier == RiskTier.YELLOW
        assert tier.label == "YELLOW_MEDIUM_RISK"

    def test_orange_high_mutation(self):
        for tool in ["replace_file_content", "python_execute", "run_command", "install_package"]:
            tier = self.gov.classify_risk(tool, {"CommandLine": "dir"})
            assert tier == RiskTier.ORANGE
            assert tier.label == "ORANGE_HIGH_RISK"

    def test_red_critical_destructive(self):
        for tool in ["delete_file", "drop_table", "drop_database", "format_drive"]:
            tier = self.gov.classify_risk(tool)
            assert tier == RiskTier.RED
            assert tier.label == "RED_CRITICAL_RISK"

    def test_red_unsafe_command_injection(self):
        dangerous_cmds = [
            "rm -rf /",
            "rm -rf *",
            "mkfs.ext4 /dev/sda",
            "chmod -R 777 /",
            "iptables -F",
            "shutdown -h now"
        ]
        for cmd in dangerous_cmds:
            tier = self.gov.classify_risk("run_command", {"CommandLine": cmd})
            assert tier == RiskTier.RED


class TestLegalDecisionStatePillars:
    """Kiểm định 5 trụ cột Legal Decision State (DIR)."""

    def setup_method(self):
        self.gov = EnterpriseRuntimeGovernance()

    def test_authority_pillar_blocks_unauthorized_deletion(self):
        contract = TaskContract(
            objective="Audit code",
            decision_authority=DecisionAuthority(can_delete_files=False, can_modify_files=True)
        )
        verdict = self.gov.evaluate_lds("delete_file", {"TargetFile": "a.txt"}, task_contract=contract, task_id="t1")
        assert not verdict.is_legal
        assert not verdict.authority_ok
        assert any("AUTHORITY_VIOLATION" in r for r in verdict.failure_reasons)

    def test_authority_pillar_blocks_unauthorized_modification(self):
        contract = TaskContract(
            objective="Read-only Audit",
            decision_authority=DecisionAuthority(can_delete_files=False, can_modify_files=False)
        )
        verdict = self.gov.evaluate_lds("replace_file_content", {"TargetFile": "a.txt"}, task_contract=contract, task_id="t1")
        assert not verdict.is_legal
        assert not verdict.authority_ok
        assert any("AUTHORITY_VIOLATION" in r for r in verdict.failure_reasons)

    def test_context_pillar_blocks_path_traversal(self):
        malicious_paths = [
            "../../etc/passwd",
            "..\\..\\Windows\\System32",
            "/etc/shadow",
            "C:\\Windows\\system.ini"
        ]
        for path in malicious_paths:
            verdict = self.gov.evaluate_lds("view_file", {"Path": path}, task_id="t1")
            assert not verdict.is_legal
            assert not verdict.context_ok
            assert any("CONTEXT_VIOLATION" in r for r in verdict.failure_reasons)

    def test_integrity_pillar_blocks_destructive_shell_syntax(self):
        verdict = self.gov.evaluate_lds("run_command", {"CommandLine": "rm -rf /var/log"}, task_id="t1")
        assert not verdict.is_legal
        assert not verdict.integrity_ok
        assert any("INTEGRITY_VIOLATION" in r for r in verdict.failure_reasons)

    def test_evidence_pillar_blocks_empty_task_grounding(self):
        verdict = self.gov.evaluate_lds("view_file", {"Path": "safe.py"}, task_id="")
        assert not verdict.is_legal
        assert not verdict.evidence_ok

    def test_lds_passes_all_5_pillars_for_legitimate_action(self):
        contract = TaskContract(
            objective="Analysis",
            decision_authority=DecisionAuthority(can_delete_files=False, can_modify_files=True)
        )
        verdict = self.gov.evaluate_lds("view_file", {"Path": "src/main.py"}, task_contract=contract, task_id="task_valid_01")
        assert verdict.is_legal
        assert verdict.authority_ok
        assert verdict.context_ok
        assert verdict.time_ok
        assert verdict.integrity_ok
        assert verdict.evidence_ok
        assert len(verdict.failure_reasons) == 0


class TestSROSCryptographicReceipts:
    """Kiểm tra biên nhận mật mã học (SROS v2) & kiểm toán phát lại (Ouroboros)."""

    def setup_method(self):
        self.gov = EnterpriseRuntimeGovernance()

    def test_receipt_sealing_and_verification(self):
        verdict = LDSVerdict(
            is_legal=True,
            authority_ok=True, context_ok=True, time_ok=True, integrity_ok=True, evidence_ok=True,
            risk_tier=RiskTier.GREEN
        )
        receipt = self.gov.seal_receipt(
            task_id="task_001",
            action="view_file",
            arguments={"Path": "safe.txt"},
            output_result="Hello World",
            lds_verdict=verdict
        )
        assert receipt.receipt_id.startswith("rcpt_")
        assert receipt.lds_legal is True
        assert receipt.verify_signature(self.gov.secret_key) is True
        assert self.gov.verify_receipt(receipt) is True

    def test_tampered_receipt_fails_verification(self):
        verdict = LDSVerdict(
            is_legal=True, authority_ok=True, context_ok=True, time_ok=True, integrity_ok=True, evidence_ok=True,
            risk_tier=RiskTier.GREEN
        )
        receipt = self.gov.seal_receipt("task_001", "view_file", {"Path": "safe.txt"}, "result", verdict)
        # Tamper output_hash
        receipt.output_hash = "tampered_hash_0000"
        assert receipt.verify_signature(self.gov.secret_key) is False
        assert self.gov.verify_receipt(receipt) is False

    def test_replay_audit_detects_tampering(self):
        verdict = LDSVerdict(
            is_legal=True, authority_ok=True, context_ok=True, time_ok=True, integrity_ok=True, evidence_ok=True,
            risk_tier=RiskTier.GREEN
        )
        r1 = self.gov.seal_receipt("task_001", "view_file", {"Path": "a.txt"}, "ok", verdict)
        r2 = self.gov.seal_receipt("task_001", "view_file", {"Path": "b.txt"}, "ok", verdict)
        
        # Valid chain
        valid, errs = self.gov.replay_audit([r1, r2])
        assert valid is True
        assert len(errs) == 0

        # Tampered chain
        r2.action = "delete_database" # Tampered
        valid, errs = self.gov.replay_audit([r1, r2])
        assert valid is False
        assert len(errs) > 0

    def test_key_rotation_replay_audit(self):
        k1 = b"key_v1_sovereign_secret_12345678"
        k2 = b"key_v2_sovereign_secret_87654321"
        key_ring = {"k_v1": k1, "k_v2": k2}
        gov1 = EnterpriseRuntimeGovernance(secret_key=k1, key_id="k_v1", key_ring=key_ring)
        gov2 = EnterpriseRuntimeGovernance(secret_key=k2, key_id="k_v2", key_ring=key_ring)

        verdict = LDSVerdict(
            is_legal=True, authority_ok=True, context_ok=True, time_ok=True, integrity_ok=True, evidence_ok=True,
            risk_tier=RiskTier.GREEN
        )
        r1 = gov1.seal_receipt("t1", "view_file", {"Path": "a.txt"}, "ok", verdict)
        r2 = gov2.seal_receipt("t1", "view_file", {"Path": "b.txt"}, "ok", verdict)

        # Audit with key_ring rotates keys by key_id
        valid, errs = gov2.replay_audit([r1, r2])
        assert valid is True
        assert len(errs) == 0

    def test_replay_audit_task_scope_and_monotonic_ordering(self):
        verdict = LDSVerdict(
            is_legal=True, authority_ok=True, context_ok=True, time_ok=True, integrity_ok=True, evidence_ok=True,
            risk_tier=RiskTier.GREEN
        )
        r1 = self.gov.seal_receipt("task_001", "view_file", {"Path": "a.txt"}, "ok", verdict)
        r2 = self.gov.seal_receipt("task_001", "view_file", {"Path": "b.txt"}, "ok", verdict)

        # Matching task scope
        valid, errs = self.gov.replay_audit([r1, r2], expected_task_id="task_001")
        assert valid is True
        assert len(errs) == 0

        # Mismatched task scope
        valid, errs = self.gov.replay_audit([r1, r2], expected_task_id="task_other")
        assert valid is False
        assert any("expected 'task_other'" in e for e in errs)

        # Non-monotonic sequence
        r_inverted = [r2, r1]
        valid, errs = self.gov.replay_audit(r_inverted)
        assert valid is False
        assert any("Non-monotonic sequence ordering" in e for e in errs)

        # Timestamp freshness check (max_age_seconds)
        r_stale = self.gov.seal_receipt("task_001", "view_file", {"Path": "c.py"}, "content C", verdict)
        r_stale.timestamp_utc = "2020-01-01T00:00:00Z"
        r_stale.hmac_signature = r_stale.compute_signature(self.gov.secret_key)
        valid, errs = self.gov.replay_audit([r_stale], max_age_seconds=3600.0)
        assert valid is False
        assert any("exceeds max_age_seconds" in e for e in errs)


class TestReceiptEnforcementInExecutionPath:
    """Kiểm tra tính bắt buộc của Receipt trong execution path thực tế."""

    def test_seal_execution_receipt_attaches_to_execution_result(self):
        layer = ExecutionIntegrityLayer(mission_id="mission_test_receipt")
        receipt = layer.seal_execution_receipt(
            action="view_file",
            arguments={"file_path": "README.md"},
            output="# JKAI Zenith Sovereign OS",
            task_id="mission_test_receipt"
        )
        assert receipt is not None
        assert receipt.action == "view_file"
        assert receipt.lds_legal is True
        assert receipt.hmac_signature != ""

        # Gắn vào ExecutionResult
        res = ExecutionResult(
            outcome=DecisionOutcome.ALLOW,
            tool_executed=True,
            result="# JKAI Zenith Sovereign OS",
            action="view_file",
            receipt=receipt.to_dict()
        )
        assert res.receipt is not None
        assert res.receipt["receipt_id"] == receipt.receipt_id
        assert res.receipt["lds_legal"] is True
        assert "hmac_signature" in res.receipt

    def test_tampered_execution_result_receipt_detected(self):
        layer = ExecutionIntegrityLayer(mission_id="mission_test_receipt")
        receipt = layer.seal_execution_receipt(
            action="view_file",
            arguments={"file_path": "README.md"},
            output="Original output",
            task_id="mission_test_receipt"
        )
        raw_dict = receipt.to_dict()
        raw_dict["output_hash"] = "hacked_hash_12345"

        reconstructed = ExecutionReceipt(**raw_dict)
        gov = EnterpriseRuntimeGovernance()
        assert not gov.verify_receipt(reconstructed)

    def test_receipt_sealing_failure_blocks_execution_fail_closed(self):
        from receptionist.executor_gateway import _seal_receipt_fail_closed

        class BrokenIntegrity:
            def seal_execution_receipt(self, **kwargs):
                raise RuntimeError("Hardware cryptographic enclave communication error")

        decision = ExecutionDecision(
            outcome=DecisionOutcome.ALLOW,
            reason="Authorized",
            action="view_file"
        )
        ok, rcpt_dict, err_msg = _seal_receipt_fail_closed(
            BrokenIntegrity(), "view_file", {"Path": "test.txt"}, "result", decision, "t1"
        )
        assert ok is False
        assert rcpt_dict is None
        assert "FAIL-CLOSED" in err_msg


class TestSecretManagementFailClosed:
    """Kiểm tra quản trị Secret: fail-closed trong production & injection."""

    def test_secret_missing_fail_closed_in_production(self, monkeypatch):
        monkeypatch.setenv("JKAI_ENV", "production")
        monkeypatch.delenv("JKAI_GOVERNANCE_SECRET", raising=False)
        monkeypatch.delenv("SOVEREIGN_GOVERNANCE_SECRET", raising=False)

        with pytest.raises(RuntimeError) as exc_info:
            EnterpriseRuntimeGovernance()
        assert "GOVERNANCE_SECRET_MISSING" in str(exc_info.value)

    def test_subprocess_clean_production_fail_closed(self):
        import subprocess
        clean_env = os.environ.copy()
        clean_env["JKAI_ENV"] = "production"
        clean_env.pop("JKAI_GOVERNANCE_SECRET", None)
        clean_env.pop("SOVEREIGN_GOVERNANCE_SECRET", None)

        cmd = [
            sys.executable, "-c",
            "from core.kernel.lds_risk_governance import EnterpriseRuntimeGovernance; EnterpriseRuntimeGovernance()"
        ]
        res = subprocess.run(cmd, env=clean_env, capture_output=True, text=True)
        assert res.returncode != 0
        assert "GOVERNANCE_SECRET_MISSING" in res.stderr

    def test_custom_secret_injection(self):
        custom_key = b"super_secret_audit_key_32bytes_long!"
        gov = EnterpriseRuntimeGovernance(secret_key=custom_key)
        assert gov.secret_key == custom_key

        verdict = LDSVerdict(
            is_legal=True, authority_ok=True, context_ok=True, time_ok=True, integrity_ok=True, evidence_ok=True,
            risk_tier=RiskTier.GREEN
        )
        receipt = gov.seal_receipt("t1", "view_file", {"Path": "a.txt"}, "ok", verdict)
        assert receipt.verify_signature(custom_key) is True
        assert receipt.verify_signature(b"wrong_key") is False

    def test_environment_secret_resolution(self, monkeypatch):
        monkeypatch.setenv("JKAI_GOVERNANCE_SECRET", "custom_env_secret_key_999")
        sec = _resolve_governance_secret()
        assert sec == b"custom_env_secret_key_999"


class TestAGHResourceLeases:
    """Kiểm tra cơ chế khóa tài nguyên đa Agent (AGH Leases - Memory)."""

    def setup_method(self):
        self.lm = ResourceLeaseManager(default_ttl=1.0)

    def test_exclusive_lease_acquisition(self):
        token_a = self.lm.acquire("/workspace/app.py", holder_id="agent_A")
        assert token_a is not None

        # Agent B attempts to acquire same file -> blocked
        token_b = self.lm.acquire("/workspace/app.py", holder_id="agent_B")
        assert token_b is None

        # Agent A can re-acquire/extend
        token_a2 = self.lm.acquire("/workspace/app.py", holder_id="agent_A")
        assert token_a2 is not None

    def test_lease_release(self):
        token = self.lm.acquire("/workspace/config.yaml", holder_id="agent_A")
        assert self.lm.is_locked("/workspace/config.yaml", holder_id="agent_B")

        self.lm.release("/workspace/config.yaml", holder_id="agent_A", lease_token=token)
        assert not self.lm.is_locked("/workspace/config.yaml", holder_id="agent_B")

        # Now agent B can acquire
        token_b = self.lm.acquire("/workspace/config.yaml", holder_id="agent_B")
        assert token_b is not None

    def test_fencing_token_validation_and_takeover(self):
        token_a = self.lm.acquire("/workspace/app.py", holder_id="agent_A")
        assert token_a is not None
        assert self.lm.validate_fencing_token("/workspace/app.py", holder_id="agent_A", lease_token=token_a) is True

        # Stale holder check
        assert self.lm.validate_fencing_token("/workspace/app.py", holder_id="agent_B", lease_token=token_a) is False
        assert self.lm.validate_fencing_token("/workspace/app.py", holder_id="agent_A", lease_token="fake_token") is False

        # Mandatory lease_token on release: release without token must fail
        assert self.lm.release("/workspace/app.py", holder_id="agent_A", lease_token=None) is False
        assert self.lm.is_locked("/workspace/app.py", holder_id="agent_B") is True


class TestCrossProcessFileResourceLease:
    """Kiểm tra atomic cross-process locking giữa các instance riêng biệt."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="jkai_test_leases_")
        self.lm1 = ResourceLeaseManager(default_ttl=0.3, lock_dir=self.tmp_dir)
        self.lm2 = ResourceLeaseManager(default_ttl=0.3, lock_dir=self.tmp_dir)

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_cross_process_mutual_exclusion(self):
        # lm1 (Agent 1 / Process 1) acquires target file
        token1 = self.lm1.acquire("/data/shared_db.sqlite", holder_id="proc_1")
        assert token1 is not None

        # lm2 (Agent 2 / Process 2) attempts to acquire -> must be rejected
        token2 = self.lm2.acquire("/data/shared_db.sqlite", holder_id="proc_2")
        assert token2 is None
        assert self.lm2.is_locked("/data/shared_db.sqlite", holder_id="proc_2") is True

    def test_cross_process_lease_expiry_takeover(self):
        token1 = self.lm1.acquire("/data/stale_file.txt", holder_id="proc_1", ttl=0.1)
        assert token1 is not None

        # Wait for TTL to expire
        time.sleep(0.15)

        # lm2 can now acquire the expired lease
        token2 = self.lm2.acquire("/data/stale_file.txt", holder_id="proc_2", ttl=0.5)
        assert token2 is not None
        assert self.lm1.is_locked("/data/stale_file.txt", holder_id="proc_1") is True

    def test_cross_process_release_and_reacquire(self):
        token1 = self.lm1.acquire("/data/pipe.log", holder_id="proc_1")
        assert token1 is not None

        # lm1 releases
        assert self.lm1.release("/data/pipe.log", holder_id="proc_1", lease_token=token1) is True

        # lm2 acquires immediately
        token2 = self.lm2.acquire("/data/pipe.log", holder_id="proc_2")
        assert token2 is not None


class TestMeruGlassBoxIntegerStates:
    """Kiểm tra hộp kính trạng thái số nguyên (Meru OS Integer States)."""

    def setup_method(self):
        self.gov = EnterpriseRuntimeGovernance()

    def test_integer_state_transitions(self):
        assert self.gov.get_state_history() == [int(AgentStateCode.IDLE)]

        self.gov.record_state(AgentStateCode.INTENT_ROUTED)
        self.gov.record_state(AgentStateCode.LDS_EVALUATING)
        self.gov.record_state(AgentStateCode.EXECUTING_SUBSTRATE)
        self.gov.record_state(AgentStateCode.POST_RECEIPT_SEALED)
        self.gov.record_state(AgentStateCode.COMPLETED)

        history = self.gov.get_state_history()
        expected = [
            0x00, # IDLE
            0x10, # INTENT_ROUTED
            0x20, # LDS_EVALUATING
            0x40, # EXECUTING_SUBSTRATE
            0x50, # POST_RECEIPT_SEALED
            0xFF  # COMPLETED
        ]
        assert history == expected


class TestMissionRuntimeReceiptIntegration:
    """Kiểm tra P0: MissionRuntime tích hợp ExecutionReceipt mật mã học thay vì receipt giả."""

    @pytest.mark.asyncio
    async def test_mission_runtime_wrapped_executor_seals_real_receipt(self):
        from unittest.mock import MagicMock, AsyncMock
        from core.kernel.mission_runtime import MissionRuntime

        mock_event_store = MagicMock()
        mock_snapshot_engine = MagicMock()
        mock_scheduler = MagicMock()
        mock_shadow = MagicMock()

        runtime = MissionRuntime(shadow_harness=mock_shadow)
        runtime.event_store = mock_event_store
        runtime.snapshot_engine = mock_snapshot_engine
        runtime.scheduler = mock_scheduler

        captured_wrapped = []
        async def fake_execute_plan(mission_id, plan, ctx, wrapped_executor):
            captured_wrapped.append(wrapped_executor)
            return True

        mock_scheduler.execute_plan = fake_execute_plan
        mock_plan = MagicMock()
        mock_plan.model_dump.return_value = {}
        mock_state = MagicMock()
        mock_state.plan = mock_plan
        mock_state.context = {}
        mock_snapshot_engine.get_latest_state.return_value = mock_state
        mock_event_store.get_events.return_value = []

        fake_executor = AsyncMock(return_value="Mission step executed successfully")
        success = await runtime.execute_mission("m_test_123", mock_plan, fake_executor)
        assert success is True
        assert len(captured_wrapped) == 1

        wrapped = captured_wrapped[0]
        node = MagicMock()
        node.id = "step_01"
        node.name = "view_file"
        node.capability = "view_file"

        res = await wrapped(node, {"file_path": "test.txt"})
        assert res == "Mission step executed successfully"

        # Verify shadow_harness received REAL ExecutionReceipt
        assert mock_shadow.record_observation.called
        call_kwargs = mock_shadow.record_observation.call_args[1]
        rcpt = call_kwargs["execution_receipt"]
        assert isinstance(rcpt, dict)
        assert rcpt["receipt_id"].startswith("rcpt_")
        assert rcpt["task_id"] == "m_test_123"
        assert rcpt["action"] == "view_file"
        assert "hmac_signature" in rcpt
        assert "output" not in rcpt  # No raw output leaked in receipt!

    @pytest.mark.asyncio
    async def test_mission_runtime_fail_closed_when_receipt_sealing_fails(self, monkeypatch):
        from unittest.mock import MagicMock, AsyncMock
        from core.kernel.mission_runtime import MissionRuntime
        import core.kernel.execution_integrity as ei_mod

        mock_event_store = MagicMock()
        mock_snapshot_engine = MagicMock()
        mock_scheduler = MagicMock()
        mock_shadow = MagicMock()

        runtime = MissionRuntime(shadow_harness=mock_shadow)
        runtime.event_store = mock_event_store
        runtime.snapshot_engine = mock_snapshot_engine
        runtime.scheduler = mock_scheduler

        captured_wrapped = []
        async def fake_execute_plan(mission_id, plan, ctx, wrapped_executor):
            captured_wrapped.append(wrapped_executor)
            return True

        mock_scheduler.execute_plan = fake_execute_plan
        mock_plan = MagicMock()
        mock_plan.model_dump.return_value = {}

        fake_executor = AsyncMock(return_value="Step output")
        await runtime.execute_mission("m_fail_closed", mock_plan, fake_executor)
        wrapped = captured_wrapped[0]

        # Force seal_execution_receipt to return None (simulated failure)
        monkeypatch.setattr(ei_mod.ExecutionIntegrityLayer, "seal_execution_receipt", lambda *a, **kw: None)

        node = MagicMock()
        node.id = "step_01"
        node.name = "view_file"
        node.capability = "view_file"

        with pytest.raises(RuntimeError) as exc_info:
            await wrapped(node, {"file_path": "test.txt"})
        assert "MISSION_RUNTIME_RECEIPT_FAIL_CLOSED" in str(exc_info.value)


class TestWeeklyExamRunnerHardening:
    """Kiểm tra P1: WeeklyExamRunner ledger recovery, hard budget, và dry-run capability separation."""

    def test_dry_run_separates_plumbing_from_capability_score_no_expected_echo(self, tmp_path):
        from core.os.cognition.weekly_exam_runner import WeeklyExamRunner

        ledger_file = str(tmp_path / "ledger.jsonl")
        runner = WeeklyExamRunner(ledger_file=ledger_file)
        report = runner.run_weekly_exam("A", dry_run=True)

        assert report["dry_run"] is True
        assert report["capability_score"] is None
        assert report["accuracy"] is None
        assert report["total_passed"] == 0
        assert report["plumbing_accuracy"] == 1.0
        assert report["plumbing_passed"] == 20

    def test_live_budget_exceeded_records_executed_tasks_and_flag(self, tmp_path, monkeypatch):
        import json
        import urllib.request
        from unittest.mock import MagicMock
        from core.os.cognition.weekly_exam_runner import WeeklyExamRunner
        import time as time_mod

        ledger_file = str(tmp_path / "ledger.jsonl")
        runner = WeeklyExamRunner(ledger_file=ledger_file)

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"response": "3000 kg"}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: mock_resp)

        # Simulate clock advancing past live_budget_seconds after 2 tasks
        base_t = 1000000.0
        calls = [0]
        def fake_time():
            calls[0] += 1
            if calls[0] <= 3:
                return base_t + 0.1 * calls[0]
            return base_t + 50.0  # Exceeds 10s budget

        monkeypatch.setattr(time_mod, "time", fake_time)
        report = runner.run_weekly_exam("A", dry_run=False, live_budget_seconds=10)

        assert report["budget_exceeded"] is True
        assert report["capability_status"] == "INCOMPLETE_BUDGET_EXCEEDED"
        assert report["capability_score"] is None
        assert report["executed_tasks"] < report["total_tasks"]
        assert report["executed_accuracy"] is not None

    def test_partial_write_recovery_in_chained_ledger(self, tmp_path):
        import json
        from core.os.cognition.weekly_exam_runner import WeeklyExamRunner

        ledger_file = tmp_path / "ledger.jsonl"
        runner = WeeklyExamRunner(ledger_file=str(ledger_file))
        runner.run_weekly_exam("A", dry_run=True)

        # Simulate partial corrupted write at the end of ledger
        with open(ledger_file, "a", encoding="utf-8") as f:
            f.write('{"timestamp": 12345, "corrupted_partial_line\n')

        # Second run must recover valid previous entry hash without crashing
        report2 = runner.run_weekly_exam("A", dry_run=True)
        assert report2["total_tasks"] == 20

        # Verify the newly appended line is valid JSON with non-GENESIS prev_sha256
        with open(ledger_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        last_entry = json.loads(lines[-1])
        assert last_entry["prev_sha256"] != "0" * 64


class TestShadowHarnessAndSanitizerHardening:
    """Kiểm tra Scope A: ShadowHarness & StateSanitizer làm sạch 4 trường, cắt skill scaffolding, phân loại GOOD/BAD."""

    def test_sanitizes_all_4_fields_and_aggregates_redaction_count(self, tmp_path):
        from core.governance.shadow_harness import ShadowHarness

        harness = ShadowHarness(telemetry_dir=str(tmp_path), enabled=True)
        raw_state = {
            "prompt": "<skill_instructions>Internal SKILL.md secret guide</skill_instructions> Kiểm tra hệ thống với key sk-" + "1234567890abcdefghijklmnopqrstuvwx"
        }
        reflex_draft = {
            "thought": "Dùng GitHub token gh" + "p_1234567890abcdefghijklmnopqrstuvwxyz để gọi API",
            "status": "success",
        }
        execution_receipt = {
            "receipt_id": "rcpt_test_01",
            "lds_legal": True,
            "hmac_signature": "sig_valid_hex",
            "leaked_note": "postgresql://admin:SuperSecret99@db.internal:5432/jkai",
        }
        metadata = {
            "api_key": "my_raw_secret_api_key_value",
        }

        cid = harness.start_observation(raw_state=raw_state, reflex_draft=reflex_draft, metadata=metadata)
        assert cid is not None
        # Pending observation in memory must ALREADY be sanitized and stripped of <skill_instructions>
        pending = harness._pending_observations[cid]
        assert "<skill_instructions>" not in pending["sanitized_state"]["prompt"]
        assert "sk-1234567890" not in pending["sanitized_state"]["prompt"]
        assert "ghp_1234567890" not in pending["reflex_draft"]["thought"]
        assert pending["metadata"]["api_key"] == "[REDACTED_SECRET_FIELD]"

        rec = harness.complete_observation(cid, execution_receipt=execution_receipt, metadata={"extra_secret": "secret_val"})
        assert rec is not None
        # Redactions from raw_state (1) + reflex_draft (1) + metadata (1) + execution_receipt (1) + extra_meta (1) >= 4
        assert rec.redaction_count >= 4
        assert "SuperSecret99" not in str(rec.execution_receipt)
        assert rec.metadata["outcome_class"] == "GOOD"

    def test_bad_observation_cannot_self_promote_to_good(self, tmp_path):
        from core.governance.shadow_harness import ShadowHarness

        harness = ShadowHarness(telemetry_dir=str(tmp_path), enabled=True)
        rec = harness.record_observation(
            raw_state={"prompt": "Delete production DB"},
            reflex_draft={"status": "success", "model_self_eval": "100% PERFECT"},
            execution_receipt={"receipt_id": "rcpt_bad", "lds_legal": False, "hmac_signature": ""},
        )
        assert rec is not None
        assert rec.metadata["outcome_class"] == "BAD"


class TestProductionFailureInjection:
    """Kiểm tra Scope C: 10 kịch bản Failure Injection & Restore Drill."""

    def test_corrupt_checkpoint_fails_closed_on_rollback(self, tmp_path):
        from core.kernel.dynamic_skill_creator import DynamicSkillCreator

        creator = DynamicSkillCreator(
            skills_root=str(tmp_path / "skills"),
            candidates_dir=str(tmp_path / "cands"),
            checkpoints_dir=str(tmp_path / "ckpts"),
        )
        corrupt_file = tmp_path / "corrupt_ckpt.json"
        corrupt_file.write_text("{broken_json_syntax", encoding="utf-8")

        res = creator.rollback_skill(str(corrupt_file))
        assert res["status"] == "error"
        assert "CORRUPT_CHECKPOINT" in res["reason"]

    @pytest.mark.asyncio
    async def test_executor_crash_and_timeout_do_not_produce_false_success_receipt(self):
        from unittest.mock import MagicMock, AsyncMock
        from core.kernel.mission_runtime import MissionRuntime

        mock_shadow = MagicMock()
        runtime = MissionRuntime(shadow_harness=mock_shadow)
        runtime.event_store = MagicMock()
        runtime.snapshot_engine = MagicMock()
        runtime.scheduler = MagicMock()

        captured_wrapped = []
        async def fake_execute_plan(mission_id, plan, ctx, wrapped_executor):
            captured_wrapped.append(wrapped_executor)
            return False

        runtime.scheduler.execute_plan = fake_execute_plan
        mock_plan = MagicMock()
        mock_plan.model_dump.return_value = {}

        # Simulate executor crash (TimeoutError / RuntimeError)
        crashing_executor = AsyncMock(side_effect=TimeoutError("EXECUTOR_SUBSTRATE_TIMEOUT_30S"))
        await runtime.execute_mission("m_timeout_test", mock_plan, crashing_executor)
        wrapped = captured_wrapped[0]

        node = MagicMock()
        node.id = "step_crash"
        node.name = "run_command"
        node.capability = "run_command"

        with pytest.raises(TimeoutError):
            await wrapped(node, {"CommandLine": "echo test"})

        # Shadow harness must NOT record a completed execution receipt on crash/timeout
        assert not mock_shadow.record_observation.called
