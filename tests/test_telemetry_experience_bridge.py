# -*- coding: utf-8 -*-
"""
tests/test_telemetry_experience_bridge.py
Kiểm tra vòng lặp tự học từ nhãn của Master vào ExperienceStore.
"""

from core.memory.experience_store import ExperienceStore
from core.memory.telemetry_experience_bridge import (
    TelemetryExperienceBridge,
    compute_error_fingerprint,
    telemetry_bridge
)


class TestTelemetryExperienceBridge:
    def setup_method(self):
        ExperienceStore.clear()
        TelemetryExperienceBridge._imported_records.clear()

    def test_01_compute_error_fingerprint_normalization(self):
        query1 = "Hôm nay là thứ mấy vậy JKAI?"
        query2 = "Hôm nay là thứ mấy?"
        fp1 = compute_error_fingerprint(query1)
        fp2 = compute_error_fingerprint(query2)
        # Cả 2 đều trích xuất ra các từ khóa cốt lõi "hôm_nay_thứ_mấy"
        assert "hôm" in fp1 and "thứ" in fp1
        assert "hôm" in fp2 and "thứ" in fp2

    def test_02_ingest_wrong_record_stores_negative_lesson(self):
        record = {
            "record_id": "web_test_001",
            "task_id": "task_abc",
            "score": 0.0,
            "verdict": "COMPLETELY_WRONG",
            "msg_preview": "Theo nghiên cứu mới nhất hôm nay là Thứ Hai.",
            "notes": "Hôm nay là Chủ Nhật, model bịa đặt."
        }
        telemetry_bridge.ingest_record(record)
        assert ExperienceStore.count() == 1

        fp = compute_error_fingerprint(record["msg_preview"])
        lessons = ExperienceStore.get_negative_lessons(fp)
        assert len(lessons) == 1
        assert "COMPLETELY_WRONG" in lessons[0]
        assert "Hôm nay là Chủ Nhật" in lessons[0]

    def test_03_ingest_partially_correct_stores_warning(self):
        record = {
            "record_id": "web_test_002",
            "task_id": "task_xyz",
            "score": 0.5,
            "verdict": "PARTIALLY_CORRECT",
            "msg_preview": "Hôm nay Chủ Nhật.",
            "notes": "Thiếu câu chào lịch sự và bước tiếp theo."
        }
        telemetry_bridge.ingest_record(record)
        assert ExperienceStore.count() == 1

        fp = compute_error_fingerprint(record["msg_preview"])
        lessons = ExperienceStore.get_negative_lessons(fp)
        assert len(lessons) == 1
        assert "PARTIALLY_CORRECT" in lessons[0]

    def test_04_correct_answer_not_stored_as_negative_lesson(self):
        # Master chấm 1.0 (Đúng) -> không coi là negative lesson
        record = {
            "record_id": "web_test_003",
            "task_id": "task_ok",
            "score": 1.0,
            "verdict": "CORRECT",
            "msg_preview": "Chào Master, hôm nay là Chủ nhật."
        }
        # Nếu chạy qua sync logic sẽ bị bỏ qua không lưu vào negative lessons
        fp = compute_error_fingerprint(record["msg_preview"])
        lessons = ExperienceStore.get_negative_lessons(fp)
        assert len(lessons) == 0
