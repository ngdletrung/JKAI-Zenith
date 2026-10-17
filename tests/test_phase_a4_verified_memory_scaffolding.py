# -*- coding: utf-8 -*-
"""
tests/test_phase_a4_verified_memory_scaffolding.py
==================================================
Kiểm thử toàn diện Giai đoạn A4: External Cognitive Scaffolding & Verified Memory Architecture.
Đảm bảo tuân thủ Phương án 1 của Master Lee Trung & Tuyên ngôn JKAI-Zenith (Mục II.2, II.5, III.4, VII.4).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.os.cognition.adaptive_controller import (
    AdaptiveController,
    AdaptiveStrategy,
    CognitiveStateSnapshot,
)
from core.os.cognition.deep_schemas import CriterionStatus, MissionCriterion, MissionOutcomeStatus
from core.os.cognition.mission_completion_gate import MissionCompletionGate
from core.os.cognition.verified_memory_store import (
    DEFAULT_A4_REPORT_PATH,
    DEFAULT_A4_TRACES_PATH,
    DEFAULT_MEMORY_STORE_PATH,
    MemoryEntry,
    MemoryTier,
    VerifiedMemoryStore,
    build_canonical_seed_entries,
    ensure_canonical_memory_store,
    run_phase_a4_memory_benchmark,
)


class TestPhaseA4VerifiedMemoryScaffolding:
    """Bộ kiểm thử 6 điều kiện cốt lõi của Kiến trúc Bộ nhớ có kiểm chứng & Khung đỡ nhận thức (Phase A4)."""

    def test_condition_1_four_tier_memory_and_unverified_rejection(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "test_store.jsonl")

        # 1. Cấm nạp RAW_OBSERVATION
        raw_entry = MemoryEntry(
            memory_id="MEM_RAW_01",
            tier=MemoryTier.RAW_OBSERVATION.value,
            domain_group="GENERAL",
            applicable_strategies=["FAST_DIRECT"],
            topic_keywords=["log"],
            title="Quan sát thô chưa kiểm chứng",
            guidance_rule="Thử chạy lệnh bất kỳ",
            verified_example="ví dụ thô",
            source_provenance="RUNTIME_RAW_LOG",
            verification_proof={"completion_status": "COMPLETE", "evidence_count": 1},
        )
        ok, msg = store.ingest_entry(raw_entry)
        assert not ok
        assert "REJECTED_UNVERIFIED_TIER" in msg

        # 2. Cấm nạp HYPOTHESIS
        hyp_entry = MemoryEntry(
            memory_id="MEM_HYP_01",
            tier=MemoryTier.HYPOTHESIS.value,
            domain_group="GENERAL",
            applicable_strategies=["MULTI_STEP_PLANNING"],
            topic_keywords=["giả thuyết"],
            title="Giả thuyết xử lý lỗi",
            guidance_rule="Có thể do lỗi mạng",
            verified_example="ví dụ giả thuyết",
            source_provenance="PLANNER_HYPOTHESIS",
            verification_proof={"completion_status": "COMPLETE", "evidence_count": 1},
        )
        ok, msg = store.ingest_entry(hyp_entry)
        assert not ok
        assert "REJECTED_UNVERIFIED_TIER" in msg

        # 3. Cấm nạp VERIFIED_EXPERIENCE nhưng trạng thái INCOMPLETE hoặc thiếu bằng chứng
        inc_entry = MemoryEntry(
            memory_id="MEM_INC_01",
            tier=MemoryTier.VERIFIED_EXPERIENCE.value,
            domain_group="D_TOOL_AND_FILEOPS",
            applicable_strategies=["MULTI_STEP_PLANNING"],
            topic_keywords=["docker"],
            title="Bài học chưa hoàn tất",
            guidance_rule="Chạy lệnh kiểm tra container",
            verified_example="docker ps",
            source_provenance="MISSION_TRACE_101",
            verification_proof={"completion_status": "INCOMPLETE", "evidence_count": 1, "unresolved_criteria": 1},
        )
        ok, msg = store.ingest_entry(inc_entry)
        assert not ok
        assert "REJECTED_INCOMPLETE_PROOF" in msg

    def test_condition_2_two_door_exam_blocklist_and_ngram_leak_guard(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "test_leak.jsonl")

        # Cửa 1: Chặn ID/Source thuộc đề thi
        door1_entry = MemoryEntry(
            memory_id="MEM_LEAK_01",
            tier=MemoryTier.VERIFIED_EXPERIENCE.value,
            domain_group="A_MATH_FIDELITY",
            applicable_strategies=["FAST_DIRECT"],
            topic_keywords=["thùng hàng"],
            title="Bài học toán học hợp lệ",
            guidance_rule="Nhân số thùng với số kg mỗi thùng.",
            verified_example="10 thùng x 5 kg = 50 kg",
            source_provenance="B_m01_trace_harvest",
            verification_proof={"completion_status": "COMPLETE", "evidence_count": 1, "unresolved_criteria": 0},
        )
        ok, msg = store.ingest_entry(door1_entry)
        assert not ok
        assert "EXAM_BLOCKLIST_DOOR1_REJECTED" in msg

        # Cửa 2: Chặn trùng lặp 4-gram >= 0.40 với đề thi thật
        door2_entry = MemoryEntry(
            memory_id="MEM_LEAK_02",
            tier=MemoryTier.VERIFIED_EXPERIENCE.value,
            domain_group="A_MATH_FIDELITY",
            applicable_strategies=["FAST_DIRECT"],
            topic_keywords=["thùng hàng"],
            title="Tính tổng khối lượng 180 thùng hàng",
            guidance_rule="Tính tổng khối lượng 180 thùng hàng, mỗi thùng 15 kg bằng 2700 kg.",
            verified_example="Tính tổng khối lượng 180 thùng hàng, mỗi thùng 15 kg = 2700 kg",
            source_provenance="SAFE_PROVENANCE_NAME",
            verification_proof={"completion_status": "COMPLETE", "evidence_count": 1, "unresolved_criteria": 0},
        )
        ok, msg = store.ingest_entry(door2_entry)
        assert not ok
        assert "EXAM_NGRAM_DOOR2_REJECTED" in msg

        # Kiểm chứng toàn bộ 8 mẫu chuẩn trong canonical seed đều vượt qua cả 2 cửa an toàn
        for seed in build_canonical_seed_entries():
            ok_seed, msg_seed = store.ingest_entry(seed)
            assert ok_seed, f"Seed {seed.memory_id} failed anti-leak guard: {msg_seed}"

    def test_condition_3_deduplication_and_superseding_hygiene(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "test_dedup.jsonl")
        e1 = MemoryEntry(
            memory_id="MEM_DEDUP_01",
            tier=MemoryTier.VERIFIED_EXPERIENCE.value,
            domain_group="ERROR_RECOVERY",
            applicable_strategies=["ERROR_ADAPTIVE_RECOVERY"],
            topic_keywords=["sqlite", "locked"],
            title="Xử lý lỗi SQLite Database Locked khi ghi đồng thời",
            guidance_rule="Khi gặp lỗi database is locked trên SQLite, bật chế độ WAL và thử lại với backoff.",
            verified_example="PRAGMA journal_mode=WAL;",
            source_provenance="VERIFIED_TRACE_SQLITE_01",
            verification_proof={"completion_status": "COMPLETE", "evidence_count": 1, "unresolved_criteria": 0},
            confidence=0.90,
        )
        ok1, msg1 = store.ingest_entry(e1)
        assert ok1 and msg1 == "INGESTED_NEW_VERIFIED_ENTRY"

        # Nạp lại bản ghi y hệt với confidence cao hơn -> Tăng revision, không sinh bản ghi thừa
        e2 = MemoryEntry(
            memory_id="MEM_DEDUP_01_DUP",
            tier=MemoryTier.VERIFIED_EXPERIENCE.value,
            domain_group="ERROR_RECOVERY",
            applicable_strategies=["ERROR_ADAPTIVE_RECOVERY"],
            topic_keywords=["sqlite", "locked"],
            title="Xử lý lỗi SQLite Database Locked khi ghi đồng thời",
            guidance_rule="Khi gặp lỗi database is locked trên SQLite, bật chế độ WAL và thử lại với backoff.",
            verified_example="PRAGMA journal_mode=WAL;",
            source_provenance="VERIFIED_TRACE_SQLITE_02",
            verification_proof={"completion_status": "COMPLETE", "evidence_count": 2, "unresolved_criteria": 0},
            confidence=0.95,
        )
        ok2, msg2 = store.ingest_entry(e2)
        assert ok2 and "DEDUPLICATED_UPDATED_REVISION_2" in msg2
        assert store.stats()["active_records"] == 1

    def test_condition_4_purposeful_retrieval_and_expiration_filtering(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "test_retrieve.jsonl")
        for seed in build_canonical_seed_entries():
            store.ingest_entry(seed)

        # Thêm 1 bản ghi đã hết hạn (expired)
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        expired_entry = MemoryEntry(
            memory_id="MEM_EXPIRED_99",
            tier=MemoryTier.ACCEPTED_KNOWLEDGE.value,
            domain_group="C_RETRIEVAL_CITATION",
            applicable_strategies=["FAST_DIRECT"],
            topic_keywords=["sovereign", "mission", "control", "port"],
            title="Thông tin cổng cũ đã hết hạn",
            guidance_rule="Cổng cũ là 8080",
            verified_example="port 8080",
            source_provenance="OLD_SPEC_V1",
            verification_proof={"approved_by": "MASTER"},
            expires_at=past,
        )
        store._entries.append(expired_entry)

        hits = store.retrieve_for_task(
            prompt="Port mặc định của Sovereign Mission Control là bao nhiêu?",
            domain_group="C_RETRIEVAL_CITATION",
            strategy="FAST_DIRECT",
            top_k=2,
        )
        hit_ids = [h.memory_id for h in hits]
        assert "MEM_DOC_002" in hit_ids
        assert "MEM_EXPIRED_99" not in hit_ids

    def test_condition_5_adaptive_controller_and_completion_gate_closed_loop(self, tmp_path: Path):
        store = VerifiedMemoryStore(store_path=tmp_path / "test_loop.jsonl")
        for seed in build_canonical_seed_entries():
            store.ingest_entry(seed)

        controller = AdaptiveController()
        state = CognitiveStateSnapshot(
            mission_id="mission_closed_loop_01",
            prompt="Cấu hình mạng giúp tôi (yêu cầu thiếu thông tin).",
            missing_information_keys=["target_device", "ip_subnet"],
        )
        decision = controller.decide_strategy_with_memory(
            state=state,
            memory_store=store,
            domain_group="E_MASTER_COMMUNICATION",
        )
        assert decision.selected_strategy == AdaptiveStrategy.ASK_USER_CLARIFICATION
        assert "MEM_COMM_001" in decision.retrieved_memory_ids
        assert "[TRI THỨC & KINH NGHIỆM ĐÃ XÁC MINH TỪ JKAI MEMORY]" in decision.grounded_scaffolding_prompt

        # Xác nhận hoàn thành qua MissionCompletionGate -> Cho phép nạp bài học mới vào Memory
        outcome = MissionCompletionGate.evaluate(
            mission_id="mission_closed_loop_01",
            criteria=[MissionCriterion(criterion_id="c1", description="Ask clarifying question", status=CriterionStatus.VERIFIED)],
            verification_context_hash="ctx_hash_verified_01",
            evidence_count=1,
        )
        assert outcome.status == MissionOutcomeStatus.COMPLETE

        new_lesson = MemoryEntry(
            memory_id="MEM_NEW_LESSON_01",
            tier=MemoryTier.VERIFIED_EXPERIENCE.value,
            domain_group="E_MASTER_COMMUNICATION",
            applicable_strategies=["ASK_USER_CLARIFICATION"],
            topic_keywords=["firewall", "thiếu dải mạng"],
            title="Hỏi rõ dải mạng CIDR khi yêu cầu cấu hình tường lửa thiếu thông số",
            guidance_rule="Khi Master yêu cầu mở port tường lửa nhưng thiếu nguồn IP, luôn hỏi rõ dải CIDR nguồn.",
            verified_example="Xin Master cho biết dải IP CIDR nguồn cần mở quyền truy cập?",
            source_provenance="VERIFIED_RUNTIME_MISSION_01",
            verification_proof={
                "completion_status": outcome.status.value,
                "evidence_count": outcome.evidence_count,
                "unresolved_criteria": outcome.success_criteria_unresolved,
            },
        )
        ok, msg = store.ingest_entry(new_lesson)
        assert ok and msg == "INGESTED_NEW_VERIFIED_ENTRY"

    def test_condition_6_disk_artifacts_and_raw_trace_parity(self):
        ensure_canonical_memory_store(DEFAULT_MEMORY_STORE_PATH)
        assert DEFAULT_MEMORY_STORE_PATH.exists()

        report = run_phase_a4_memory_benchmark(live_ollama=False)
        assert DEFAULT_A4_TRACES_PATH.exists()
        assert DEFAULT_A4_REPORT_PATH.exists()

        # Kiểm tra khớp tuyệt đối SHA-256 và byte_size của cả Memory Store và Raw Inference Traces
        raw_trace_bytes = DEFAULT_A4_TRACES_PATH.read_bytes()
        assert b"\r\n" not in raw_trace_bytes, "Raw traces file must use pure LF line endings"
        actual_trace_sha = hashlib.sha256(raw_trace_bytes).hexdigest()
        actual_trace_size = len(raw_trace_bytes)

        assert report["raw_inference_traces"]["sha256"] == actual_trace_sha
        assert report["raw_inference_traces"]["byte_size"] == actual_trace_size

        raw_store_bytes = DEFAULT_MEMORY_STORE_PATH.read_bytes()
        assert b"\r\n" not in raw_store_bytes, "Memory store file must use pure LF line endings"
        actual_store_sha = hashlib.sha256(raw_store_bytes).hexdigest()
        assert report["verified_memory_store"]["sha256"] == actual_store_sha
        assert report["verified_memory_store"]["byte_size"] == len(raw_store_bytes)

        # Kiểm tra số lượng bản ghi và kết quả cải thiện thực nghiệm
        lines = [json.loads(line) for line in raw_trace_bytes.decode("utf-8").splitlines() if line.strip()]
        assert len(lines) == 20
        actual_passes = sum(1 for r in lines if r.get("passed") is True)
        assert report["raw_inference_traces"]["passed_tasks"] == actual_passes

        a4_metrics = report["progression_comparison"]["phase_a4_scaffolding_plus_verified_memory"]
        assert a4_metrics["passed_tasks"] == actual_passes
        assert a4_metrics["live_tcr"] > 0.55, f"Expected Phase A4 Live TCR > 0.55 (Phase A3), got {a4_metrics['live_tcr']}"
        assert a4_metrics["safety_violations"] == 0
        assert report["hardware_verification"]["within_hardware_limits"] is True
