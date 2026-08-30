# -*- coding: utf-8 -*-
"""
Unit test suite cho 4 Khối Kiến Trúc Nhận Thức Toàn Diện Mới:
1. Recursive Intent Feedback
2. World Graph Real-time Synchronizer (v2.0 Live Docker)
3. Artifact Packaging & Delivery (v2.0 TTL Janitor)
4. Self-Reflection & Continuous Improvement
"""

import os
import time
import pytest
from core.os.routing.feedback_learner import feedback_learner
from core.knowledge_sources.world_sync import world_sync
from core.kernel.artifact_packager import artifact_packager
from core.kernel.self_reflection import self_reflection


class TestHolisticPillars:
    """Kiểm tra toàn diện các khối kiến trúc chiến lược mới."""

    def test_recursive_intent_feedback(self):
        corr = feedback_learner.record_correction(
            goal="báo cáo tài chính doanh nghiệp quý 3",
            original_intent="CHAT",
            corrected_intent="OFFICE",
            corrected_tags=["OFFICE", "ANALYSIS"]
        )
        assert corr.corrected_intent == "OFFICE"
        assert feedback_learner.get_corrections_count() > 0

    def test_world_graph_sync_and_live_discovery(self):
        snapshot = world_sync.sync_hardware_state()
        assert snapshot.vram_free_mb > 0
        assert snapshot.ram_free_gb > 0
        assert len(snapshot.active_containers) >= 4
        assert "ai-brain" in snapshot.active_containers

    def test_artifact_packager_manifest_and_zip(self, tmp_path):
        f1 = tmp_path / "report1.xlsx"
        f1.write_text("dummy xlsx content", encoding="utf-8")
        f2 = tmp_path / "summary.docx"
        f2.write_text("dummy docx content", encoding="utf-8")

        pkg_out_dir = tmp_path / "pkg_out"
        pkg = artifact_packager.package_artifacts(
            task_id="task_test_delivery",
            artifact_paths=[str(f1), str(f2)],
            output_base_dir=str(pkg_out_dir)
        )

        assert os.path.exists(pkg.manifest_path)
        assert pkg.zip_path is not None
        assert os.path.exists(pkg.zip_path)
        assert len(pkg.file_checksums) == 2

    def test_artifact_packager_ttl_janitor_cleanup(self, tmp_path):
        # Tạo 1 package giả lập cũ hơn 8 ngày
        old_pkg_dir = tmp_path / "pkg_old_123"
        old_pkg_dir.mkdir()
        manifest_file = old_pkg_dir / "manifest.json"
        
        eight_days_ago = time.time() - (8 * 86400.0)
        import json
        manifest_file.write_text(json.dumps({"package_id": "pkg_old_123", "created_at": eight_days_ago}), encoding="utf-8")

        # Chạy TTL Janitor với ngưỡng 7 ngày
        cleaned = artifact_packager.cleanup_expired_packages(max_age_days=7.0, target_dir=str(tmp_path))
        assert cleaned == 1
        assert not os.path.exists(str(old_pkg_dir))

    def test_self_reflection_scoring_and_tuner(self):
        # 1. Output tốt
        rep_good = self_reflection.reflect_on_output(
            task_id="task_reflect_01",
            goal="Tạo bảng lương tháng 8",
            answer="Bảng lương đã được hoàn tất thành công.\n\n📁 **Tệp tin đã tạo:** `workspace/outputs/bang_luong.xlsx`",
            has_artifacts=True
        )
        assert rep_good.overall_quality >= 0.85

        # 2. Output chứa placeholder lỗi
        rep_bad = self_reflection.reflect_on_output(
            task_id="task_reflect_02",
            goal="Phân tích thị trường",
            answer="[PLACEHOLDER] Chưa có nội dung chi tiết.",
            has_artifacts=False
        )
        assert rep_bad.overall_quality < 0.80
        assert rep_bad.lowest_dimension in {"accuracy", "completeness"}
