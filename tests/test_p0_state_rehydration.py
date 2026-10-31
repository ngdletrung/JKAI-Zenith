# -*- coding: utf-8 -*-
"""
test_p0_state_rehydration.py
Harness kiểm định Hợp đồng State Rehydration & Task Recovery
Kiểm chứng 9 tiêu chí bất biến của OpenCode & Master (SDS v28.27.0).
"""

import copy
import hashlib
import json
import unittest
from typing import Dict, List, Optional, Any


class StateRehydrationError(Exception):
    """Lỗi trạng thái trong quá trình rehydration."""
    pass


class SequenceGapError(StateRehydrationError):
    """Phát hiện lỗ hổng chuỗi sự kiện (Sequence Gap)."""
    def __init__(self, expected_seq: int, received_seq: int):
        super().__init__(f"SEQUENCE_GAP_DETECTED(expected={expected_seq}, received={received_seq})")
        self.expected_seq = expected_seq
        self.received_seq = received_seq


class StaleClientError(StateRehydrationError):
    """Khách hàng gửi state/action với version cũ bị từ chối."""
    pass


class RehydrationEngine:
    """
    Engine mô phỏng Event Sourcing & Checkpoint Rehydration theo chuẩn Redis Event Stream.
    Đảm bảo tính bất biến, idempotent và khả năng phục hồi sau sự cố (F5 / worker crash).
    """

    TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.current_seq: int = 0
        self.state: Dict[str, Any] = {
            "task_id": task_id,
            "status": "INITIALIZED",
            "progress_percent": 0,
            "applied_actions": [],
            "version": 0,
            "terminal_reached": False,
        }
        self.event_log: List[Dict[str, Any]] = []
        self.checkpoints: Dict[int, Dict[str, Any]] = {}
        self.processed_event_ids: set = set()

    def create_checkpoint(self) -> Dict[str, Any]:
        """Tạo điểm phục hồi nguyên tử (Atomic Checkpoint) tại sequence hiện tại."""
        snapshot = copy.deepcopy(self.state)
        snapshot_bytes = json.dumps(snapshot, sort_keys=True).encode("utf-8")
        checkpoint_record = {
            "seq_id": self.current_seq,
            "state_snapshot": snapshot,
            "checkpoint_hash": hashlib.sha256(snapshot_bytes).hexdigest(),
        }
        self.checkpoints[self.current_seq] = checkpoint_record
        return checkpoint_record

    def apply_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Áp dụng một sự kiện theo thứ tự đơn điệu tăng nghiêm ngặt."""
        event_id = event["event_id"]
        seq_id = event["seq_id"]
        event_type = event["type"]
        payload = event.get("payload", {})

        # 1. Duplicate Handling: Bỏ qua an toàn nếu event_id đã xử lý
        if event_id in self.processed_event_ids:
            return self.state

        # 2. Sequence Monotonicity & Gap Detection
        expected_seq = self.current_seq + 1
        if seq_id < expected_seq:
            # Event cũ hoặc đến muộn đã có trong log
            return self.state
        if seq_id > expected_seq:
            # Phát hiện lỗ hổng sự kiện!
            raise SequenceGapError(expected_seq=expected_seq, received_seq=seq_id)

        # 3. Terminal State Invariant: Trạng thái kết thúc không bao giờ bị lùi ngược
        if self.state["terminal_reached"]:
            return self.state

        # 4. Áp dụng biến đổi trạng thái
        if event_type == "TASK_START":
            self.state["status"] = "RUNNING"
        elif event_type == "ACTION_EXECUTED":
            self.state["applied_actions"].append(payload.get("action_id"))
            self.state["progress_percent"] = payload.get("progress", self.state["progress_percent"])
        elif event_type == "TASK_CANCEL":
            self.state["status"] = "CANCELLED"
            self.state["terminal_reached"] = True
        elif event_type == "TASK_COMPLETE":
            self.state["status"] = "COMPLETED"
            self.state["progress_percent"] = 100
            self.state["terminal_reached"] = True
        elif event_type == "TASK_FAIL":
            self.state["status"] = "FAILED"
            self.state["terminal_reached"] = True

        self.current_seq = seq_id
        self.state["version"] = seq_id
        self.event_log.append(copy.deepcopy(event))
        self.processed_event_ids.add(event_id)
        return self.state

    def rehydrate_from_checkpoint(self, checkpoint_seq: int, remaining_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phục hồi trạng thái từ checkpoint gần nhất + replay các sự kiện còn thiếu (Idempotent)."""
        if checkpoint_seq not in self.checkpoints:
            raise StateRehydrationError(f"CHECKPOINT_NOT_FOUND({checkpoint_seq})")

        checkpoint = self.checkpoints[checkpoint_seq]
        # Verify checkpoint hash
        computed_hash = hashlib.sha256(
            json.dumps(checkpoint["state_snapshot"], sort_keys=True).encode("utf-8")
        ).hexdigest()
        if computed_hash != checkpoint["checkpoint_hash"]:
            raise StateRehydrationError("CHECKPOINT_CORRUPTED_HASH_MISMATCH")

        # Khôi phục trạng thái
        self.state = copy.deepcopy(checkpoint["state_snapshot"])
        self.current_seq = checkpoint_seq

        # Replay sự kiện sau checkpoint
        for event in remaining_events:
            self.apply_event(event)

        return self.state

    def client_mutate(self, client_version: int, new_action: str) -> Dict[str, Any]:
        """Kiểm tra xung đột state từ stale client (Optimistic Concurrency Control)."""
        if client_version != self.state["version"]:
            raise StaleClientError(
                f"STALE_CLIENT_REJECTED(client_ver={client_version}, server_ver={self.state['version']})"
            )
        # Sinh event kế tiếp
        next_seq = self.current_seq + 1
        event = {
            "event_id": f"evt_{self.task_id}_{next_seq}",
            "seq_id": next_seq,
            "type": "ACTION_EXECUTED",
            "payload": {"action_id": new_action, "progress": 50}
        }
        return self.apply_event(event)


