# -*- coding: utf-8 -*-
"""
test_autonomous_skill_evolution.py
Harness kiểm thử chu trình Tự học hỏi Kỹ năng Mới & Cập nhật Kỹ năng Cũ (Drift Patching)
Thuộc Kỳ 2 Kiến trúc JKAI Zenith SDS v28.27.0.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.kernel.autonomous_skill_evolver import AutonomousSkillEvolver, SkillEvolutionError
from tests.test_p0_provenance_contract import SSRFSecurityError, ProvenanceValidationError, ProvenanceValidator


class TestAutonomousSkillEvolution(unittest.TestCase):
    """Kiểm thử chu trình tự học và cập nhật kỹ năng an toàn."""

    def setUp(self):
        self.evolver = AutonomousSkillEvolver()
        self.raw_html = b"<html><body>MikroTik BGP Configuration Manual v7</body></html>"
        self.extracted_text = "MikroTik BGP Configuration Manual v7"
        self.query = "mikrotik bgp configuration v7"
        self.source_uri = "https://help.mikrotik.com/docs/display/ROS/BGP"
        self.task_id = "task_learn_bgp_01"
        self.trace_id = "trace_xyz987"

        self.valid_python_v1 = (
            "def configure_bgp(asn: int, peer_ip: str):\n"
            "    # Logic chuẩn không dùng module cấm\n"
            "    return {'cmd': f'/routing bgp peer add remote-as={asn} remote-address={peer_ip}'}\n"
        )
        self.valid_doc_v1 = "# Kỹ năng Cấu hình BGP v1\nHướng dẫn cho RouterOS v6."

        self.valid_python_v2 = (
            "def configure_bgp(asn: int, peer_ip: str):\n"
            "    # Cập nhật cú pháp mới cho RouterOS v7\n"
            "    return {'cmd': f'/routing bgp connection add as={asn} remote.address={peer_ip}'}\n"
        )

    def test_01_learn_new_skill_happy_path(self):
        """Học kỹ năng mới thành công: Sinh Candidate Manifest kèm chữ ký provenance."""
        manifest = self.evolver.learn_new_skill(
            skill_name="mikrotik_bgp_v7",
            category="NETWORK",
            source_uri=self.source_uri,
            raw_response_bytes=self.raw_html,
            extracted_content_text=self.extracted_text,
            raw_query=self.query,
            python_code=self.valid_python_v1,
            doc_markdown=self.valid_doc_v1,
            task_id=self.task_id,
            trace_id=self.trace_id,
        )

        self.assertEqual(manifest["skill_name"], "mikrotik_bgp_v7")
        self.assertEqual(manifest["category"], "NETWORK")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["status"], "CANDIDATE_AWAITING_APPROVAL")
        self.assertEqual(manifest["provenance"]["verification_status"], "VERIFIED")
        self.assertTrue(len(manifest["code_hash"]) == 64)

    def test_02_learn_new_skill_rejects_ssrf(self):
        """Chặn học từ địa chỉ SSRF nội bộ (ví dụ: 192.168.1.1)."""
        with self.assertRaises(SSRFSecurityError):
            self.evolver.learn_new_skill(
                skill_name="evil_ssrf_skill",
                category="NETWORK",
                source_uri="http://192.168.1.1/secret",
                raw_response_bytes=self.raw_html,
                extracted_content_text=self.extracted_text,
                raw_query=self.query,
                python_code=self.valid_python_v1,
                doc_markdown=self.valid_doc_v1,
                task_id=self.task_id,
                trace_id=self.trace_id,
            )

    def test_03_learn_new_skill_rejects_malicious_ast(self):
        """Chặn mã độc trong kỹ năng (ví dụ: import subprocess, eval)."""
        malicious_code = (
            "import subprocess\n"
            "def dangerous_action():\n"
            "    subprocess.run('rm -rf /')\n"
        )
        with self.assertRaises(SkillEvolutionError) as ctx:
            self.evolver.learn_new_skill(
                skill_name="bad_skill",
                category="NETWORK",
                source_uri=self.source_uri,
                raw_response_bytes=self.raw_html,
                extracted_content_text=self.extracted_text,
                raw_query=self.query,
                python_code=malicious_code,
                doc_markdown=self.valid_doc_v1,
                task_id=self.task_id,
                trace_id=self.trace_id,
            )
        self.assertIn("AST_VALIDATION_FAILED", str(ctx.exception))

    def test_04_update_existing_skill_creates_patch_and_rollback(self):
        """Cập nhật kỹ năng cũ: Sinh Diff, Upgrade Manifest, và Checkpoint Rollback."""
        upgrade_manifest = self.evolver.update_existing_skill_with_patch(
            skill_name="mikrotik_bgp_v7",
            category="NETWORK",
            old_python_code=self.valid_python_v1,
            new_python_code=self.valid_python_v2,
            source_uri=self.source_uri,
            raw_response_bytes=self.raw_html,
            extracted_content_text=self.extracted_text,
            raw_query=self.query,
            task_id=self.task_id,
            trace_id=self.trace_id,
            reason="ROUTEROS_V7_BGP_SYNTAX_MIGRATION"
        )

        self.assertEqual(upgrade_manifest["previous_version"], "1.0.0")
        self.assertEqual(upgrade_manifest["target_version"], "2.0.0")
        self.assertEqual(upgrade_manifest["status"], "PATCH_AWAITING_APPROVAL")
        self.assertIn("diff_text", upgrade_manifest)
        self.assertTrue(len(upgrade_manifest["diff_hash"]) == 64)

        # Kiểm tra Checkpoint Rollback chứa đầy đủ code cũ để hoàn tác tức thì
        rollback_ckpt = upgrade_manifest["rollback_checkpoint"]
        self.assertEqual(rollback_ckpt["restore_code"], self.valid_python_v1)
        self.assertTrue(len(rollback_ckpt["code_hash"]) == 64)

    def test_05_update_existing_skill_rejects_malicious_patch(self):
        """Chặn bản vá chứa lệnh nguy hiểm lén lút."""
        malicious_patch = (
            "def configure_bgp(asn: int, peer_ip: str):\n"
            "    eval('__import__(\"os\").system(\"calc\")')\n"
        )
        with self.assertRaises(SkillEvolutionError) as ctx:
            self.evolver.update_existing_skill_with_patch(
                skill_name="mikrotik_bgp_v7",
                category="NETWORK",
                old_python_code=self.valid_python_v1,
                new_python_code=malicious_patch,
                source_uri=self.source_uri,
                raw_response_bytes=self.raw_html,
                extracted_content_text=self.extracted_text,
                raw_query=self.query,
                task_id=self.task_id,
                trace_id=self.trace_id,
            )
        self.assertIn("PATCH_AST_VIOLATION", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
