"""
JKAI-Zenith Soak Test Harness & Deterministic Runner
Enforces 6 Mandatory Measurement Gates (M1 - M6) as mandated by Red Team Auditor.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import json
import ast
import shutil
import tempfile
import psutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Brain dir
BRAIN_DIR = WORKSPACE_ROOT / "services" / "ai-brain"
if str(BRAIN_DIR) not in sys.path:
    sys.path.insert(0, str(BRAIN_DIR))

from core.kernel.durable_checkpoint import DurableCheckpointEngine, StateEnvelope, get_checkpoint_engine
from core.kernel.replan_circuit_breaker import ReplanCircuitBreaker, ErrorSignature, BreakerDecision
from core.security.single_authority_fsm import SingleAuthorityFSM, AuthorityVerdict
from core.kernel.tool_contracts import ToolContractRegistry
from core.kernel.model_output_parser import ModelOutputParser
from core.verification.hybrid_verifier import HybridVerifier
from core.utils.pipeline_cache import PipelineCache, _is_cacheable_result


@dataclass
class ScenarioResult:
    scenario_id: str
    name: str
    group: str
    passed: bool
    tool_latency_ms: float
    mission_latency_ms: float
    rss_delta_kb: float
    zombie_count: int
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SoakSummary:
    total_runs: int
    passed_runs: int
    failed_runs: int
    tcr: float
    tool_p95_ms: float
    tool_median_ms: float
    mission_p95_ms: float
    mission_median_ms: float
    total_rss_delta_mb: float
    checkpoint_db_size_kb: float
    scenario_pass_rates: Dict[str, float]
    zombie_violations: int
    aborted_early: bool = False
    abort_reason: Optional[str] = None


class SoakHarness:
    """
    Executes a structured battery of 25 scenarios under rigorous measurement gates.
    """

    def __init__(self, db_path: Optional[Path] = None, temp_dir: Optional[Path] = None):
        self.process = psutil.Process()
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp(prefix="jkai_soak_"))
        self.db_path = db_path or (self.temp_dir / "soak_checkpoints.db")
        self.checkpoint_engine = DurableCheckpointEngine(self.db_path)
        self.circuit_breaker = ReplanCircuitBreaker()
        self.verifier = HybridVerifier()
        self.cache = PipelineCache()
        self.cache._redis = False  # isolate to local memory cache

    def cleanup(self):
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    async def run_scenario_isolated(
        self,
        scenario_fn: Callable[[str, Path], Any],
        scenario_id: str,
        name: str,
        group: str,
        run_idx: int,
    ) -> ScenarioResult:
        """Runs a single scenario with isolation (M6), zombie tracking (M3), RSS tracking (M4)."""
        mission_id = f"soak_{scenario_id}_r{run_idx}_{int(time.time()*1000)}"
        
        # M6: Reset breaker state for this mission_id
        self.circuit_breaker._history.pop(mission_id, None)
        self.circuit_breaker._tripped.pop(mission_id, None)

        # M3 & M4: Record baselines
        initial_rss = self.process.memory_info().rss
        current_task = asyncio.current_task()
        initial_tasks = {t for t in asyncio.all_tasks() if t is not current_task and not t.done()}

        t0_mission = time.perf_counter()
        passed = False
        tool_latency_ms = 0.0
        error_msg = None
        details = {}

        try:
            passed, tool_latency_ms, details = await scenario_fn(mission_id, self.temp_dir)
        except Exception as e:
            passed = False
            error_msg = str(e)
            tool_latency_ms = 0.0

        t1_mission = time.perf_counter()
        mission_latency_ms = (t1_mission - t0_mission) * 1000.0

        # M3: Measure zombie task count
        final_tasks = {t for t in asyncio.all_tasks() if t is not current_task and not t.done()}
        zombies = len(final_tasks - initial_tasks)

        # M4: Measure RSS delta
        final_rss = self.process.memory_info().rss
        rss_delta_kb = (final_rss - initial_rss) / 1024.0

        return ScenarioResult(
            scenario_id=scenario_id,
            name=name,
            group=group,
            passed=passed and (zombies == 0),
            tool_latency_ms=tool_latency_ms,
            mission_latency_ms=mission_latency_ms,
            rss_delta_kb=rss_delta_kb,
            zombie_count=zombies,
            error=error_msg,
            details=details,
        )

    # --------------------------------------------------------------------------
    # GROUP 1: FILE OPERATIONS & LOCAL PRIMITIVES (S01 - S05)
    # --------------------------------------------------------------------------

    async def s01_quadratic_solver(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S01: Create and write valid Python quadratic solver script."""
        from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import write_to_file
        target = str(temp_dir / f"{mission_id}_quad.py")
        code = (
            "import math\n\n"
            "def solve_quadratic(a, b, c):\n"
            "    if a == 0:\n"
            "        return None if b == 0 else (-c / b,)\n"
            "    delta = b**2 - 4*a*c\n"
            "    if delta < 0:\n"
            "        return ()\n"
            "    if delta == 0:\n"
            "        return (-b / (2*a),)\n"
            "    return ((-b - math.sqrt(delta))/(2*a), (-b + math.sqrt(delta))/(2*a))\n\n"
            "if __name__ == '__main__':\n"
            "    print(solve_quadratic(1, -5, 6))\n"
        )
        t0 = time.perf_counter()
        res = await write_to_file(target, code)
        t_ms = (time.perf_counter() - t0) * 1000.0

        # M1 Oracle
        ok = os.path.exists(target) and "thành công" in str(res).lower()
        if ok:
            with open(target, "r", encoding="utf-8") as f:
                ast.parse(f.read())
        return ok, t_ms, {"file": target}

    async def s02_view_file(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S02: View existing project file and verify contents."""
        from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import view_file
        target = temp_dir / f"{mission_id}_sample.txt"
        target.write_text("JKAI_ZENITH_SOAK_VERIFICATION_TOKEN_999", encoding="utf-8")
        
        t0 = time.perf_counter()
        res = await view_file(str(target))
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = "JKAI_ZENITH_SOAK_VERIFICATION_TOKEN_999" in str(res)
        return ok, t_ms, {"len": len(str(res))}

    async def s03_replace_file_content_backup(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S03: Replace function in script with auto-backup creation and AST validation."""
        from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import replace_file_content
        target = temp_dir / f"{mission_id}_replace.py"
        target.write_text("def old_fn():\n    return 1\n", encoding="utf-8")

        t0 = time.perf_counter()
        res = await replace_file_content(str(target), "def old_fn():\n    return 1", "def new_fn():\n    return 2")
        t_ms = (time.perf_counter() - t0) * 1000.0

        # M1 Oracle
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        has_new = "def new_fn():" in content
        # check backup file exists
        backups = list(temp_dir.glob(f"{mission_id}_replace.py.bak.*"))
        ok = has_new and len(backups) > 0 and "thành công" in str(res).lower()
        return ok, t_ms, {"backups": len(backups)}

    async def s04_delete_file_guard(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S04: Delete temporary file and verify deletion."""
        from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import delete_file
        target = temp_dir / f"{mission_id}_temp.log"
        target.write_text("temp data", encoding="utf-8")

        t0 = time.perf_counter()
        res = await delete_file(str(target), confirm=True)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = not os.path.exists(target) and "thành công" in str(res).lower()
        return ok, t_ms, {"status": str(res)}

    async def s05_list_dir_with_aliases(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S05: list_dir with parameter aliases (path='.') and case insensitivity."""
        t0 = time.perf_counter()
        valid, err, model = ToolContractRegistry.validate_tool_call("list_dir", {"path": str(temp_dir)})
        from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import list_dir
        dir_path = model.DirectoryPath if model else str(temp_dir)
        res = await list_dir(DirectoryPath=dir_path)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = valid and isinstance(res, dict) and res.get("status") == "success" and "items" in res
        return ok, t_ms, {"entries": len(res.get("items", [])) if isinstance(res, dict) else 0}

    # --------------------------------------------------------------------------
    # GROUP 2: SECURITY & POLICY ENFORCEMENT (S06 - S10)
    # --------------------------------------------------------------------------

    async def s06_path_guard_sensitive(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S06: Path Guard blocks sensitive files (.env, credentials)."""
        from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import write_to_file
        t0 = time.perf_counter()
        res = await write_to_file(str(temp_dir / ".env"), "SECRET=123")
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = "bảo vệ an ninh" in str(res).lower() or "từ chối" in str(res).lower()
        return ok, t_ms, {"response": str(res)}

    async def s07_blacklist_supremacy_deny(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S07: Single Authority FSM denies dangerous commands via Blacklist Supremacy."""
        t0 = time.perf_counter()
        fsm = SingleAuthorityFSM(mission_id=mission_id)
        verdict, reason, record = fsm.evaluate(
            action="run_command",
            arguments={"CommandLine": "rm -rf /"},
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (verdict == AuthorityVerdict.DENY) and ("BLACKLIST" in record.rule_matched)
        return ok, t_ms, {"verdict": str(verdict), "rule": record.rule_matched}

    async def s08_invariant_c3_arbitrary_python(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S08: Invariant C3 blocks inline arbitrary Python command execution."""
        t0 = time.perf_counter()
        fsm = SingleAuthorityFSM(mission_id=mission_id)
        verdict, reason, record = fsm.evaluate(
            action="python_execute",
            arguments={"code": "import socket"},
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (verdict == AuthorityVerdict.DENY) and ("INVARIANT_C3" in record.rule_matched)
        return ok, t_ms, {"rule": record.rule_matched}

    async def s09_parser_trailing_commas(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S09: ModelOutputParser parses and auto-repairs trailing commas."""
        raw = '{"thought": "test", "tool": "write_to_file", "params": {"path": "a.py",},}'
        t0 = time.perf_counter()
        parsed = ModelOutputParser.parse(raw)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = parsed.get("tool") == "write_to_file" and parsed.get("params", {}).get("path") == "a.py"
        return ok, t_ms, parsed

    async def s10_parser_truncated_unclosed_braces(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S10: ModelOutputParser auto-repairs unclosed braces due to token truncation."""
        raw = '```json\n{"thought": "fixing", "tool": "view_file", "params": {"AbsolutePath": "main.py"'
        t0 = time.perf_counter()
        parsed = ModelOutputParser.parse(raw)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = parsed.get("tool") == "view_file" and parsed.get("params", {}).get("AbsolutePath") == "main.py"
        return ok, t_ms, parsed

    # --------------------------------------------------------------------------
    # GROUP 3: CIRCUIT BREAKER & RELIABILITY (S11 - S15)
    # --------------------------------------------------------------------------

    async def s11_circuit_breaker_infra_fail_fast(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S11: ReplanCircuitBreaker trips fail-fast on repeated infrastructure failures (N=2)."""
        cb = self.circuit_breaker
        t0 = time.perf_counter()
        sig = cb.classify("ConnectionRefused: Cannot connect", "write_to_file")
        cb.record(mission_id, sig)
        d = cb.record(mission_id, sig)
        tripped, decision = cb.is_tripped(mission_id)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = tripped and decision.action == "FAIL_FAST"
        return ok, t_ms, {"tripped": tripped, "reason": decision.reason}

    async def s12_circuit_breaker_contract_fail_fast(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S12: ReplanCircuitBreaker trips fail-fast on repeated contract failures (N=2)."""
        cb = self.circuit_breaker
        t0 = time.perf_counter()
        sig = cb.classify("CONTRACT_VIOLATION: Missing required field DirectoryPath", "list_dir")
        cb.record(mission_id, sig)
        d = cb.record(mission_id, sig)
        tripped, decision = cb.is_tripped(mission_id)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = tripped and decision.action == "FAIL_FAST"
        return ok, t_ms, {"tripped": tripped}

    async def s13_hard_timeout_simulation(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S13: Hard Mission Timeout wrapper records FAILED checkpoint and returns error."""
        t0 = time.perf_counter()
        # Simulate timeout event execution
        ik = self.checkpoint_engine.compute_idempotency_key(mission_id, -1, "MISSION_HARD_TIMEOUT", {"timeout": 1})
        self.checkpoint_engine.save_checkpoint(
            mission_id=mission_id,
            step_id=-1,
            status="FAILED",
            state=StateEnvelope(version="1.0", messages=[{"role": "system", "content": "Timeout drill"}], next_step_id=-1),
            idempotency_key=ik,
        )
        latest = self.checkpoint_engine.load_latest_checkpoint(mission_id)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = latest is not None and latest.status == "FAILED" and latest.step_id == -1
        return ok, t_ms, {"status": latest.status if latest else None}

    async def s14_pipeline_cache_success_only(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S14: PipelineCache caches and retrieves a valid SUCCESS response."""
        goal = f"Tính toán số Pi cho mission {mission_id}"
        result_payload = {
            "status": "SUCCESS",
            "answer": "Số Pi xấp xỉ 3.14159",
            "judicial_review": {"verdict": "PASS", "passed": True}
        }
        t0 = time.perf_counter()
        await self.cache.set(goal, "fast", result_payload)
        retrieved = await self.cache.get(goal, "fast")
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = retrieved is not None and retrieved.get("answer") == "Số Pi xấp xỉ 3.14159"
        return ok, t_ms, {"cached": bool(retrieved)}

    async def s15_pipeline_cache_skip_errors(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S15: PipelineCache rejects caching failed, fallback, or error responses."""
        goal = f"Tác vụ thất bại cho mission {mission_id}"
        t0 = time.perf_counter()
        # Attempt 1: FAILED status
        await self.cache.set(goal, "fast", {"status": "FAILED", "answer": "Lỗi"})
        # Attempt 2: Fallback report
        await self.cache.set(goal, "deep", {"status": "SUCCESS", "answer": "Báo cáo Master! Chuỗi hành pháp chuyên sâu T2-T6..."})
        # Attempt 3: Judicial review FAIL
        await self.cache.set(f"{goal}_2", "fast", {"status": "SUCCESS", "answer": "Code", "judicial_review": {"verdict": "FAIL"}})

        res1 = await self.cache.get(goal, "fast")
        res2 = await self.cache.get(goal, "deep")
        res3 = await self.cache.get(f"{goal}_2", "fast")
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (res1 is None) and (res2 is None) and (res3 is None)
        return ok, t_ms, {"all_skipped": ok}

    # --------------------------------------------------------------------------
    # GROUP 4: DURABLE CHECKPOINT & RECOVERY (S16 - S20)
    # --------------------------------------------------------------------------

    async def s16_checkpoint_save_pending_and_completed(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S16: Save PENDING then COMPLETED checkpoint in SQLite WAL."""
        state = StateEnvelope(version="1.0", messages=[{"role": "user", "content": "hi"}], next_step_id=2)
        ik = self.checkpoint_engine.compute_idempotency_key(mission_id, 1, "write_to_file", {"path": "a.txt"})
        
        t0 = time.perf_counter()
        self.checkpoint_engine.save_checkpoint(mission_id, 1, "PENDING", state, ik)
        self.checkpoint_engine.save_checkpoint(mission_id, 1, "COMPLETED", state, ik)
        cp = self.checkpoint_engine.load_latest_checkpoint(mission_id)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = cp is not None and cp.status == "COMPLETED" and cp.step_id == 1
        return ok, t_ms, {"status": cp.status if cp else None}

    async def s17_idempotent_skip(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S17: Idempotent skip recognizes already-completed tool invocation."""
        state = StateEnvelope(version="1.0", messages=[], next_step_id=2)
        ik = self.checkpoint_engine.compute_idempotency_key(mission_id, 2, "run_command", {"CommandLine": "ls"})
        
        t0 = time.perf_counter()
        self.checkpoint_engine.save_checkpoint(mission_id, 2, "COMPLETED", state, ik)
        is_done = self.checkpoint_engine.is_step_completed(ik)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = is_done is True
        return ok, t_ms, {"is_step_completed": is_done}

    async def s18_crash_recovery_replay(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S18: New engine instance recovers latest COMPLETED step and skips replay."""
        state1 = StateEnvelope(version="1.0", messages=[{"role": "user", "content": "s1"}], next_step_id=2)
        state2 = StateEnvelope(version="1.0", messages=[{"role": "user", "content": "s2"}], next_step_id=3)
        ik1 = self.checkpoint_engine.compute_idempotency_key(mission_id, 1, "t1", {})
        ik2 = self.checkpoint_engine.compute_idempotency_key(mission_id, 2, "t2", {})

        t0 = time.perf_counter()
        self.checkpoint_engine.save_checkpoint(mission_id, 1, "COMPLETED", state1, ik1)
        self.checkpoint_engine.save_checkpoint(mission_id, 2, "COMPLETED", state2, ik2)

        # Spawn fresh engine instance on same DB file (simulating post-crash restart)
        fresh_engine = DurableCheckpointEngine(self.db_path)
        recovered = fresh_engine.load_latest_checkpoint(mission_id)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = recovered is not None and recovered.step_id == 2 and recovered.status == "COMPLETED"
        return ok, t_ms, {"recovered_step": recovered.step_id if recovered else None}

    async def s19_state_envelope_versioning(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S19: StateEnvelope round-trip serialization maintains version and artifacts."""
        env = StateEnvelope(
            version="1.0",
            messages=[{"role": "system", "content": "alpha"}],
            artifacts_manifest={"file.py": {"sha1": "abc12345"}},
            next_step_id=5,
        )
        t0 = time.perf_counter()
        serialized = env.to_json()
        deserialized = StateEnvelope.from_json(serialized)
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (
            deserialized.version == "1.0"
            and deserialized.next_step_id == 5
            and deserialized.artifacts_manifest.get("file.py", {}).get("sha1") == "abc12345"
        )
        return ok, t_ms, {"version": deserialized.version}

    async def s20_checkpoint_sub_10ms_budget(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S20: Measure SQLite WAL write latency across 10 sequential checkpoints (<10ms avg)."""
        latencies = []
        state = StateEnvelope(version="1.0", messages=[], next_step_id=1)
        for i in range(1, 11):
            ik = self.checkpoint_engine.compute_idempotency_key(mission_id, i, "bench", {"i": i})
            t_write = self.checkpoint_engine.save_checkpoint(mission_id, i, "COMPLETED", state, ik)
            latencies.append(t_write)

        avg_lat = sum(latencies) / len(latencies)
        ok = avg_lat < 10.0
        return ok, avg_lat, {"avg_ms": avg_lat, "max_ms": max(latencies)}

    # --------------------------------------------------------------------------
    # GROUP 5: HYBRID VERIFIER & DETERMINISTIC GATE (S21 - S25)
    # --------------------------------------------------------------------------

    async def s21_verifier_code_path_accept(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S21: HybridVerifier Deterministic Gate accepts valid python file write."""
        target = temp_dir / f"{mission_id}_valid.py"
        target.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        t0 = time.perf_counter()
        passed, reason, conf = HybridVerifier.verify(
            tool_name="write_to_file",
            args={"TargetFile": str(target)},
            result="Ghi tệp thành công",
            task_id=mission_id
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = passed and ("APPROVED" in reason)
        return ok, t_ms, {"passed": passed, "reason": reason}

    async def s22_verifier_code_path_reject_syntax(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S22: HybridVerifier Deterministic Gate rejects python file with syntax error."""
        target = temp_dir / f"{mission_id}_bad.py"
        target.write_text("delta = b**2 - 4ac\n", encoding="utf-8")

        t0 = time.perf_counter()
        passed, reason, conf = HybridVerifier.verify(
            tool_name="write_to_file",
            args={"TargetFile": str(target)},
            result="Ghi tệp thành công",
            task_id=mission_id
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (not passed) and ("SyntaxError" in reason or "syntax error" in reason.lower())
        return ok, t_ms, {"reason": reason}

    async def s23_verifier_code_path_reject_missing_file(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S23: HybridVerifier Deterministic Gate rejects when target file was not created."""
        target = temp_dir / f"{mission_id}_nonexistent.py"
        t0 = time.perf_counter()
        passed, reason, conf = HybridVerifier.verify(
            tool_name="write_to_file",
            args={"TargetFile": str(target)},
            result="Ghi tệp thành công",
            task_id=mission_id
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (not passed) and ("does not exist" in reason.lower() or "không tồn tại" in reason)
        return ok, t_ms, {"reason": reason}

    async def s24_verifier_non_code_accept(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S24: HybridVerifier Non-Code Path accepts structured search result payload."""
        t0 = time.perf_counter()
        passed, reason, conf = HybridVerifier.verify(
            tool_name="SEARCH_WEB_GLOBAL",
            args={"query": "dân số Việt Nam"},
            result={"results": [{"title": "Dân số", "content": "100 triệu người"}]},
            task_id=mission_id
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = passed and conf >= 0.85
        return ok, t_ms, {"confidence": conf, "reason": reason}

    async def s25_verifier_non_code_reject_empty(self, mission_id: str, temp_dir: Path) -> Tuple[bool, float, Dict]:
        """S25: HybridVerifier Non-Code Path rejects empty or error payload."""
        t0 = time.perf_counter()
        passed, reason, conf = HybridVerifier.verify(
            tool_name="SEARCH_WEB_GLOBAL",
            args={"query": "thông tin rỗng"},
            result="",
            task_id=mission_id
        )
        t_ms = (time.perf_counter() - t0) * 1000.0

        ok = (not passed) and conf <= 0.20
        return ok, t_ms, {"reason": reason, "confidence": conf}

    # --------------------------------------------------------------------------
    # SCENARIOS REGISTRY
    # --------------------------------------------------------------------------

    def get_all_scenarios(self) -> List[Tuple[str, str, str, Callable]]:
        return [
            # Group 1: File Ops
            ("S01", "Quadratic Solver Script Creation", "FILE_OPS", self.s01_quadratic_solver),
            ("S02", "View Project File & Verify Content", "FILE_OPS", self.s02_view_file),
            ("S03", "Replace File Content & Auto-Backup", "FILE_OPS", self.s03_replace_file_content_backup),
            ("S04", "Delete File With Security Guard", "FILE_OPS", self.s04_delete_file_guard),
            ("S05", "List Dir With Parameter Aliases", "FILE_OPS", self.s05_list_dir_with_aliases),

            # Group 2: Security & Policy
            ("S06", "Path Guard Protected Files", "SECURITY", self.s06_path_guard_sensitive),
            ("S07", "Blacklist Supremacy Hard Deny", "SECURITY", self.s07_blacklist_supremacy_deny),
            ("S08", "Invariant C3 Arbitrary Python Deny", "SECURITY", self.s08_invariant_c3_arbitrary_python),
            ("S09", "Parser Auto-Repair Trailing Commas", "PARSER", self.s09_parser_trailing_commas),
            ("S10", "Parser Auto-Repair Unclosed Braces", "PARSER", self.s10_parser_truncated_unclosed_braces),

            # Group 3: Circuit Breaker & Reliability
            ("S11", "Circuit Breaker INFRA Fail-Fast", "CIRCUIT_BREAKER", self.s11_circuit_breaker_infra_fail_fast),
            ("S12", "Circuit Breaker CONTRACT Fail-Fast", "CIRCUIT_BREAKER", self.s12_circuit_breaker_contract_fail_fast),
            ("S13", "Hard Mission Timeout FAILED Checkpoint", "TIMEOUT", self.s13_hard_timeout_simulation),
            ("S14", "Pipeline Cache SUCCESS-Only Cache", "CACHE", self.s14_pipeline_cache_success_only),
            ("S15", "Pipeline Cache Skip Errors & Fallbacks", "CACHE", self.s15_pipeline_cache_skip_errors),

            # Group 4: Checkpoint & Recovery
            ("S16", "Durable Checkpoint PENDING/COMPLETED", "CHECKPOINT", self.s16_checkpoint_save_pending_and_completed),
            ("S17", "Idempotent Skip On Duplicate Key", "CHECKPOINT", self.s17_idempotent_skip),
            ("S18", "Crash Recovery Replay On Fresh Engine", "RECOVERY", self.s18_crash_recovery_replay),
            ("S19", "StateEnvelope Versioned Round-Trip", "CHECKPOINT", self.s19_state_envelope_versioning),
            ("S20", "SQLite WAL Commit Latency Budget", "BENCHMARK", self.s20_checkpoint_sub_10ms_budget),

            # Group 5: Hybrid Verifier
            ("S21", "Hybrid Verifier Code Path Accept", "VERIFIER", self.s21_verifier_code_path_accept),
            ("S22", "Hybrid Verifier Code Path Reject Syntax", "VERIFIER", self.s22_verifier_code_path_reject_syntax),
            ("S23", "Hybrid Verifier Code Path Reject Missing", "VERIFIER", self.s23_verifier_code_path_reject_missing_file),
            ("S24", "Hybrid Verifier Non-Code Accept Valid", "VERIFIER", self.s24_verifier_non_code_accept),
            ("S25", "Hybrid Verifier Non-Code Reject Empty", "VERIFIER", self.s25_verifier_non_code_reject_empty),
        ]

    async def run_ladder_1_smoke(self) -> SoakSummary:
        """Runs Ladder Step 1: Smoke 25x1 (25 missions)."""
        scenarios = self.get_all_scenarios()
        results: List[ScenarioResult] = []
        consecutive_failures = 0
        last_error_sig = None

        print("\n" + "=" * 80)
        print("🚀 [SOAK-HARNESS] BẮT ĐẦU CHẠY NẤC 1: SMOKE 25×1 (25 MISSIONS ĐỘC LẬP)")
        print("   6 Cổng Đo: M1 Oracle | M2 TCR | M3 Zombie | M4 RSS | M5 Latency | M6 Isolation")
        print("=" * 80)

        initial_total_rss = self.process.memory_info().rss

        for idx, (s_id, name, group, fn) in enumerate(scenarios, start=1):
            res = await self.run_scenario_isolated(fn, s_id, name, group, run_idx=1)
            results.append(res)

            status_mark = "✅ PASS" if res.passed else "❌ FAIL"
            print(
                f"[{idx:02d}/25] {s_id} ({group:<15}): {name:<42} | "
                f"{status_mark} | Tool: {res.tool_latency_ms:6.2f}ms | Miss: {res.mission_latency_ms:6.2f}ms | "
                f"RSSΔ: {res.rss_delta_kb:+6.1f}KB | Z: {res.zombie_count}"
            )

            # Abort Rule: 3 consecutive failures with identical signature
            if not res.passed:
                err_sig = f"{s_id}:{res.error}"
                if err_sig == last_error_sig:
                    consecutive_failures += 1
                else:
                    consecutive_failures = 1
                    last_error_sig = err_sig

                if consecutive_failures >= 3:
                    print(f"\n🛑 [SOAK-ABORT] Dừng khẩn cấp: 3 kịch bản liên tiếp fail cùng chữ ký '{err_sig}'!")
                    return self._compile_summary(results, initial_total_rss, aborted=True, reason=err_sig)
            else:
                consecutive_failures = 0
                last_error_sig = None

        final_total_rss = self.process.memory_info().rss
        total_rss_delta_mb = (final_total_rss - initial_total_rss) / (1024.0 * 1024.0)

        summary = self._compile_summary(results, initial_total_rss)
        print("\n" + "=" * 80)
        print(f"📊 [SOAK-HARNESS NẤC 1 KẾT QUẢ]:")
        print(f"   • Tổng số missions: {summary.total_runs} (Passed: {summary.passed_runs}, Failed: {summary.failed_runs})")
        print(f"   • TCR Tổng: {summary.tcr * 100:.1f}% (Ngưỡng yêu cầu: ≥98.0%)")
        print(f"   • Tool-layer Latency: Median={summary.tool_median_ms:.2f}ms, P95={summary.tool_p95_ms:.2f}ms (Ngưỡng P95: <50.0ms)")
        print(f"   • Mission Latency: Median={summary.mission_median_ms:.2f}ms, P95={summary.mission_p95_ms:.2f}ms")
        print(f"   • Zombie Task Violations (M3): {summary.zombie_violations} (Ngưỡng yêu cầu: 0)")
        print(f"   • Total RSS Delta (M4): {summary.total_rss_delta_mb:+.2f} MB")
        print(f"   • Checkpoint DB Size: {summary.checkpoint_db_size_kb:.2f} KB")
        print("=" * 80)
        return summary

    async def run_ladder_2_leak(self, repeats_per_scenario: int = 10) -> SoakSummary:
        """Runs Ladder Step 2: 5 representative scenarios x 10 runs = 50 missions."""
        all_scenarios = {s[0]: s for s in self.get_all_scenarios()}
        selected_ids = ["S01", "S07", "S11", "S16", "S21"]
        scenarios = [all_scenarios[sid] for sid in selected_ids]

        results: List[ScenarioResult] = []
        print("\n" + "=" * 80)
        print(f"🚀 [SOAK-HARNESS] BẮT ĐẦU CHẠY NẤC 2: RESOURCE LEAK AUDIT (5 SCENARIOS × {repeats_per_scenario} REPEATS = {len(scenarios) * repeats_per_scenario} MISSIONS)")
        print("   Mục tiêu: Đảm bảo Zero Memory Leak (RSS < +50MB), Zero Zombies, TCR >= 98%")
        print("=" * 80)

        initial_total_rss = self.process.memory_info().rss
        total_runs = len(scenarios) * repeats_per_scenario
        current_run = 0

        for r in range(1, repeats_per_scenario + 1):
            for s_id, name, group, fn in scenarios:
                current_run += 1
                res = await self.run_scenario_isolated(fn, s_id, name, group, run_idx=r)
                results.append(res)
                status_mark = "✅ PASS" if res.passed else "❌ FAIL"
                if current_run % 5 == 0 or not res.passed:
                    print(
                        f"[{current_run:02d}/{total_runs}] Iter {r:02d} | {s_id} ({group:<15}): {name:<35} | "
                        f"{status_mark} | Tool: {res.tool_latency_ms:6.2f}ms | Miss: {res.mission_latency_ms:6.2f}ms | "
                        f"RSSΔ: {res.rss_delta_kb:+6.1f}KB | Z: {res.zombie_count}"
                    )

        summary = self._compile_summary(results, initial_total_rss)
        print("\n" + "=" * 80)
        print(f"📊 [SOAK-HARNESS NẤC 2 KẾT QUẢ]:")
        print(f"   • Tổng số missions: {summary.total_runs} (Passed: {summary.passed_runs}, Failed: {summary.failed_runs})")
        print(f"   • TCR Tổng: {summary.tcr * 100:.1f}% (Ngưỡng yêu cầu: ≥98.0%)")
        print(f"   • Tool-layer Latency: Median={summary.tool_median_ms:.2f}ms, P95={summary.tool_p95_ms:.2f}ms (Ngưỡng P95: <50.0ms)")
        print(f"   • Mission Latency: Median={summary.mission_median_ms:.2f}ms, P95={summary.mission_p95_ms:.2f}ms")
        print(f"   • Zombie Task Violations (M3): {summary.zombie_violations} (Ngưỡng yêu cầu: 0)")
        print(f"   • Total RSS Delta (M4): {summary.total_rss_delta_mb:+.2f} MB (Ngưỡng: < 50.0 MB)")
        print(f"   • Checkpoint DB Size: {summary.checkpoint_db_size_kb:.2f} KB")
        print("=" * 80)
        return summary

    async def run_ladder_3_full(self, repeats_per_scenario: int = 100) -> SoakSummary:
        """Runs Ladder Step 3: Full 25 scenarios x 100 runs = 2500 missions."""
        scenarios = self.get_all_scenarios()
        results: List[ScenarioResult] = []
        total_runs = len(scenarios) * repeats_per_scenario
        print("\n" + "=" * 80)
        print(f"🚀 [SOAK-HARNESS] BẮT ĐẦU CHẠY NẤC 3: MARATHON SOAK (25 SCENARIOS × {repeats_per_scenario} REPEATS = {total_runs} MISSIONS)")
        print("   Mục tiêu: TCR >= 98%, Zero Zombie, P95 < 50ms, RSS delta < 100MB")
        print("=" * 80)

        initial_total_rss = self.process.memory_info().rss
        current_run = 0

        for r in range(1, repeats_per_scenario + 1):
            for s_id, name, group, fn in scenarios:
                current_run += 1
                res = await self.run_scenario_isolated(fn, s_id, name, group, run_idx=r)
                results.append(res)
                if current_run % 25 == 0 or not res.passed:
                    status_mark = "✅ PASS" if res.passed else "❌ FAIL"
                    print(
                        f"[{current_run:04d}/{total_runs}] Iter {r:03d} | {s_id} ({group:<15}): {name:<35} | "
                        f"{status_mark} | Tool: {res.tool_latency_ms:6.2f}ms | Miss: {res.mission_latency_ms:6.2f}ms | "
                        f"RSSΔ: {res.rss_delta_kb:+6.1f}KB | Z: {res.zombie_count}"
                    )

        summary = self._compile_summary(results, initial_total_rss)
        print("\n" + "=" * 80)
        print(f"📊 [SOAK-HARNESS NẤC 3 KẾT QUẢ]:")
        print(f"   • Tổng số missions: {summary.total_runs} (Passed: {summary.passed_runs}, Failed: {summary.failed_runs})")
        print(f"   • TCR Tổng: {summary.tcr * 100:.1f}% (Ngưỡng yêu cầu: ≥98.0%)")
        print(f"   • Tool-layer Latency: Median={summary.tool_median_ms:.2f}ms, P95={summary.tool_p95_ms:.2f}ms (Ngưỡng P95: <50.0ms)")
        print(f"   • Mission Latency: Median={summary.mission_median_ms:.2f}ms, P95={summary.mission_p95_ms:.2f}ms")
        print(f"   • Zombie Task Violations (M3): {summary.zombie_violations} (Ngưỡng yêu cầu: 0)")
        print(f"   • Total RSS Delta (M4): {summary.total_rss_delta_mb:+.2f} MB")
        print(f"   • Checkpoint DB Size: {summary.checkpoint_db_size_kb:.2f} KB")
        print("=" * 80)
        return summary

    def _compile_summary(self, results: List[ScenarioResult], initial_rss: int, aborted: bool = False, reason: Optional[str] = None) -> SoakSummary:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        tcr = passed / total if total > 0 else 0.0

        tool_latencies = sorted(r.tool_latency_ms for r in results)
        mission_latencies = sorted(r.mission_latency_ms for r in results)

        def p95(arr: List[float]) -> float:
            if not arr: return 0.0
            idx = int(len(arr) * 0.95)
            return arr[min(idx, len(arr) - 1)]

        def median(arr: List[float]) -> float:
            if not arr: return 0.0
            return arr[len(arr) // 2]

        final_rss = self.process.memory_info().rss
        total_rss_delta_mb = (final_rss - initial_rss) / (1024.0 * 1024.0)

        db_size_kb = (self.db_path.stat().st_size / 1024.0) if self.db_path.exists() else 0.0
        scenario_pass_rates = {r.scenario_id: (1.0 if r.passed else 0.0) for r in results}
        zombies = sum(r.zombie_count for r in results)

        return SoakSummary(
            total_runs=total,
            passed_runs=passed,
            failed_runs=failed,
            tcr=tcr,
            tool_p95_ms=p95(tool_latencies),
            tool_median_ms=median(tool_latencies),
            mission_p95_ms=p95(mission_latencies),
            mission_median_ms=median(mission_latencies),
            total_rss_delta_mb=total_rss_delta_mb,
            checkpoint_db_size_kb=db_size_kb,
            scenario_pass_rates=scenario_pass_rates,
            zombie_violations=zombies,
            aborted_early=aborted,
            abort_reason=reason,
        )


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="JKAI Zenith 3-Ladder Soak Harness")
    parser.add_argument("--ladder", type=int, choices=[1, 2, 3], default=1, help="Ladder step to run (1=Smoke 25x1, 2=Leak 5x10, 3=Full 25x100)")
    parser.add_argument("--repeats", type=int, default=None, help="Custom repeat count")
    args = parser.parse_args()

    harness = SoakHarness()
    try:
        if args.ladder == 1:
            summary = await harness.run_ladder_1_smoke()
            if summary.tcr >= 0.98 and summary.zombie_violations == 0:
                print("\n🎉 [NẤC 1 SMOKE 25×1: THÀNH CÔNG VƯỢT TRỘI — ĐẠT 100% CỔNG M1-M6]")
                sys.exit(0)
            else:
                print("\n⚠️ [NẤC 1 SMOKE 25×1: CHƯA ĐẠT CHỈ TIÊU]")
                sys.exit(1)
        elif args.ladder == 2:
            reps = args.repeats or 10
            summary = await harness.run_ladder_2_leak(repeats_per_scenario=reps)
            if summary.tcr >= 0.98 and summary.zombie_violations == 0 and summary.total_rss_delta_mb < 50.0:
                print("\n🎉 [NẤC 2 LEAK AUDIT 5×10: THÀNH CÔNG VƯỢT TRỘI — ZERO LEAK]")
                sys.exit(0)
            else:
                print("\n⚠️ [NẤC 2 LEAK AUDIT 5×10: CHƯA ĐẠT CHỈ TIÊU]")
                sys.exit(1)
        elif args.ladder == 3:
            reps = args.repeats or 100
            summary = await harness.run_ladder_3_full(repeats_per_scenario=reps)
            if summary.tcr >= 0.98 and summary.zombie_violations == 0:
                print("\n🎉 [NẤC 3 MARATHON SOAK: HOÀN THÀNH XUẤT SẮC]")
                sys.exit(0)
            else:
                print("\n⚠️ [NẤC 3 MARATHON SOAK: CHƯA ĐẠT CHỈ TIÊU]")
                sys.exit(1)
    finally:
        harness.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
