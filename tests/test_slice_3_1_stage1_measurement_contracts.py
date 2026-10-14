# -*- coding: utf-8 -*-
"""
tests/test_slice_3_1_stage1_measurement_contracts.py
====================================================
Slice 3.1 (Giai đoạn 1 — Đo được mới tối ưu được):
1. Kế toán token/latency theo 6 khâu StageAttribution (10-step mission mẫu, khớp ±5% với bill Ollama đo ngoài).
2. CacheAligner-flag (học Headroom): Bộ kiểm tra tiền tố system trước mỗi call, phân loại đúng 20/20 prompt mẫu (10 sạch + 10 nhiễm volatile).
3. Capability registry tự probe (học WeKnora): Tự động probe 3 model Ollama (context thật, JSON-mode, tốc độ, num_predict an toàn -> ghi card JSON, sai số tốc độ < 20% khi chạy lại).
4. Đồng bộ hằng số READ_ONLY_REPLAY_SAFE_TOOLS trong worktree_sandbox.py theo nhắc nhở Lượt 278 của OpenCode.
"""

from __future__ import annotations

import json
from pathlib import Path


def test_stage1_1_stage_attribution_token_latency_accounting_10_steps():
    """
    Mục 1 (Giai đoạn 1): Kế toán token/latency theo 6 khâu StageAttribution.
    Xong khi: mission mẫu 10 bước bóc được bảng chi phí theo khâu,
    tổng khớp ±5% với bill Ollama đo ngoài.
    """
    from core.utils.repo_map import (
        StageAttribution,
        get_mission_stage_cost_report,
        record_mission_stage_trace,
        reset_mission_stage_ledger,
    )

    mission_id = "mission_stage1_cost_audit_10steps"
    reset_mission_stage_ledger(mission_id)

    steps_plan = [
        (1, StageAttribution.GOAL_INGRESS, "router_ingress", 120, 35, 18.5),
        (2, StageAttribution.EVIDENCE_RETRIEVAL, "query_repo_map", 210, 80, 12.0),
        (3, StageAttribution.EVIDENCE_RETRIEVAL, "view_file", 450, 110, 9.4),
        (4, StageAttribution.ACTION_PROPOSAL, "planner_propose", 680, 190, 420.0),
        (5, StageAttribution.CONTROLLER_GATE, "action_validator", 40, 10, 2.1),
        (6, StageAttribution.TOOL_EXECUTION, "replace_file_content", 520, 140, 35.0),
        (7, StageAttribution.EVIDENCE_RETRIEVAL, "read_stream_window", 310, 60, 6.2),
        (8, StageAttribution.ACTION_PROPOSAL, "planner_refine", 610, 175, 390.0),
        (9, StageAttribution.TOOL_EXECUTION, "run_command", 290, 95, 810.0),
        (10, StageAttribution.COMPLETION_VERIFICATION, "verify_file", 180, 55, 14.8),
    ]

    expected_total_tokens = sum(t_in + t_out for _, _, _, t_in, t_out, _ in steps_plan)
    for step_no, stage, tool_name, tok_in, tok_out, lat_ms in steps_plan:
        record_mission_stage_trace(
            mission_id=mission_id,
            step=step_no,
            stage_attribution=stage,
            tool=tool_name,
            tokens_in=tok_in,
            tokens_out=tok_out,
            latency_ms=lat_ms,
        )

    # Giả lập bill Ollama đo ngoài lệch nhẹ +2.1% (nằm trong ngưỡng ±5%)
    external_ollama_bill = int(round(expected_total_tokens * 1.021))
    report = get_mission_stage_cost_report(
        mission_id=mission_id,
        external_ollama_bill_tokens=external_ollama_bill,
    )

    assert report["mission_id"] == mission_id
    assert report["total_steps"] == 10
    assert report["total_tokens"] == expected_total_tokens
    assert set(report["by_stage"].keys()) == {s.value for s in StageAttribution}
    assert report["by_stage"]["EVIDENCE_RETRIEVAL"]["steps"] == 3
    assert report["by_stage"]["ACTION_PROPOSAL"]["tokens_in"] == 680 + 610
    assert report["top_token_bottleneck_stage"] == "ACTION_PROPOSAL"
    assert report["top_latency_bottleneck_stage"] == "TOOL_EXECUTION"
    assert report["reconciliation_delta_pct"] <= 5.0
    assert report["within_5pct_tolerance"] is True


