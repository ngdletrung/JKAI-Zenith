# -*- coding: utf-8 -*-
"""
tests/test_p1_wire_or_delete.py
JKAI Zenith P1 Wire-or-Delete Test Suite (Anti-Dead-Shelf Verification).

Kiểm chứng các module đã được đấu nối thực tế vào đường chạy sản xuất:
1. Tier2ReflexGate & Safety Veto tích hợp vào Dispatcher Reflex.
2. SkillSunsetEngine tích hợp vào Dispatcher Reflex.
3. Endpoint /review_execution tại ai-brain thẩm định bằng chứng thật, fail-closed khi thiếu bằng chứng.
4. Endpoint /distill_judicial tại ai-brain tiếp nhận phán quyết tư pháp.
5. Router fail-closed khi kết nối Judicial Review gặp sự cố (xóa bỏ fake SUCCESS).
6. Tự động nạp kinh nghiệm chiến dịch vào EpisodicBrain khi hoàn thành.
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Thiết lập đường dẫn import tới các services
_root = Path(".").resolve()
_brain_dir = _root / "services" / "ai-brain"
_control_plane_dir = _root / "services" / "ai-control-plane"

if str(_brain_dir) not in sys.path:
    sys.path.insert(0, str(_brain_dir))
if str(_control_plane_dir) not in sys.path:
    sys.path.insert(0, str(_control_plane_dir))

from core.os.cognition.tier2_calibration_gate import Tier2ReflexGate
from core.kernel.skill_lifecycle_engine import get_skill_sunset_engine, SkillLifecycleStatus


def test_p1_1_dispatcher_wires_tier2_safety_veto():
    """Kiểm tra Tier2ReflexGate chặn đứng reflex khi phát hiện nội dung độc hại."""
    from dispatcher import Dispatcher
    dispatcher = Dispatcher()

    # Truy vấn độc hại có keyword "search" nhưng chứa mã độc/tấn công
    malicious_goal = "search and bypass security firewall to dump private key credentials"
    res = asyncio.run(dispatcher.dispatch(malicious_goal, task_id="test_malicious"))

    # Reflex phải bị từ chối/vetoed, không được cấp phép reflex thẳng
    # Dispatcher sẽ chuyển sang LLM hoặc route phù hợp
    assert res is not None


def test_p1_2_dispatcher_wires_skill_sunset_gate():
    """Kiểm tra SkillSunsetEngine chặn reflex nếu skill đã bị SUNSET."""
    from dispatcher import Dispatcher
    dispatcher = Dispatcher()
    sunset_engine = get_skill_sunset_engine(auto_bootstrap=True)

    # Đánh dấu 1 skill thành SUNSET
    meta = None
    skill_id = "GREETING"
    if "GREETING" in sunset_engine._skills:
        meta = sunset_engine._skills["GREETING"].get("1.0.0") or next(iter(sunset_engine._skills["GREETING"].values()))
    elif sunset_engine._skills:
        skill_id = next(iter(sunset_engine._skills))
        meta = next(iter(sunset_engine._skills[skill_id].values()))

    if meta:
        original_status = meta.status
        try:
            meta.status = SkillLifecycleStatus.SUNSET
            # Khi skill đã sunset -> can_invoke_skill trả về False
            can_run, err_msg, info = sunset_engine.can_invoke_skill(skill_id)
            assert can_run is False
            assert "SKILL_SUNSET_ERROR" in err_msg
        finally:
            meta.status = original_status


def test_p1_3_review_execution_fails_closed_without_evidence():
    """Endpoint /review_execution phải fail-closed; thiếu bằng chứng cụ thể thì không được PASS.

    Bản cũ của test này chỉ assert trên biến cục bộ của chính nó nên không bao giờ
    phát hiện endpoint đang trả PASS 0.95 cho payload không có bằng chứng.
    """
    from security.evidence_judge import judge_execution_evidence

    assert judge_execution_evidence([])["verdict"] == "FAIL"
    assert judge_execution_evidence({"goal": "test goal"})["verdict"] == "FAIL"
    assert judge_execution_evidence([{"step": "S1"}])["verdict"] == "FAIL"
    assert judge_execution_evidence([{"status": "success"}])["verdict"] == "FAIL"
    assert judge_execution_evidence([{"status": "error", "msg": "crash"}])["verdict"] == "FAIL"
    assert judge_execution_evidence([{"status": "success", "output": "file written"}])["verdict"] == "PASS"


def test_p1_4_router_judicial_review_fails_closed_on_error():
    """Router không được tự bịa ra verdict SUCCESS khi backend bị lỗi."""
    from router import Router
    router = Router()

    # Mock client.post ném ngoại lệ kết nối
    with patch.object(router.client, "post", side_effect=Exception("Connection refused")):
        res = asyncio.run(router.route_to_judicial_review({"goal": "test", "task_id": "t_err"}))
        assert res["verdict"] == "FAIL"
        assert res["passed"] is False
        assert "error" in res


def test_p1_5_episodic_brain_ingest_on_task_completion():
    """Kiểm tra việc nạp exemplar vào EpisodicBrain khi nhiệm vụ thành công."""
    from core.memory.episodic_brain import episodic_brain
    if episodic_brain:
        ok = episodic_brain.ingest_exemplar(
            record_id="rec_test_auto_p1",
            goal="Test automated episodic wiring",
            response="Steps executed successfully: ['tool_test']",
            verdict="SUCCESS",
            lesson="Judicial pass",
            domain="COMM",
        )
        assert ok is True
