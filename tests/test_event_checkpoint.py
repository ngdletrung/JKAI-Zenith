# -*- coding: utf-8 -*-
"""
tests/test_event_checkpoint.py
===============================
Kiểm thử chuyên biệt cho Trọng điểm 3: Microkernel Event Stream & Step Checkpointing (Học hỏi OpenHands / LangGraph):
1. Tạo Checkpoint trạng thái bất biến sau mỗi bước DAG.
2. Phát xạ sự kiện OBSERVATION_RECORDED và STEP_CHECKPOINT_COMMITTED vào CognitiveEventStore.
3. Cơ chế tìm kiếm Checkpoint tốt nhất gần nhất (Best Valid Checkpoint selection).
4. Khôi phục và quay lui ngữ cảnh (Time-Travel Backtracking).
5. Bảo tồn dữ kiện đã xác minh (Verified Facts retention) khi Critic kích hoạt Re-plan.
"""

import pytest

from core.os.cognition.event_checkpoint import CheckpointStore, StepCheckpoint
from core.os.cognition.event_model import event_store


def test_create_checkpoint_records_event_and_facts():
    store = CheckpointStore()
    mission_id = "test_mission_cp_01"
    trace_id = "trace_cp_01"

    evidence = {
        "status": "success",
        "results": [
            {
                "title": "Báo cáo VN-Index",
                "url": "https://vietstock.vn/vnindex-tang.htm",
                "snippet": "VN-Index tăng 15 điểm đạt mốc 1300 với khối lượng 68 triệu đơn vị.",
            }
        ],
        "output": "[1] Báo cáo VN-Index: Thanh khoản 50.5 nghìn tỷ",
    }

    cp = store.create_checkpoint(
        mission_id=mission_id,
        step_id="step_search_stocks",
        step_index=1,
        status="SUCCESS",
        evidence=evidence,
        action_name="SEARCH_WEB_GLOBAL",
        trace_id=trace_id,
    )

    assert cp.checkpoint_id.startswith(f"cp_{mission_id}_1_")
    assert cp.status == "SUCCESS"
    assert len(cp.verified_facts) >= 1
    assert "VN-Index" in cp.verified_facts[0]

    # Kiểm tra sự kiện lưu trong event_store
    events = event_store.get_events_for_aggregate(mission_id)
    assert any(e.event_type == "OBSERVATION_RECORDED" for e in events)
    assert any(e.event_type == "STEP_CHECKPOINT_COMMITTED" for e in events)


def test_get_best_checkpoint_prioritizes_success_and_facts():
    store = CheckpointStore()
    m_id = "test_mission_cp_best"

    # Step 1: Lỗi (ERROR)
    store.create_checkpoint(
        mission_id=m_id,
        step_id="step_1",
        step_index=1,
        status="ERROR",
        evidence={"status": "error", "msg": "Network timeout"},
    )

    # Step 2: Thành công có 2 facts (SUCCESS)
    store.create_checkpoint(
        mission_id=m_id,
        step_id="step_2",
        step_index=2,
        status="SUCCESS",
        evidence={"output": "[1] Fact A\n[2] Fact B"},
    )

    # Step 3: Thành công một phần có 1 fact (PARTIAL)
    store.create_checkpoint(
        mission_id=m_id,
        step_id="step_3",
        step_index=3,
        status="PARTIAL",
        evidence={"output": "[1] Fact C"},
    )

    best = store.get_best_checkpoint(m_id)
    assert best is not None
    assert best.step_id == "step_2"
    assert best.status == "SUCCESS"


def test_time_travel_backtracking_consolidates_facts():
    store = CheckpointStore()
    m_id = "test_mission_backtrack"
    trace_id = "trace_bt_01"

    store.create_checkpoint(
        mission_id=m_id,
        step_id="step_01",
        step_index=1,
        status="SUCCESS",
        evidence={"output": "[1] Dữ liệu VN-Index tăng 12 điểm"},
        trace_id=trace_id,
    )

    store.create_checkpoint(
        mission_id=m_id,
        step_id="step_02",
        step_index=2,
        status="SUCCESS",
        evidence={"output": "[2] Khối ngoại mua ròng 1500 tỷ"},
        trace_id=trace_id,
    )

    best_cp, cons_evidence, facts = store.backtrack_to_best_checkpoint(m_id, trace_id=trace_id)
    assert best_cp is not None
    assert len(facts) >= 2
    assert any("VN-Index" in f for f in facts)
    assert any("Khối ngoại" in f for f in facts)

    # Thẩm tra sự kiện CONTEXT_BACKTRACKED
    events = event_store.get_events_for_aggregate(m_id)
    assert any(e.event_type == "CONTEXT_BACKTRACKED" for e in events)