def test_stage1_2_cache_aligner_flag_20_prompts_benchmark():
    """
    Mục 2 (Giai đoạn 1): CacheAligner-flag (học Headroom).
    Xong khi: 20 prompt mẫu (10 sạch + 10 nhiễm volatile ở đầu prompt) phân loại đúng 20/20.
    """
    from core.kernel.context_manager import ContextManager, inspect_system_prefix_cache_alignment

    clean_prompts = [
        "You are JKAI Zenith Sovereign Architect. Follow strict deterministic engineering rules.",
        "SYSTEM DIRECTIVE: Always validate AST syntax before writing files to disk.",
        "Role: Senior Red Team Auditor. Verify every claim against empirical test output.",
        "Nguyên tắc cốt lõi: Không bao giờ bịa đặt kết quả tìm kiếm khi mạng ngoại tuyến.",
        "You are a local-first Python assistant. Use iter_workspace_files for repository traversal.",
        "JKAI Kernel Policy v28.4.1: Enforce GBNF grammar constraints on structured JSON tool calls.",
        "Security Policy: Block all RFC1918 private IPs and cloud metadata endpoints in URL fetch.",
        "Memory Governance: Preserve pinned system instructions at index 0 for KV cache reuse.",
        "Coding Standard: Write behavioral failing tests before modifying production modules.",
        "Trợ lý kỹ thuật JKAI: Trả lời ngắn gọn, chính xác, trích dẫn dòng code cụ thể.",
    ]

    volatile_infected_prompts = [
        "[System Clock: 2026-10-12T19:25:04+07:00] You are JKAI Zenith Sovereign Architect.",
        "Current timestamp: 1791807904 | Role: Senior Red Team Auditor.",
        "request_id=9f8e7d6c-5b4a-4321-8765-1029384756ab\nYou are a coding assistant.",
        "task_state=RUNNING_STEP_3 | current_step=3 | Follow deterministic rules.",
        "Workspace sandbox: .zenith/worktrees/wt_99881122/core/utils/engine.py\nSystem prompt.",
        "current_time: 19:26:55 — You are JKAI Zenith local assistant.",
        "trace_id: trc_887766554433 | Always verify code with pytest.",
        "free_vram_mb=4128 | cpu_load_pct=74.2 | System Role: Planner.",
        "now_ms=1791807904123 — JKAI Kernel Policy: Use local models first.",
        "Temp dir: /tmp/jkai_run_88219a/session.json | Role: Executor.",
    ]

    assert len(clean_prompts) == 10
    assert len(volatile_infected_prompts) == 10

    clean_correct = 0
    for idx, prompt in enumerate(clean_prompts, 1):
        res = inspect_system_prefix_cache_alignment(prompt)
        assert res["volatile_flag"] is False, f"Clean prompt #{idx} falsely flagged: {res}"
        assert res["cache_aligned"] is True
        clean_correct += 1

    infected_correct = 0
    for idx, prompt in enumerate(volatile_infected_prompts, 1):
        res = inspect_system_prefix_cache_alignment(prompt)
        assert res["volatile_flag"] is True, f"Volatile prompt #{idx} missed: {prompt}"
        assert res["cache_aligned"] is False
        assert len(res["reasons"]) >= 1
        infected_correct += 1

    assert clean_correct + infected_correct == 20

    # Kiểm tra tích hợp trực tiếp vào ContextManager KV telemetry
    cm = ContextManager(max_token_budget=4096, reserved_output_tokens=512)
    cm.prune_messages(
        messages=[
            {"role": "system", "content": volatile_infected_prompts[0]},
            {"role": "user", "content": "Hello"},
        ],
        session_id="sess_cache_aligner_check",
    )
    kv = cm.get_kv_prefix_telemetry("sess_cache_aligner_check")
    assert kv["cache_aligner_clean"] is False
    assert len(kv["volatile_flags"]) >= 1


def _live_ollama_host_or_none():
    try:
        import httpx
        from core.governor.model_capabilities import normalize_ollama_host

        host = normalize_ollama_host(None)
        r = httpx.get(f"{host}/api/tags", timeout=2.0)
        if r.status_code == 200:
            return host, {m.get("name") for m in r.json().get("models", [])}
    except Exception:
        pass
    return None, set()


def test_stage1_3_capability_registry_live_show_3_models(tmp_path: Path):
    """
    Mục 3a (Giai đoạn 1) — Kiểm tra nhanh (< 0.3s) metadata thật từ `/api/show`:
    - probe_source bắt buộc == "ollama_api_show" và context_length khớp đúng /api/show.
    - Ollama offline -> SKIP (NOT_TESTED), không được PASS trên số fallback.
    """
    import pytest
    import httpx
    from core.governor.model_capabilities import probe_installed_models_registry

    target_models = [
        "qwen3.5:4b",
        "oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU",
        "hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:UD-Q4_K_XL",
    ]
    host, installed = _live_ollama_host_or_none()
    if host is None:
        pytest.skip("NOT_TESTED: Ollama offline — live /api/show probe not executed")
    missing = [m for m in target_models if m not in installed]
    if missing:
        pytest.skip(f"NOT_TESTED: models not installed: {missing}")

    out_file = tmp_path / "model_capability_cards.json"
    report = probe_installed_models_registry(
        model_names=target_models,
        ollama_host=host,
        output_path=out_file,
        repeat_runs=2,
        measure_speed=False,
    )
    persisted = json.loads(out_file.read_text(encoding="utf-8"))
    assert persisted["probed_count"] == 3

    for model_name in target_models:
        card = report["cards"][model_name]
        assert card["probe_source"] == "ollama_api_show"
        assert card["card_status"] == "LIVE"
        assert card["speed_source"] == "NOT_TESTED"

        show = httpx.post(f"{host}/api/show", json={"name": model_name}, timeout=10.0).json()
        expected_ctx = next(
            int(v) for k, v in (show.get("model_info") or {}).items() if k.endswith(".context_length")
        )
        assert card["context_length"] == expected_ctx
        assert int(card["recommended_num_predict"]) >= 512


