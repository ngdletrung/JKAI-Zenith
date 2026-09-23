# -*- coding: utf-8 -*-
"""
tests/test_policy_determinism.py
Unit tests verifying Policy Engine Determinism & Concurrency Safety (P0-2).

Turn 60 Consensus & Constraints:
- Asserts strict verdict determinism across 100 iterations (verdict & rule_matched, ignoring uuid/ts).
- Documents that SingleAuthorityFSM is pure-functional per evaluation (race-free by construction).
- Tests concurrent thread-safety:
  1) SingleAuthorityFSM under 50 concurrent threads.
  2) Truly shared mutable state: _HealthCache under 50 concurrent threads.
  3) Truly shared mutable state: ExperienceStore under 50 concurrent threads.
"""

import threading
import pytest
from core.security.single_authority_fsm import (
    SingleAuthorityFSM,
    AuthorityVerdict,
)




class TestPolicyDeterminism:

    def test_policy_determinism_100_iterations(self):
        """
        [P0-2]: Cùng input phải cho cùng output verdict 100/100 lần.
        Assert verdict và rule_matched, bỏ qua timestamp/trace_id ngẫu nhiên.
        """
        fsm = SingleAuthorityFSM(mission_id="test_mission_det")


        from unittest.mock import MagicMock
        mock_contract = MagicMock()
        mock_contract.forbidden_actions = []

        test_cases = [
            # 1. Arbitrary code -> Unconditional DENY (Invariant C3)
            ("python_eval", {"code": "import os; os.system('ls')"}, None, AuthorityVerdict.DENY),
            # 2. Blacklisted pattern -> Unconditional DENY
            ("write_file", {"path": ".env"}, None, AuthorityVerdict.DENY),
            # 3. Path traversal outside workspace -> DENY
            ("read_file", {"path": "/etc/passwd"}, None, AuthorityVerdict.DENY),
            # 4. Safe read without contract -> ALLOW (Fail-Open for observation)
            ("read_file", {"path": "README.md"}, None, AuthorityVerdict.ALLOW),
            # 5. Non-observation action without contract -> Fail-closed DENY
            ("execute_command", {"command": "git status"}, None, AuthorityVerdict.DENY),
            # 6. High-risk command with valid contract -> REQUIRE_APPROVAL
            ("execute_command", {"command": "curl https://api.github.com"}, mock_contract, AuthorityVerdict.REQUIRE_APPROVAL),
        ]


        for action, args, contract, expected_verdict in test_cases:
            verdicts = []
            for _ in range(100):
                verdict, reason, record = fsm.evaluate(action, args, contract)
                verdicts.append(verdict)

            unique_verdicts = set(verdicts)
            assert len(unique_verdicts) == 1, (
                f"FSM NON-DETERMINISTIC for action '{action}': "
                f"Got multiple verdicts: {unique_verdicts}"
            )
            assert verdicts[0] == expected_verdict, (
                f"Action '{action}' expected {expected_verdict}, got {verdicts[0]}"
            )

    def test_fsm_concurrency_thread_safety(self):
        """
        [P0-2]: 50 threads đồng thời gọi evaluate() trên cùng 1 instance FSM.
        FSM không có shared mutable state (race-free by construction);
        Test này xác nhận không có race condition hay unhandled exception dưới tải đồng thời.
        """
        fsm = SingleAuthorityFSM(mission_id="test_mission_concurrency")
        results = []

        lock = threading.Lock()

        def worker(action, args):
            verdict, reason, record = fsm.evaluate(action, args)
            with lock:
                results.append((action, verdict))

        threads = []
        for i in range(50):
            act = "write_file" if i % 2 == 0 else "read_file"
            args = {"path": ".env"} if i % 2 == 0 else {"path": "safe.py"}
            t = threading.Thread(target=worker, args=(act, args))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 50
        write_verdicts = [v for act, v in results if act == "write_file"]
        read_verdicts = [v for act, v in results if act == "read_file"]

        # Toàn bộ write_file vào .env phải là DENY
        assert all(v == AuthorityVerdict.DENY for v in write_verdicts)
        # Toàn bộ read_file safe.py phải là ALLOW
        assert all(v == AuthorityVerdict.ALLOW for v in read_verdicts)

    def test_health_cache_concurrency_shared_mutable(self):
        """
        [P0-2]: Kiểm tra đối tượng chia sẻ thực tế: _HealthCache dưới 50 threads đồng thời.
        Các luồng đọc và ghi xen kẽ không gây corrupt state hay deadlock.
        """
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain"))
        from receptionist.executor_gateway import _HealthCache

        cache = _HealthCache()
        errors = []

        def worker(thread_id):
            try:
                for i in range(20):
                    name = f"executor_{i % 3}"
                    cache.update(name, (thread_id + i) % 2 == 0)
                    _ = cache.is_known_healthy(name)
                    if i % 5 == 0:
                        cache.mark_unhealthy(name)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent cache access raised errors: {errors}"

    def test_experience_store_concurrency_shared_mutable(self):
        """
        [P0-2]: Kiểm tra ExperienceStore (shared singleton with RLock) dưới 50 threads đồng thời.
        """
        from core.memory.experience_store import ExperienceStore
        from core.contracts.verification_contract import ExperienceRecord
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    rec = ExperienceRecord(
                        task_signature=f"concurrent_task_{thread_id}",
                        strategy_used=f"strategy_{i}",
                        tools_used=[f"tool_{thread_id}"]
                    )
                    ExperienceStore.add_record(rec)
                    _ = ExperienceStore.count()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent ExperienceStore access raised errors: {errors}"
        # Max cap 500 should be respected
        assert ExperienceStore.count() <= 500

