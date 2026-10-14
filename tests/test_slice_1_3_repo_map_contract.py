# -*- coding: utf-8 -*-
"""
tests/test_slice_1_3_repo_map_contract.py
=========================================
Slice 1.3 Contract-First Test Suite (Red -> Green TDD per Law #1 & Turn 264):
1. 6 Core Architectural Questions answered dynamically by 2-Tier AST RepoMap:
   - Q1_INGRESS (Tiếp nhận yêu cầu)
   - Q2_CONTROLLER (Quyết định / Điều phối)
   - Q3_ACTUATOR (Thực thi công cụ)
   - Q4_VERIFICATION (Xác minh kết quả)
   - Q5_STATE_PERSISTENCE (Lưu trữ dữ liệu & trạng thái)
   - Q6_BLAST_RADIUS (Phân tích phạm vi ảnh hưởng ngược khi sửa module/symbol)
2. 2-Tier AST RepoMap (Tier 0 Overview + Tier 1 Symbol/Import/Blast-Radius Navigation)
   + Navigation Turn Reduction Benchmark (10 real JKAI symbol/impact tasks).
3. StageAttribution 6-Stage Failure Attribution Telemetry Contract (Enum + Mandatory Verdict Field).
4. 5 Independent Stream Metrics Evaluators (Retrieval Recall, Evidence Coverage,
   Citation Accuracy, Task Correctness, Latency & Token Cost) proving
   100% Citation Accuracy != 100% Evidence Coverage (Point B of THAM KHẢO).
5. Point E Clean Dependency Import & Reproducibility Audit for 17 dependencies in pyproject.toml.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest


def test_repo_map_answers_6_core_architectural_questions():
    """
    Contract 1 (Point C): RepoMap must answer all 6 Core Architectural Questions
    with verified existing files, line ranges, and key symbols on disk.
    """
    from core.utils.repo_map import answer_architectural_questions, get_tier0_overview

    ws_root = Path(__file__).resolve().parent.parent
    answers = answer_architectural_questions(ws_root)

    required_questions = (
        "Q1_INGRESS",
        "Q2_CONTROLLER",
        "Q3_ACTUATOR",
        "Q4_VERIFICATION",
        "Q5_STATE_PERSISTENCE",
        "Q6_BLAST_RADIUS",
    )
    for q_key in required_questions:
        assert q_key in answers, f"Missing architectural question {q_key}"
        q_data = answers[q_key]
        assert q_data.get("question"), f"Empty question prompt for {q_key}"
        components = q_data.get("components", [])
        assert len(components) >= 1, f"No verified components found for {q_key}"
        for comp in components:
            rel_path = comp["path"]
            full_path = ws_root / rel_path
            assert full_path.is_file(), f"Component path does not exist on disk: {rel_path}"
            assert comp.get("symbols"), f"Component {rel_path} in {q_key} must list AST symbols with line ranges"

    # Explicit semantic checks on the 6 answers
    q1_paths = {c["path"] for c in answers["Q1_INGRESS"]["components"]}
    assert "services/ai-brain/app.py" in q1_paths or "services/ai-brain/state_pipeline.py" in q1_paths

    q2_paths = {c["path"] for c in answers["Q2_CONTROLLER"]["components"]}
    assert "core/kernel/project_agent_loop.py" in q2_paths

    q3_paths = {c["path"] for c in answers["Q3_ACTUATOR"]["components"]}
    assert "intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py" in q3_paths

    q4_paths = {c["path"] for c in answers["Q4_VERIFICATION"]["components"]}
    assert "core/utils/ast_code_auditor.py" in q4_paths

    q5_paths = {c["path"] for c in answers["Q5_STATE_PERSISTENCE"]["components"]}
    assert "core/kernel/durable_checkpoint.py" in q5_paths

    # Q6 Blast Radius must demonstrate live reverse-dependency edges
    q6_sample = answers["Q6_BLAST_RADIUS"]
    assert q6_sample.get("reverse_dependency_edges", 0) > 10

    tier0 = get_tier0_overview(ws_root, max_tokens=450)
    assert "Q1_INGRESS" in tier0["text"]
    assert "Q6_BLAST_RADIUS" in tier0["text"]
    assert tier0["estimated_tokens"] > 50
    assert tier0["budget_expandable"] is True


def test_repo_map_tier1_symbol_and_blast_radius_navigation():
    """
    Contract 2: Tier 1 symbol lookup & reverse-import blast radius computation.
    """
    from core.utils.repo_map import query_repo_map, query_blast_radius

    ws_root = Path(__file__).resolve().parent.parent

    # Warm index and query symbol `analyze_python_aci_diagnostics`
    res = query_repo_map(
        query="analyze_python_aci_diagnostics",
        workspace_root=ws_root,
        include_blast_radius=True,
    )
    assert res["status"] == "success"
    matches = res["symbol_matches"]
    assert any(
        m["name"] == "analyze_python_aci_diagnostics"
        and m["path"] == "core/utils/ast_code_auditor.py"
        and m["start_line"] >= 300
        for m in matches
    )

    # Check blast radius of `core/utils/ast_code_auditor.py`
    blast = query_blast_radius("core/utils/ast_code_auditor.py", workspace_root=ws_root)
    importer_paths = {imp["importer_path"] for imp in blast["importers"]}
    assert "intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py" in importer_paths
    assert "core/kernel/project_agent_loop.py" in importer_paths

    # Warm query must complete under 25ms
    res_warm = query_repo_map(
        query="ProjectAgentLoop",
        workspace_root=ws_root,
        include_blast_radius=True,
    )
    assert res_warm["elapsed_ms"] < 25.0


def test_repo_map_navigation_benchmark_10_tasks():
    """
    Contract 3: 10-task localization benchmark comparing blind search turns vs RepoMap turns.
    """
    from core.utils.repo_map import run_repo_map_navigation_benchmark

    report = run_repo_map_navigation_benchmark()
    assert report["total_tasks"] == 10
    assert report["repo_map_accuracy"] == 1.0
    assert report["avg_repo_map_turns"] <= 1.2
    assert report["avg_blind_search_turns"] >= 3.0
    assert report["turn_reduction_ratio"] >= 0.50


def test_stage_attribution_6_stage_telemetry_contract():
    """
    Contract 4 (Section 3 of THAM KHẢO): 6-Stage Failure Attribution Enum & Mandatory Verdict Field.
    """
    from core.utils.repo_map import (
        StageAttribution,
        StageTelemetryVerdict,
        classify_step_stage_attribution,
    )
    from core.kernel.action_validator import validate_action

    expected_stages = [
        "GOAL_INGRESS",
        "EVIDENCE_RETRIEVAL",
        "ACTION_PROPOSAL",
        "CONTROLLER_GATE",
        "TOOL_EXECUTION",
        "COMPLETION_VERIFICATION",
    ]
    assert [s.value for s in StageAttribution] == expected_stages

    # Mandatory field in StageTelemetryVerdict
    verdict = StageTelemetryVerdict(
        task_id="test-task-1",
        step=1,
        stage_attribution=StageAttribution.EVIDENCE_RETRIEVAL,
        outcome_ok=True,
        detail="Queried RepoMap Tier 1 for symbol localization",
    )
    dumped = verdict.to_dict()
    assert dumped["stage_attribution"] == "EVIDENCE_RETRIEVAL"

    # Automatic stage classification across failure modes
    assert classify_step_stage_attribution(tool=None, decision="SCHEMA_INVALID", outcome_ok=False) == StageAttribution.ACTION_PROPOSAL
    assert classify_step_stage_attribution(tool="unknown_xyz", decision="UNKNOWN_TOOL", outcome_ok=False) == StageAttribution.CONTROLLER_GATE
    assert classify_step_stage_attribution(tool="query_repo_map", decision="PERMIT", outcome_ok=True) == StageAttribution.EVIDENCE_RETRIEVAL
    assert classify_step_stage_attribution(tool="replace_file_content", decision="PERMIT", outcome_ok=False) == StageAttribution.TOOL_EXECUTION
    assert classify_step_stage_attribution(tool="verify_file", decision="PERMIT", outcome_ok=False, is_final_verification=True) == StageAttribution.COMPLETION_VERIFICATION

    # ActionValidator integration for `query_repo_map`
    act_verdict = validate_action("query_repo_map", {"query": "ProjectAgentLoop"}, check_firewall=False)
    assert act_verdict.decision.value == "PERMIT"
    assert act_verdict.stage_attribution == StageAttribution.CONTROLLER_GATE.value


def test_5_stream_metrics_contract_and_coverage_vs_citation_distinction():
    """
    Contract 5 (Point B of THAM KHẢO): 5 independent stream metrics functions,
    proving 100% Citation Accuracy does NOT imply 100% Evidence Coverage.
    """
    from core.utils.repo_map import (
        compute_retrieval_recall,
        compute_evidence_coverage,
        compute_citation_accuracy,
        compute_task_correctness,
        compute_latency_token_cost,
        evaluate_stream_5_metrics,
    )

    # Case where agent cites 1 chunk with 100% accurate line citation,
    # but only reads 1 out of 4 required evidence spans (25% Evidence Coverage).
    required_spans = [(10, 20), (100, 120), (300, 320), (700, 750)]
    retrieved_spans = [(10, 25), (100, 125)]  # 2/4 retrieved = 0.50 recall
    read_spans = [(10, 20)]                   # 1/4 covered = 0.25 coverage
    citations = [{"line_start": 10, "line_end": 20, "supported_by_source": True}]

    recall = compute_retrieval_recall(required_spans, retrieved_spans)
    coverage = compute_evidence_coverage(required_spans, read_spans)
    citation_acc = compute_citation_accuracy(citations)
    correctness = compute_task_correctness(["fact_1"], ["fact_1", "fact_2", "fact_3", "fact_4"])
    cost = compute_latency_token_cost(elapsed_ms=120.5, prompt_tokens=450, completion_tokens=150)

    assert recall == 0.50
    assert coverage == 0.25
    assert citation_acc == 1.00
    assert citation_acc != coverage, "100% citation accuracy must NOT masquerade as 100% evidence coverage"
    assert correctness == 0.25
    assert cost["total_tokens"] == 600

    summary = evaluate_stream_5_metrics(
        required_spans=required_spans,
        retrieved_spans=retrieved_spans,
        read_spans=read_spans,
        citations=citations,
        predicted_facts=["fact_1"],
        expected_facts=["fact_1", "fact_2", "fact_3", "fact_4"],
        elapsed_ms=120.5,
        prompt_tokens=450,
        completion_tokens=150,
    )
    assert set(summary.keys()) >= {
        "retrieval_recall",
        "evidence_coverage",
        "citation_accuracy",
        "task_correctness",
        "latency_token_cost",
    }


def test_actuator_query_repo_map_and_point_e_dependency_audit():
    """
    Contract 6: Actuator `logic.query_repo_map` + Point E dependency audit.
    """
    from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR import logic
    from core.utils.repo_map import audit_pyproject_dependencies_point_e

    res = asyncio.run(logic.query_repo_map(query="analyze_python_aci_diagnostics"))
    assert res["status"] == "success"
    assert len(res["symbol_matches"]) >= 1

    dep_audit = audit_pyproject_dependencies_point_e()
    assert dep_audit["declared_count"] == 17
    assert "importable_in_current_env" in dep_audit
    assert dep_audit["clean_venv_install_status"] in ("PASS", "NOT_TESTED", "PARTIAL")
