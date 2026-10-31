# -*- coding: utf-8 -*-
"""
test_visual_aci_and_confirmation_gate.py
Harness kiểm định Cổng Phê duyệt Hành động (Action Confirmation Gate), Set-of-Marks (SoM),
và Phản tư Thị giác (Visual Diff Verification) cho Kỳ 2.
"""

import io
import sys
import time
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "ai-browser"))
from visual_aci_gateway import VisualACIGateway, ActionRiskLevel


class TestVisualACIAndConfirmationGate(unittest.TestCase):
    """Kiểm thử thực chứng toàn bộ các cơ chế an toàn của Visual ACI Gateway."""

    def setUp(self):
        self.task_id = "task_config_firewall_01"
        self.trace_id = "trace_abc123"
        self.state_hash = "sha256_mock_before_state_aaaa1111"

    def test_01_mutation_risk_classifier(self):
        """Kiểm tra phân loại rủi ro mutation chính xác."""
        # Mutation nguy hiểm -> HIGH
        risk, reasons = VisualACIGateway.evaluate_mutation_risk("click", element_name="Apply Changes", element_tag="button")
        self.assertEqual(risk, ActionRiskLevel.HIGH)
        self.assertTrue(any("apply" in r.lower() for r in reasons))

        risk, _ = VisualACIGateway.evaluate_mutation_risk("click", element_name="Reboot Device", element_tag="button")
        self.assertEqual(risk, ActionRiskLevel.HIGH)

        risk, _ = VisualACIGateway.evaluate_mutation_risk("click", element_name="Lưu cấu hình", element_tag="button")
        self.assertEqual(risk, ActionRiskLevel.HIGH)

        # Read-only
        risk, _ = VisualACIGateway.evaluate_mutation_risk("observe")
        self.assertEqual(risk, ActionRiskLevel.READ_ONLY)

        risk, _ = VisualACIGateway.evaluate_mutation_risk("screenshot")
        self.assertEqual(risk, ActionRiskLevel.READ_ONLY)

        # Click thông thường -> MEDIUM
        risk, _ = VisualACIGateway.evaluate_mutation_risk("click", element_name="Next Page", element_tag="a", element_role="link")
        self.assertEqual(risk, ActionRiskLevel.MEDIUM)

    def test_02_action_confirmation_card_generation(self):
        """Kiểm tra sinh thẻ xác nhận (Action Confirmation Card) đầy đủ thông tin."""
        card = VisualACIGateway.create_confirmation_card(
            task_id=self.task_id,
            trace_id=self.trace_id,
            action="click",
            target_ref="@e5",
            element_name="Apply Firewall Filter",
            element_rect={"x": 100, "y": 200, "width": 80, "height": 30},
            state_before_hash=self.state_hash,
            rollback_command="/ip firewall filter remove [find comment='test']",
            timeout_seconds=300
        )

        self.assertTrue(card["action_id"].startswith("act_"))
        self.assertEqual(card["mutation_risk"], ActionRiskLevel.HIGH)
        self.assertEqual(card["approval_status"], "PENDING_USER_APPROVAL")
        self.assertEqual(card["target_ref"], "@e5")
        self.assertEqual(card["state_before_hash"], self.state_hash)
        self.assertTrue(len(card["approval_token"]) == 64)

    def test_03_approval_token_verification_success(self):
        """Kiểm tra phê duyệt thành công khi token hợp lệ và trạng thái không trôi."""
        card = VisualACIGateway.create_confirmation_card(
            task_id=self.task_id,
            trace_id=self.trace_id,
            action="click",
            target_ref="@e5",
            element_name="Apply",
            element_rect={"x": 10, "y": 10, "width": 50, "height": 20},
            state_before_hash=self.state_hash,
        )

        ok, msg = VisualACIGateway.verify_action_execution(
            card=card,
            provided_token=card["approval_token"],
            current_state_hash=self.state_hash,
            current_action="click",
            current_target_ref="@e5",
            current_task_id=self.task_id,
            current_trace_id=self.trace_id,
            current_url=card.get("url", ""),
        )
        self.assertTrue(ok)
        self.assertEqual(msg, "APPROVAL_VERIFIED")

    def test_04_approval_token_tampered_or_invalid(self):
        """Kiểm tra từ chối khi token bị làm giả hoặc sai chữ ký."""
        card = VisualACIGateway.create_confirmation_card(
            task_id=self.task_id,
            trace_id=self.trace_id,
            action="click",
            target_ref="@e5",
            element_name="Apply",
            element_rect={"x": 10, "y": 10, "width": 50, "height": 20},
            state_before_hash=self.state_hash,
        )

        ok, msg = VisualACIGateway.verify_action_execution(
            card=card,
            provided_token="tampered_fake_token_" + "0" * 44,
            current_state_hash=self.state_hash,
            current_action="click",
            current_target_ref="@e5",
            current_task_id=self.task_id,
            current_trace_id=self.trace_id,
            current_url=card.get("url", ""),
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "INVALID_APPROVAL_SIGNATURE")

    def test_05_toctou_state_drift_detected(self):
        """Kiểm tra bảo vệ TOCTOU: Màn hình bị trôi/thay đổi trước khi thực thi click."""
        card = VisualACIGateway.create_confirmation_card(
            task_id=self.task_id,
            trace_id=self.trace_id,
            action="click",
            target_ref="@e5",
            element_name="Apply",
            element_rect={"x": 10, "y": 10, "width": 50, "height": 20},
            state_before_hash=self.state_hash,
        )

        drifted_hash = "sha256_different_state_bbbb2222"
        ok, msg = VisualACIGateway.verify_action_execution(
            card=card,
            provided_token=card["approval_token"],
            current_state_hash=drifted_hash,
            current_action="click",
            current_target_ref="@e5",
            current_task_id=self.task_id,
            current_trace_id=self.trace_id,
            current_url=card.get("url", ""),
        )
        self.assertFalse(ok)
        self.assertIn("TOCTOU_STATE_DRIFT", msg)

    def test_06_set_of_marks_overlay_rendering(self):
        """Kiểm tra phủ nhãn Set-of-Marks (SoM) lên ảnh chụp màn hình."""
        # Tạo ảnh trắng 200x200
        img = Image.new("RGB", (200, 200), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        elements = [
            {"rect": {"x": 20, "y": 20, "width": 60, "height": 30}},
            {"rect": {"x": 100, "y": 120, "width": 50, "height": 25}},
        ]

        som_bytes = VisualACIGateway.render_set_of_marks(raw_bytes, elements)
        self.assertTrue(len(som_bytes) > 0)
        self.assertNotEqual(som_bytes, raw_bytes)  # Đã có nhãn vẽ đè lên

        # Verify ảnh sau khi phủ nhãn đọc được hợp lệ
        som_img = Image.open(io.BytesIO(som_bytes))
        self.assertEqual(som_img.size, (200, 200))

    def test_07_visual_diff_verification(self):
        """Kiểm tra đo lường sai khác thị giác (Visual Diff)."""
        img1 = Image.new("RGB", (100, 100), color="white")
        buf1 = io.BytesIO()
        img1.save(buf1, format="PNG")
        bytes1 = buf1.getvalue()

        # So sánh ảnh giống hệt
        res_same = VisualACIGateway.compute_visual_diff(bytes1, bytes1)
        self.assertEqual(res_same["diff_percentage"], 0.0)
        self.assertFalse(res_same["state_changed"])

        # Tạo ảnh có ô vuông đen 30x30 (900 pixels / 10000 = 9%)
        img2 = Image.new("RGB", (100, 100), color="white")
        for x in range(30):
            for y in range(30):
                img2.putpixel((x, y), (0, 0, 0))
        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")
        bytes2 = buf2.getvalue()

        res_diff = VisualACIGateway.compute_visual_diff(bytes1, bytes2)
        self.assertEqual(res_diff["diff_percentage"], 9.0)
        self.assertTrue(res_diff["state_changed"])

    def test_08_verify_action_execution_rejects_missing_context(self):
        """Kiểm tra gọi trực tiếp verify_action_execution mà thiếu context fields (None/rỗng) => Bắt buộc REJECT."""
        card = VisualACIGateway.create_confirmation_card(
            task_id=self.task_id,
            trace_id=self.trace_id,
            action="click",
            target_ref="@e5",
            element_name="Apply",
            element_rect={"x": 10, "y": 10, "width": 50, "height": 20},
            state_before_hash=self.state_hash,
            url="http://localhost:9999/",
        )

        # Thiếu current_action
        ok, msg = VisualACIGateway.verify_action_execution(
            card=card,
            provided_token=card["approval_token"],
            current_state_hash=self.state_hash,
            current_action=None,  # Thiếu!
            current_target_ref="@e5",
            current_task_id=self.task_id,
            current_trace_id=self.trace_id,
            current_url="http://localhost:9999/",
        )
        self.assertFalse(ok)
        self.assertIn("CONTEXT_BINDING_REQUIRED_MISSING_FIELD(action)", msg)

        # Thiếu current_target_ref
        ok2, msg2 = VisualACIGateway.verify_action_execution(
            card=card,
            provided_token=card["approval_token"],
            current_state_hash=self.state_hash,
            current_action="click",
            current_target_ref="",  # Rỗng!
            current_task_id=self.task_id,
            current_trace_id=self.trace_id,
            current_url="http://localhost:9999/",
        )
        self.assertFalse(ok2)
        self.assertIn("CONTEXT_BINDING_REQUIRED_MISSING_FIELD(target_ref)", msg2)


if __name__ == "__main__":
    unittest.main()
