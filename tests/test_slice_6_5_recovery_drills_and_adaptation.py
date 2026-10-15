# -*- coding: utf-8 -*-
"""
tests/test_slice_6_5_recovery_drills_and_adaptation.py
Kiểm thử toàn diện Slice 6.5: Operational Recovery Drills & Sovereign Adaptation Harness.
Hiện thực hóa Bước 5 trong Lộ trình 1 Quý của Master:
"Đo recovery drills: cố tình chọc lỗi (tool die, mạng rớt, format lạ) đo tỷ lệ phục hồi
 — tiêu chí Adaptation hiện là ô trống duy nhất trong 10 tiêu chí."

Khóa chặt 5 điều kiện kiểm thử:
1. Điều kiện 1: Chọc lỗi Tool Crash (Broken Pipe / SIGKILL) phục hồi qua Circuit Breaker Fallback.
2. Điều kiện 2: Chọc lỗi Network Drop (Socket Timeout / Connection Refused) phục hồi qua Offline Cache.
3. Điều kiện 3: Chọc lỗi Malformed Format (JSON hỏng, markdown fence) tự phục hồi qua Self-Healing Parser.
4. Điều kiện 4: Toàn bộ 15 kịch bản Diễn tập Thích ứng đạt Tỷ lệ Phục hồi >= 90% (>= 0.90), đóng dấu CRITERION_FULFILLED.
5. Điều kiện 5: Sổ cái Chained Recovery Drill Ledger bảo đảm tính toàn vẹn băm chuỗi SHA-256.
"""

import json
from pathlib import Path
import pytest

from core.os.cognition.recovery_drill_harness import (
    FaultType,
    RecoveryDrillHarness,
)


def test_condition_1_tool_crash_recovery_drill(tmp_path):
    """Điều kiện 1: Phục hồi khi công cụ chính bị crash đột ngột."""
    ledger_file = tmp_path / "drill_ledger.jsonl"
    harness = RecoveryDrillHarness(ledger_path=ledger_file)

    def crashing_primary():
        raise BrokenPipeError("Subprocess pipe broken")

    def healthy_fallback():
        return {"status": "success", "data": "fallback_result"}

    res = harness.execute_tool_crash_drill(
        drill_id="test_crash_01",
        primary_tool=crashing_primary,
        fallback_tool=healthy_fallback,
        verifier=lambda r: r.get("status") == "success",
    )

    assert res.recovered is True
    assert res.recovery_mechanism == "CIRCUIT_BREAKER_FALLBACK"
    assert res.output_verified is True
    assert res.latency_ms > 0.0


def test_condition_2_network_drop_and_cache_fallback(tmp_path):
    """Điều kiện 2: Phục hồi khi mạng rớt / timeout socket qua cơ chế offline cache."""
    ledger_file = tmp_path / "drill_ledger.jsonl"
    harness = RecoveryDrillHarness(ledger_path=ledger_file)

    def failing_network(attempt: int):
        raise TimeoutError("Socket connect timeout 3.0s")

    def local_cache_provider():
        return {"cached": True, "data": "persisted_snapshot"}

    res = harness.execute_network_drop_drill(
        drill_id="test_net_01",
        network_caller=failing_network,
        offline_cache_provider=local_cache_provider,
        verifier=lambda r: r.get("cached") is True,
        max_retries=2,
    )

    assert res.recovered is True
    assert res.recovery_mechanism == "OFFLINE_CACHE_FALLBACK"
    assert res.output_verified is True


def test_condition_3_malformed_format_self_healing_repair(tmp_path):
    """Điều kiện 3: Tự phục hồi cấu trúc dữ liệu khi upstream trả về JSON dị dạng."""
    ledger_file = tmp_path / "drill_ledger.jsonl"
    harness = RecoveryDrillHarness(ledger_path=ledger_file)

    malformed_json = '```json\n{"action": "read_file", "path": "core/os/cognition/deep_fsm.py",}\n```'

    def robust_repair_parser(text: str):
        import re
        cleaned = text.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence_match:
            raw = fence_match.group(1)
            raw_clean = re.sub(r",\s*\}", "}", raw)
            return json.loads(raw_clean)
        raise ValueError("UNABLE_TO_REPAIR")

    res = harness.execute_malformed_format_drill(
        drill_id="test_format_01",
        raw_malformed_text=malformed_json,
        repair_parser=robust_repair_parser,
        verifier=lambda r: r.get("action") == "read_file",
    )

    assert res.recovered is True
    assert res.recovery_mechanism == "FAST_PARSER_SELF_HEALING_REPAIR"
    assert res.output_verified is True


def test_condition_4_full_sovereign_adaptation_suite_and_threshold(tmp_path):
    """Điều kiện 4: Chạy toàn bộ 15 kịch bản diễn tập thích ứng, đo tỷ lệ phục hồi >= 90%."""
    ledger_file = tmp_path / "drill_ledger.jsonl"
    harness = RecoveryDrillHarness(ledger_path=ledger_file)

    summary = harness.run_full_sovereign_adaptation_suite()

    assert summary["total_drills"] == 15
    assert summary["recovered_drills"] >= 14  # Tối thiểu 14/15 đạt >= 93%
    assert summary["recovery_rate"] >= 0.90, f"Recovery rate ({summary['recovery_rate']}) < 0.90!"
    assert summary["sovereign_adaptation_status"] == "CRITERION_FULFILLED"

    # Xác nhận cả 3 danh mục đều có kết quả phục hồi
    cats = summary["by_fault_category"]
    assert "TOOL_CRASH" in cats and cats["TOOL_CRASH"]["recovered"] == 5
    assert "NETWORK_DROP" in cats and cats["NETWORK_DROP"]["recovered"] == 5
    assert "MALFORMED_FORMAT" in cats and cats["MALFORMED_FORMAT"]["recovered"] == 5


def test_condition_5_chained_recovery_drill_ledger_integrity(tmp_path):
    """Điều kiện 5: Kiểm tra tính toàn vẹn băm chuỗi SHA-256 của sổ cái diễn tập phục hồi."""
    ledger_file = tmp_path / "drill_ledger.jsonl"
    harness = RecoveryDrillHarness(ledger_path=ledger_file)

    # Chạy toàn bộ diễn tập
    harness.run_full_sovereign_adaptation_suite()

    assert ledger_file.exists()
    lines = [json.loads(l) for l in ledger_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 16  # 15 ca diễn tập + 1 bản ghi adaptation_summary

    # Kiểm tra liên kết chuỗi băm
    assert lines[0]["prev_hash"] == "GENESIS_RECOVERY_DRILL_HASH_000000"
    for i in range(1, len(lines)):
        assert lines[i]["prev_hash"] == lines[i - 1]["entry_hash"], f"Đứt gãy băm tại bản ghi {i}"