def test_stage1_3_opt_in_live_generate_speed_3_models(tmp_path: Path):
    """
    Mục 3b (Giai đoạn 1) — Đóng nợ Lượt 282 (`tach-test-live-khoi-suite-mac-dinh`):
    Benchmark `/api/generate` nạp cả 3 model (gồm 30B, mất ~70s) chỉ chạy khi bật
    `JKAI_RUN_LIVE_MODEL_PROBE=1`, mặc định skip minh bạch với `NOT_TESTED`.
    """
    import os
    import pytest
    from core.governor.model_capabilities import probe_installed_models_registry

    if os.getenv("JKAI_RUN_LIVE_MODEL_PROBE", "0") != "1":
        pytest.skip(
            "NOT_TESTED: Heavy 70s 3-model /api/generate speed benchmark is opt-in (set JKAI_RUN_LIVE_MODEL_PROBE=1)"
        )

    target_models = [
        "qwen3.5:4b",
        "oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU",
        "hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:UD-Q4_K_XL",
    ]
    host, installed = _live_ollama_host_or_none()
    if host is None:
        pytest.skip("NOT_TESTED: Ollama offline — live capability probe not executed")
    missing = [m for m in target_models if m not in installed]
    if missing:
        pytest.skip(f"NOT_TESTED: models not installed: {missing}")

    out_file = tmp_path / "model_capability_cards_live.json"
    report = probe_installed_models_registry(
        model_names=target_models,
        ollama_host=host,
        output_path=out_file,
        repeat_runs=2,
        measure_speed=True,
    )
    for model_name in target_models:
        card = report["cards"][model_name]
        assert card["speed_source"] == "live_api_generate"
        assert len(card["speed_samples_tps"]) == 2
        assert card["tokens_per_sec"] > 0.0
        assert card["repeat_speed_drift_pct"] < 20.0



def test_stage1_3b_capability_probe_offline_marks_fallback_not_tested():
    """
    Khi /api/show và /api/generate không truy cập được: card phải đóng dấu FALLBACK,
    tốc độ = None (NOT_TESTED), không bao giờ sinh số tốc độ giả.
    """
    from core.governor.model_capabilities import probe_ollama_model_card

    def _dead_show(host, model):
        raise ConnectionError("offline")

    def _dead_generate(host, model, num_predict):
        raise ConnectionError("offline")

    card = probe_ollama_model_card(
        "qwen3.5:4b",
        ollama_host="http://127.0.0.1:9",
        show_fetcher=_dead_show,
        generate_fetcher=_dead_generate,
        measure_speed=True,
    )
    assert card["probe_source"] == "deterministic_fallback"
    assert card["card_status"] == "FALLBACK"
    assert card["speed_source"] == "NOT_TESTED"
    assert card["tokens_per_sec"] is None
    assert card["repeat_speed_drift_pct"] is None
    assert card["speed_samples_tps"] == []


def test_stage1_3c_ollama_host_normalization_handles_bind_all_address():
    """OLLAMA_HOST=0.0.0.0 (địa chỉ bind) phải được chuẩn hóa về 127.0.0.1 để client gọi được."""
    from core.governor.model_capabilities import normalize_ollama_host

    assert normalize_ollama_host("0.0.0.0") == "http://127.0.0.1:11434"
    assert normalize_ollama_host("0.0.0.0:11434") == "http://127.0.0.1:11434"
    assert normalize_ollama_host("http://0.0.0.0:11500/") == "http://127.0.0.1:11500"
    assert normalize_ollama_host("http://host.docker.internal:11434") == "http://host.docker.internal:11434"


def test_turn278_open_reminder_read_only_replay_safe_tools_constant():
    """
    Đóng nhắc nhở Lượt 278 của OpenCode: READ_ONLY_REPLAY_SAFE_TOOLS phải tồn tại
    tường minh trong core.os.cognition.worktree_sandbox để grep thấy ngay.
    """
    from core.os.cognition.worktree_sandbox import READ_ONLY_REPLAY_SAFE_TOOLS

    assert "view_file" in READ_ONLY_REPLAY_SAFE_TOOLS
    assert "query_repo_map" in READ_ONLY_REPLAY_SAFE_TOOLS
    assert "verify_file" in READ_ONLY_REPLAY_SAFE_TOOLS
    assert "write_to_file" not in READ_ONLY_REPLAY_SAFE_TOOLS
    assert "run_command" not in READ_ONLY_REPLAY_SAFE_TOOLS