class TestP0StateRehydration(unittest.TestCase):
    """Bộ kiểm thử 9 tiêu chí bất biến của State Rehydration & Task Recovery."""

    def setUp(self):
        self.task_id = "task_visual_config_router_01"
        self.engine = RehydrationEngine(self.task_id)

    def test_01_monotonic_sequence_progression(self):
        """Tiêu chí 1: Chuỗi sự kiện tăng đơn điệu nghiêm ngặt."""
        evt1 = {"event_id": "e1", "seq_id": 1, "type": "TASK_START"}
        evt2 = {"event_id": "e2", "seq_id": 2, "type": "ACTION_EXECUTED", "payload": {"action_id": "click_ip_menu"}}
        self.engine.apply_event(evt1)
        self.engine.apply_event(evt2)
        self.assertEqual(self.engine.current_seq, 2)
        self.assertEqual(self.engine.state["status"], "RUNNING")
        self.assertEqual(self.engine.state["applied_actions"], ["click_ip_menu"])

    def test_02_atomic_checkpoint_creation_and_integrity(self):
        """Tiêu chí 2: Tạo checkpoint nguyên tử kèm băm SHA-256 xác thực."""
        self.engine.apply_event({"event_id": "e1", "seq_id": 1, "type": "TASK_START"})
        self.engine.apply_event({"event_id": "e2", "seq_id": 2, "type": "ACTION_EXECUTED", "payload": {"action_id": "open_tab"}})
        
        cp = self.engine.create_checkpoint()
        self.assertEqual(cp["seq_id"], 2)
        self.assertTrue(len(cp["checkpoint_hash"]) == 64)
        self.assertEqual(cp["state_snapshot"]["status"], "RUNNING")

    def test_03_idempotent_replay(self):
        """Tiêu chí 3: Replay cùng log sự kiện nhiều lần cho ra trạng thái giống hệt nhau."""
        events = [
            {"event_id": "e1", "seq_id": 1, "type": "TASK_START"},
            {"event_id": "e2", "seq_id": 2, "type": "ACTION_EXECUTED", "payload": {"action_id": "act_1"}},
            {"event_id": "e3", "seq_id": 3, "type": "ACTION_EXECUTED", "payload": {"action_id": "act_2"}},
        ]
        for e in events:
            self.engine.apply_event(e)
        state_first = copy.deepcopy(self.engine.state)

        # Replay lại trên một engine mới tinh
        new_engine = RehydrationEngine(self.task_id)
        for e in events:
            new_engine.apply_event(e)
        state_second = copy.deepcopy(new_engine.state)

        self.assertEqual(state_first, state_second)
        self.assertEqual(state_first["applied_actions"], ["act_1", "act_2"])

    def test_04_duplicate_event_safe_deduplication(self):
        """Tiêu chí 4: Xử lý an toàn các sự kiện trùng lặp (không áp dụng lần 2)."""
        evt1 = {"event_id": "e1", "seq_id": 1, "type": "TASK_START"}
        evt2 = {"event_id": "e2", "seq_id": 2, "type": "ACTION_EXECUTED", "payload": {"action_id": "add_ip_192"}}
        self.engine.apply_event(evt1)
        self.engine.apply_event(evt2)
        # Gửi lại evt2
        self.engine.apply_event(evt2)

        self.assertEqual(self.engine.current_seq, 2)
        # Không bị nhân đôi action
        self.assertEqual(self.engine.state["applied_actions"], ["add_ip_192"])

    def test_05_sequence_gap_detection(self):
        """Tiêu chí 5: Phát hiện lỗ hổng sự kiện (Sequence Gap) và từ chối áp dụng."""
        evt1 = {"event_id": "e1", "seq_id": 1, "type": "TASK_START"}
        evt_gap = {"event_id": "e4", "seq_id": 4, "type": "ACTION_EXECUTED", "payload": {"action_id": "act_jump"}}
        self.engine.apply_event(evt1)

        with self.assertRaises(SequenceGapError) as ctx:
            self.engine.apply_event(evt_gap)
        self.assertEqual(ctx.exception.expected_seq, 2)
        self.assertEqual(ctx.exception.received_seq, 4)

    def test_06_worker_restart_recovery_from_checkpoint(self):
        """Tiêu chí 6: Worker crash và khôi phục từ checkpoint + replay sự kiện còn thiếu."""
        self.engine.apply_event({"event_id": "e1", "seq_id": 1, "type": "TASK_START"})
        self.engine.apply_event({"event_id": "e2", "seq_id": 2, "type": "ACTION_EXECUTED", "payload": {"action_id": "nav_to_dns"}})
        self.engine.create_checkpoint()

        remaining_events = [
            {"event_id": "e3", "seq_id": 3, "type": "ACTION_EXECUTED", "payload": {"action_id": "set_dns_server"}},
            {"event_id": "e4", "seq_id": 4, "type": "TASK_COMPLETE"}
        ]

        # Khởi tạo worker mới sau crash và rehydrate
        recovered_worker = RehydrationEngine(self.task_id)
        recovered_worker.checkpoints = self.engine.checkpoints
        final_state = recovered_worker.rehydrate_from_checkpoint(2, remaining_events)

        self.assertEqual(final_state["status"], "COMPLETED")
        self.assertEqual(final_state["applied_actions"], ["nav_to_dns", "set_dns_server"])
        self.assertEqual(recovered_worker.current_seq, 4)

    def test_07_cancel_survives_reconnect(self):
        """Tiêu chí 7: Tác vụ đã CANCELLED luôn giữ nguyên sau khi kết nối lại, không hồi sinh."""
        self.engine.apply_event({"event_id": "e1", "seq_id": 1, "type": "TASK_START"})
        self.engine.apply_event({"event_id": "e2", "seq_id": 2, "type": "TASK_CANCEL"})
        self.assertEqual(self.engine.state["status"], "CANCELLED")

        # Thử gửi sự kiện tiếp theo
        self.engine.apply_event({"event_id": "e3", "seq_id": 3, "type": "ACTION_EXECUTED", "payload": {"action_id": "post_cancel"}})
        # Vẫn phải là CANCELLED
        self.assertEqual(self.engine.state["status"], "CANCELLED")
        self.assertNotIn("post_cancel", self.engine.state["applied_actions"])

    def test_08_terminal_state_cannot_regress(self):
        """Tiêu chí 8: Trạng thái kết thúc (COMPLETED) không bị lùi về RUNNING."""
        self.engine.apply_event({"event_id": "e1", "seq_id": 1, "type": "TASK_START"})
        self.engine.apply_event({"event_id": "e2", "seq_id": 2, "type": "TASK_COMPLETE"})
        self.assertEqual(self.engine.state["status"], "COMPLETED")

        # Cố gắng hồi sinh về RUNNING
        self.engine.apply_event({"event_id": "e3", "seq_id": 3, "type": "TASK_START"})
        self.assertEqual(self.engine.state["status"], "COMPLETED")

    def test_09_stale_client_mutation_rejected(self):
        """Tiêu chí 9: Client giữ state version cũ cố gắng ghi đè sẽ bị từ chối ngay lập tức."""
        self.engine.apply_event({"event_id": "e1", "seq_id": 1, "type": "TASK_START"})
        self.engine.apply_event({"event_id": "e2", "seq_id": 2, "type": "ACTION_EXECUTED", "payload": {"action_id": "act_v2"}})
        # Server đang ở version 2
        self.assertEqual(self.engine.state["version"], 2)

        # Client A có version 1 (do chưa F5 hoặc lag mạng) cố gắng thực thi
        with self.assertRaises(StaleClientError) as ctx:
            self.engine.client_mutate(client_version=1, new_action="stale_action")
        self.assertIn("STALE_CLIENT_REJECTED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
