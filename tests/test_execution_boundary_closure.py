# -*- coding: utf-8 -*-
"""
🧪 TEST SUITE: EXECUTION BOUNDARY CLOSURE & IMMUTABLE POLICY SNAPSHOT
File: tests/test_execution_boundary_closure.py

Kiểm chứng 4 Invariants cốt lõi:
1. JKAI-BND-001 (No Ungoverned Execution): Không có ExecutionGrant hợp lệ -> FAIL-CLOSED.
2. JKAI-BND-002 (Single Authority Boundary): Mọi tool call phải đi qua Authority Gateway.
3. JKAI-LAW-03 (Immutable Policy Snapshot): PolicySnapshot không thể bị giả mạo hay sửa đổi.
4. Defense Against Tampering: Can thiệp đối số hoặc chữ ký HMAC -> Bị chặn ngay lập tức.
"""

import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from core.kernel.policy_snapshot import (
    PolicySnapshot,
    create_policy_snapshot,
    issue_execution_grant,
    verify_execution_grant,
)
from core.kernel.execution_integrity import ExecutionIntegrityLayer, DecisionOutcome


class TestPolicySnapshotAndGrants(unittest.TestCase):
    def setUp(self):
        self.mission_id = "test_mission_001"
        self.snap = create_policy_snapshot(
            mission_id=self.mission_id,
            can_modify_files=True,
            can_delete_files=False,
            can_send_external_message=False,
            budget_max_turns=10
        )

    def test_policy_snapshot_creation_and_hash_integrity(self):
        """Kiểm tra tính toàn vẹn của mã băm PolicySnapshot."""
        self.assertIsNotNone(self.snap.snapshot_id)
        self.assertTrue(self.snap.snapshot_id.startswith("snap_"))
        self.assertEqual(self.snap.mission_id, self.mission_id)
        self.assertTrue(len(self.snap.snapshot_hash) > 0)
        self.assertEqual(self.snap.compute_hash(), self.snap.snapshot_hash)

    def test_valid_execution_grant_verification(self):
        """Cấp Grant hợp lệ và xác thực trên Executor -> Thành công."""
        tool_name = "SEARCH_WEB_GLOBAL"
        tool_args = {"query": "JKAI AI OS 2026"}

        grant = issue_execution_grant(
            mission_id=self.mission_id,
            snapshot_id=self.snap.snapshot_id,
            tool_name=tool_name,
            tool_args=tool_args,
            ttl_seconds=60.0
        )

        is_valid, reason = verify_execution_grant(
            grant.to_dict(),
            expected_tool=tool_name,
            actual_args=tool_args
        )
        self.assertTrue(is_valid)
        self.assertIn("hợp lệ", reason)

    def test_missing_or_null_grant_fails_closed(self):
        """Gọi Executor không có Grant -> FAIL-CLOSED (Bị từ chối)."""
        is_valid, reason = verify_execution_grant(
            None,
            expected_tool="OFFICE_SUITE_MASTER",
            actual_args={"action": "create_excel"}
        )
        self.assertFalse(is_valid)
        self.assertIn("FAIL-CLOSED", reason)

    def test_tampered_args_fails_verification(self):
        """Thay đổi đối số sau khi được cấp Grant -> Phát hiện can thiệp và từ chối."""
        tool_name = "OFFICE_SUITE_MASTER"
        tool_args = {"action": "create_excel", "filename": "report.xlsx"}

        grant = issue_execution_grant(
            mission_id=self.mission_id,
            snapshot_id=self.snap.snapshot_id,
            tool_name=tool_name,
            tool_args=tool_args,
            ttl_seconds=60.0
        )

        # Kẻ tấn công sửa filename thành file nhạy cảm
        tampered_args = {"action": "create_excel", "filename": "/etc/shadow"}

        is_valid, reason = verify_execution_grant(
            grant.to_dict(),
            expected_tool=tool_name,
            actual_args=tampered_args
        )
        self.assertFalse(is_valid)
        self.assertIn("không khớp với mã băm", reason)

    def test_tampered_signature_fails_verification(self):
        """Làm giả chữ ký HMAC -> Bị chặn."""
        tool_name = "SEARCH_WEB_GLOBAL"
        tool_args = {"query": "AI Agents"}

        grant = issue_execution_grant(
            mission_id=self.mission_id,
            snapshot_id=self.snap.snapshot_id,
            tool_name=tool_name,
            tool_args=tool_args,
            ttl_seconds=60.0
        )

        grant_dict = grant.to_dict()
        grant_dict["signature"] = "forged_bad_signature_0000000000000000"

        is_valid, reason = verify_execution_grant(
            grant_dict,
            expected_tool=tool_name,
            actual_args=tool_args
        )
        self.assertFalse(is_valid)
        self.assertIn("không hợp lệ hoặc bị giả mạo", reason)

    def test_expired_grant_fails_verification(self):
        """Grant đã quá hạn TTL -> Từ chối."""
        tool_name = "SEARCH_WEB_GLOBAL"
        tool_args = {"query": "Test"}

        # Cấp grant với TTL âm (đã hết hạn)
        grant = issue_execution_grant(
            mission_id=self.mission_id,
            snapshot_id=self.snap.snapshot_id,
            tool_name=tool_name,
            tool_args=tool_args,
            ttl_seconds=-10.0
        )

        is_valid, reason = verify_execution_grant(
            grant.to_dict(),
            expected_tool=tool_name,
            actual_args=tool_args
        )
        self.assertFalse(is_valid)
        self.assertIn("hết hạn", reason)

    def test_execution_integrity_layer_issues_grant_on_allow(self):
        """ExecutionIntegrityLayer cấp grant đính kèm khi ra quyết định ALLOW."""
        integrity = ExecutionIntegrityLayer(mission_id=self.mission_id)
        decision = integrity.authorize(
            action="SEARCH_WEB_GLOBAL",
            arguments={"query": "JKAI AI OS"},
            snapshot=self.snap
        )

        self.assertEqual(decision.outcome, DecisionOutcome.ALLOW)
        self.assertIsNotNone(decision.grant)
        self.assertEqual(decision.grant.get("tool_name"), "SEARCH_WEB_GLOBAL")
        self.assertTrue(len(decision.grant.get("signature", "")) > 0)


if __name__ == "__main__":
    unittest.main()
