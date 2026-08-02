#!/usr/bin/env python3
"""
Automated Benchmark & Quality Evaluator for JKAI Zenith.
Evaluates system quality across 3 key performance dimensions:
1. Intent Routing Accuracy (%)
2. Tool Argument Parsing & Type Coercion Rate (%)
3. Autonomous Self-Healing Success Rate (%)
Outputs structured JSON report to evaluation_report.json.
"""

import os
import time
import json
import asyncio
from typing import Dict, Any, List

from intelligence.agents.agent_router import agent_router
from core.guardrails.tool_schema_validator import tool_schema_validator
from core.kernel.context_manager import context_manager


def run_intent_routing_benchmark() -> Dict[str, Any]:
    """Evaluates agent router's intent classification accuracy against test dataset."""
    test_cases = [
        ("Lập kế hoạch phân rã nhiệm vụ cho hệ thống", ["planner", "strategist", "coordinator"]),
        ("Viết code Python và build ứng dụng", ["executor", "sparc_engineer", "default_executor"]),
        ("Đánh giá bảo mật và quét lỗ hổng", ["security_architect", "critic"]),
        ("Đo benchmark và tối ưu hóa hiệu năng", ["performance_engineer", "critic"]),
        ("Tra cứu tài liệu và nghiên cứu báo cáo khoa học", ["scholar", "receptionist"]),
    ]

    correct = 0
    total = len(test_cases)
    results = []

    for prompt, expected_agents in test_cases:
        routed = agent_router.route_task(prompt)
        routed_name = routed["name"].lower().replace("-", "_")
        is_correct = any(expected.lower().replace("-", "_") in routed_name for expected in expected_agents)
        if is_correct:
            correct += 1
        results.append({
            "prompt": prompt,
            "selected_agent": routed_name,
            "expected_candidates": expected_agents,
            "passed": is_correct
        })

    accuracy = (correct / total) * 100
    return {
        "metric": "Intent Routing Accuracy",
        "score_pct": round(accuracy, 2),
        "passed": correct,
        "total": total,
        "details": results
    }


def run_tool_validation_benchmark() -> Dict[str, Any]:
    """Evaluates JSON tool call parser and parameter coercion reliability."""
    test_payloads = [
        ('```json\n{"tool": "run_command", "args": {"command": "pytest", "timeout": "60"}}\n```', True),
        ('{"action": "view_file", "parameters": {"path": "main.py"}}', True),
        ('Invalid string without JSON payload', False),
    ]

    correct = 0
    total = len(test_payloads)
    results = []

    for payload, expected_valid in test_payloads:
        tool_name, args, err = tool_schema_validator.parse_tool_call(payload)
        is_valid = tool_name is not None and args is not None
        if is_valid == expected_valid:
            correct += 1
        results.append({
            "payload_snippet": payload[:40],
            "parsed_tool": tool_name,
            "is_valid": is_valid,
            "expected_valid": expected_valid,
            "passed": is_valid == expected_valid
        })

    accuracy = (correct / total) * 100
    return {
        "metric": "Tool Validation & Parsing Accuracy",
        "score_pct": round(accuracy, 2),
        "passed": correct,
        "total": total,
        "details": results
    }


def run_context_pruner_benchmark() -> Dict[str, Any]:
    """Evaluates context manager's memory preservation efficiency under heavy load."""
    sys_msg = {"role": "system", "content": "Pinned System Instruction."}
    msgs = [sys_msg] + [{"role": "user", "content": f"Turn {i}: " + ("content payload text " * 150)} for i in range(40)]

    pruned = context_manager.prune_messages(msgs)
    is_pinned = pruned[0] == sys_msg
    is_compressed = len(pruned) < len(msgs)

    passed = is_pinned and is_compressed
    return {
        "metric": "Context Window Preservation Rate",
        "score_pct": 100.0 if passed else 0.0,
        "system_prompt_pinned": is_pinned,
        "history_pruned": is_compressed,
        "original_messages": len(msgs),
        "pruned_messages": len(pruned)
    }


def main():
    print("[BENCHMARK] Initiating Automated Quality Benchmark Suite for JKAI Zenith...")
    t0 = time.time()

    routing_res = run_intent_routing_benchmark()
    tool_res = run_tool_validation_benchmark()
    context_res = run_context_pruner_benchmark()

    overall_score = round((routing_res["score_pct"] + tool_res["score_pct"] + context_res["score_pct"]) / 3, 2)
    elapsed_sec = round(time.time() - t0, 3)

    report = {
        "timestamp": time.time(),
        "elapsed_seconds": elapsed_sec,
        "overall_quality_score": overall_score,
        "metrics": {
            "intent_routing": routing_res,
            "tool_validation": tool_res,
            "context_preservation": context_res
        }
    }

    report_path = os.path.join(os.getenv("WORKSPACE_ROOT", r"D:\Docker\JKAI"), "evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("JKAI ZENITH BENCHMARK SUMMARY REPORT")
    print("=" * 60)
    print(f"Overall Quality Score      : {overall_score}%")
    print(f"1. Intent Routing Accuracy    : {routing_res['score_pct']}% ({routing_res['passed']}/{routing_res['total']})")
    print(f"2. Tool Validation Rate       : {tool_res['score_pct']}% ({tool_res['passed']}/{tool_res['total']})")
    print(f"3. Context Preservation Rate  : {context_res['score_pct']}%")
    print(f"Evaluation Time               : {elapsed_sec}s")
    print(f"Full Report Saved To          : {report_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
