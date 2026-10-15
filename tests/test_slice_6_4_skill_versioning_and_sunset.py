# -*- coding: utf-8 -*-
"""
tests/test_slice_6_4_skill_versioning_and_sunset.py
Kiểm thử toàn diện Slice 6.4: Skill Versioning, Regression Test Harness & Sunset Lifecycle.
Hiện thực hóa Bước 4 trong Lộ trình 1 Quý của Master:
"Skill versioning + regression: mỗi skill có version, test hồi quy, sunset khi cũ.
 Kẻo skill cũ thành sự thật cũ."

Khóa chặt 5 điều kiện kiểm thử:
1. Điều kiện 1: Hợp đồng phiên bản kỹ năng (SemVer, TTL 90 ngày, kiểm tra quá hạn is_expired).
2. Điều kiện 2: Khung hồi quy chặn đứng nâng cấp khi chưa có bài thi hồi quy (Zero-test block).
3. Điều kiện 3: Khung hồi quy phát hiện lỗi suy giảm (regression) và chặn đứng nâng cấp (Fail-closed).
4. Điều kiện 4: Nâng cấp thành công (100% pass) thăng hạng phiên bản mới và chuyển phiên bản cũ sang DEPRECATED.
5. Điều kiện 5: Động cơ Sunset tự động hạ sát kỹ năng quá hạn thành SUNSET, chặn thực thi trực tiếp và ghi sổ cái băm chuỗi.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from core.kernel.skill_lifecycle_engine import (
    SkillLifecycleStatus,
    SkillVersionMeta,
    SkillRegressionCase,
    SkillRegressionHarness,
    SkillSunsetEngine,
)


def test_condition_1_skill_versioning_metadata_and_expiry():
    """Điều kiện 1: Kiểm tra siêu dữ liệu SemVer và logic phát hiện quá hạn."""
    now = datetime.now(timezone.utc)

    # 1. Kỹ năng mới tạo -> Không quá hạn
    fresh_meta = SkillVersionMeta(
        skill_id="SYSTEM_CORE_EXECUTOR",
        version="1.0.0",
        created_at=now.isoformat(),
        max_supported_days=90,
    )
    assert fresh_meta.is_expired(now) is False

    # 2. Kỹ năng tạo cách đây 95 ngày -> Quá hạn TTL
    old_time = now - timedelta(days=95)
    expired_meta = SkillVersionMeta(
        skill_id="SYSTEM_CORE_EXECUTOR",
        version="0.9.0",
        created_at=old_time.isoformat(),
        max_supported_days=90,
    )
    assert expired_meta.is_expired(now) is True

    # 3. Kỹ năng có ngày sunset_at cụ thể trong quá khứ -> Quá hạn
    sunset_past = now - timedelta(days=1)
    sunset_meta = SkillVersionMeta(
        skill_id="LEGACY_TELNET_TOOL",
        version="1.0.0",
        created_at=now.isoformat(),
        sunset_at=sunset_past.isoformat(),
    )
    assert sunset_meta.is_expired(now) is True


def test_condition_2_regression_harness_blocks_untested_upgrades(tmp_path):
    """Điều kiện 2: Chặn đứng mọi hành vi nâng cấp tự động khi chưa có bài thi hồi quy."""
    ledger_file = tmp_path / "skill_ledger.jsonl"
    engine = SkillSunsetEngine(ledger_path=ledger_file)

    meta_v1 = SkillVersionMeta(skill_id="NETWORK_PROBER", version="1.0.0")
    engine.register_skill_version(meta_v1)

    # Đề xuất nâng cấp v2.0.0 nhưng chưa đăng ký bài test hồi quy nào
    meta_v2 = SkillVersionMeta(skill_id="NETWORK_PROBER", version="2.0.0")
    ok, reason = engine.upgrade_skill_version(
        new_meta=meta_v2,
        skill_runner=lambda args: {"status": "ok"},
        predicates={},
    )

    assert ok is False
    assert "ZERO_REGRESSION_TESTS_REGISTERED" in reason
    # Phiên bản hiện hành vẫn phải là v1.0.0
    assert engine._latest_versions["NETWORK_PROBER"] == "1.0.0"


def test_condition_3_regression_harness_catches_regression_and_blocks_update(tmp_path):
    """Điều kiện 3: Khi có bài test bị rớt (pass rate < 1.0) -> Chặn nâng cấp ngay lập tức."""
    ledger_file = tmp_path / "skill_ledger.jsonl"
    engine = SkillSunsetEngine(ledger_path=ledger_file)

    skill_id = "SQL_QUERY_GENERATOR"
    meta_v1 = SkillVersionMeta(skill_id=skill_id, version="1.0.0")
    engine.register_skill_version(meta_v1)

    # Đăng ký 2 bài thi hồi quy
    cases = [
        SkillRegressionCase(
            case_id="case_select",
            input_args={"table": "users", "fields": ["id", "name"]},
            expected_predicate="pred_valid_select",
            description="Kiểm tra câu lệnh SELECT cơ bản",
        ),
        SkillRegressionCase(
            case_id="case_limit",
            input_args={"table": "logs", "limit": 10},
            expected_predicate="pred_has_limit",
            description="Kiểm tra mệnh đề LIMIT",
        ),
    ]
    engine.regression_harness.register_cases(skill_id, cases)

    predicates = {
        "pred_valid_select": lambda r: "SELECT" in r.get("sql", ""),
        "pred_has_limit": lambda r: "LIMIT 10" in r.get("sql", ""),
    }

    # Giả lập runner mới bị lỗi: quên hỗ trợ tham số limit (gây regression)
    def broken_candidate_runner(args):
        if "fields" in args:
            return {"sql": "SELECT id, name FROM users"}
        # Quên mệnh đề LIMIT -> Trượt test case 2
        return {"sql": "SELECT * FROM logs"}

    meta_v2 = SkillVersionMeta(skill_id=skill_id, version="1.1.0")
    ok, reason = engine.upgrade_skill_version(
        new_meta=meta_v2,
        skill_runner=broken_candidate_runner,
        predicates=predicates,
    )

    assert ok is False
    assert "REGRESSION_DETECTED" in reason
    assert engine._latest_versions[skill_id] == "1.0.0"
    assert engine._skills[skill_id]["1.0.0"].status == SkillLifecycleStatus.ACTIVE


def test_condition_4_successful_upgrade_deprecates_older_version(tmp_path):
    """Điều kiện 4: Nâng cấp thành công (100% pass) thăng hạng v2 và hạ cấp v1 sang DEPRECATED."""
    ledger_file = tmp_path / "skill_ledger.jsonl"
    engine = SkillSunsetEngine(ledger_path=ledger_file)

    skill_id = "DATA_COMPRESSOR"
    meta_v1 = SkillVersionMeta(skill_id=skill_id, version="1.0.0")
    engine.register_skill_version(meta_v1)

    cases = [
        SkillRegressionCase(
            case_id="case_compress",
            input_args={"data": "AAAAABBBBB"},
            expected_predicate="pred_compressed",
        )
    ]
    engine.regression_harness.register_cases(skill_id, cases)

    predicates = {
        "pred_compressed": lambda r: len(r.get("compressed", "")) > 0 and r.get("ratio", 0) > 0,
    }

    # Runner hoàn hảo đáp ứng 100% test
    def perfect_runner(args):
        return {"compressed": "5A5B", "ratio": 0.4}

    meta_v2 = SkillVersionMeta(skill_id=skill_id, version="2.0.0")
    ok, msg = engine.upgrade_skill_version(
        new_meta=meta_v2,
        skill_runner=perfect_runner,
        predicates=predicates,
    )

    assert ok is True
    assert "UPGRADE_APPROVED" in msg
    assert engine._latest_versions[skill_id] == "2.0.0"

    # Phiên bản mới là ACTIVE
    assert engine._skills[skill_id]["2.0.0"].status == SkillLifecycleStatus.ACTIVE
    # Phiên bản cũ là DEPRECATED kèm con trỏ superseded_by
    old_meta = engine._skills[skill_id]["1.0.0"]
    assert old_meta.status == SkillLifecycleStatus.DEPRECATED
    assert old_meta.superseded_by == f"{skill_id}:2.0.0"

    # Gọi phiên bản cũ vẫn được nhưng có cảnh báo
    allowed, warn_msg, info = engine.can_invoke_skill(skill_id, version="1.0.0")
    assert allowed is True
    assert "WARNING_SKILL_DEPRECATED" in warn_msg


def test_condition_5_sunset_engine_blocks_invocation_and_chained_ledger(tmp_path):
    """Điều kiện 5: Tự động sunset kỹ năng quá hạn, chặn đứng thực thi và ghi nhận sổ cái băm chuỗi."""
    ledger_file = tmp_path / "skill_lifecycle_ledger.jsonl"
    engine = SkillSunsetEngine(ledger_path=ledger_file)

    skill_id = "LEGACY_REPORT_BUILDER"
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=120)  # Đã quá hạn 120 ngày (> 90 ngày)

    expired_meta = SkillVersionMeta(
        skill_id=skill_id,
        version="1.0.0",
        created_at=old_time.isoformat(),
        superseded_by=f"{skill_id}:2.0.0",
    )
    engine.register_skill_version(expired_meta)

    # 1. Quét hoàng hôn (Sunset Scan)
    sunset_items = engine.scan_and_sunset_expired_skills(current_time=now)
    assert len(sunset_items) == 1
    assert sunset_items[0]["skill_id"] == skill_id
    assert sunset_items[0]["version"] == "1.0.0"
    assert expired_meta.status == SkillLifecycleStatus.SUNSET

    # 2. Cố tình gọi kỹ năng đã SUNSET mà không có cờ cho phép -> Bị chặn đứng (fail-closed)
    can_run, err_msg, info = engine.can_invoke_skill(skill_id, version="1.0.0", allow_sunset=False)
    assert can_run is False
    assert "SKILL_SUNSET_ERROR" in err_msg
    assert info["superseded_by"] == f"{skill_id}:2.0.0"

    # 3. Cho phép gọi với cờ allow_sunset=True phục vụ kiểm toán lịch sử
    can_run_audit, audit_msg, _ = engine.can_invoke_skill(skill_id, version="1.0.0", allow_sunset=True)
    assert can_run_audit is True

    # 4. Kiểm tra sổ cái băm chuỗi SHA-256 Chained Ledger
    assert ledger_file.exists()
    lines = [json.loads(l) for l in ledger_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) >= 2  # Gồm register + sunset
    assert lines[0]["prev_hash"] == "GENESIS_SKILL_LIFECYCLE_HASH_000000"
    assert lines[1]["prev_hash"] == lines[0]["entry_hash"]


def test_condition_6_bootstrap_physical_skills_from_disk(tmp_path):
    """Điều kiện 6 (Phản biện Lượt 336): Tự động bootstrap quét kỹ năng thật từ intelligence/skills/."""
    from core.kernel.skill_lifecycle_engine import bootstrap_physical_skills

    test_ledger = tmp_path / "bootstrap_ledger.jsonl"
    engine = SkillSunsetEngine(ledger_path=test_ledger)

    loaded_count = bootstrap_physical_skills(engine=engine)
    assert loaded_count >= 100, f"Chỉ quét được {loaded_count} kỹ năng, yêu cầu >= 100 kỹ năng thật!"

    # Xác nhận kỹ năng cốt lõi SYSTEM_CORE_EXECUTOR có mặt trong registry
    assert "SYSTEM_CORE_EXECUTOR" in engine._skills
    meta = engine._skills["SYSTEM_CORE_EXECUTOR"]["1.0.0"]
    assert meta.status == SkillLifecycleStatus.ACTIVE


def test_condition_7_end_to_end_wiring_in_skill_retriever(tmp_path):
    """Điều kiện 7 (Phản biện Lượt 336): Đấu nối cổng Sunset vào đường chạy thực thi thật của SkillRetriever."""
    from core.os.cognition.skill_retriever import DynamicSkillRetriever

    test_ledger = tmp_path / "retriever_ledger.jsonl"
    engine = SkillSunsetEngine(ledger_path=test_ledger)

    # Đăng ký kỹ năng SEARCH_WEB_GLOBAL là ACTIVE
    engine.register_skill_version(SkillVersionMeta(
        skill_id="SEARCH_WEB_GLOBAL",
        version="1.0.0",
        status=SkillLifecycleStatus.ACTIVE,
    ))

    retriever = DynamicSkillRetriever(lifecycle_engine=engine)

    # 1. Khi kỹ năng đang ACTIVE -> Kiểm định thực thi OK
    can_exec, msg = retriever.verify_skill_execution_permission("SEARCH_WEB_GLOBAL")
    assert can_exec is True
    assert msg == "SKILL_ACTIVE_READY"

    # 2. Truy xuất động nạp thành công công cụ vào MCP tools
    verdict = retriever.retrieve_active_tools(
        query="Giá vàng và tỷ giá hôm nay",
        top_k=3,
    )
    selected_ids = [m.skill_id for m in verdict.selected_manifests]
    assert "SEARCH_WEB_GLOBAL" in selected_ids

    # 3. Hoàng hôn kỹ năng (SUNSET)
    meta = engine._skills["SEARCH_WEB_GLOBAL"]["1.0.0"]
    meta.status = SkillLifecycleStatus.SUNSET
    meta.superseded_by = "SEARCH_WEB_GLOBAL:2.0.0"

    # 4. Khi kỹ năng đã SUNSET -> Cổng thực thi CHẶN ĐỨNG (Fail-closed)
    can_exec_sunset, sunset_err = retriever.verify_skill_execution_permission("SEARCH_WEB_GLOBAL")
    assert can_exec_sunset is False
    assert "SKILL_SUNSET_ERROR" in sunset_err
    assert "SEARCH_WEB_GLOBAL:2.0.0" in sunset_err

    # 5. Truy xuất động TỰ ĐỘNG LOẠI BỎ kỹ năng SUNSET khỏi danh sách công cụ gửi LLM
    verdict_after = retriever.retrieve_active_tools(
        query="Giá vàng và tỷ giá hôm nay",
        top_k=3,
    )
    selected_ids_after = [m.skill_id for m in verdict_after.selected_manifests]
    assert "SEARCH_WEB_GLOBAL" not in selected_ids_after
    assert "SEARCH_WEB_GLOBAL:SUNSET" in verdict_after.excluded_manifests

