# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: tests/test_structured_output_grammar.py
- Role: Sealed 50-Prompt Structured Output Benchmark & Grammar-Constrained Decoding (GBNF/JSON Schema) Suite
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.4.1
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Any, Type

import pytest
from pydantic import BaseModel, ValidationError

import core.utils.engine as engine_mod
from core.utils.engine import JKAIIntelligenceEngine
from core.utils.regex import extract_json
from core.utils.structured_output import (
    SCHEMA_REGISTRY,
    CriticOutput,
    ExecuteOutput,
    LookupOutput,
    PlanOutput,
    StructuredOutputWrapper,
)

# ==============================================================================
# SEALED 50-PROMPT STRUCTURED OUTPUT BENCHMARK (EN / VI CÓ DẤU / VI KHÔNG DẤU / MIX)
# Covers all 4 core structured schemas: PLANNER (15), CRITIC (15), EXECUTOR (10), LOOKUP (10)
# ==============================================================================
SEALED_50_STRUCTURED_PROMPTS: list[dict[str, Any]] = [
    # --- 1..15: PLANNER (PlanOutput: required `steps: list[dict]`, optional `reasoning: str`) ---
    {"id": "P01", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Lập kế hoạch kiểm tra sức khỏe container ai-brain và redis-ai."},
    {"id": "P02", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Lap ke hoach sao luu co so du lieu SQLite truoc khi nang cap schema."},
    {"id": "P03", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Create a 2-step plan to inspect port 11434 GPU models and verify VRAM usage."},
    {"id": "P04", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Lập kế hoạch debug lỗi timeout 400s trong wait_for_opencode_reply.py."},
    {"id": "P05", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Kiem tra file rule_hardware.md va doi chieu tham so num_predict cua role CHAT."},
    {"id": "P06", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Plan a safe rollback if git worktree mutation fails unit tests."},
    {"id": "P07", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Thiết kế các bước chạy pytest cho module sovereign_reflex_hub.py."},
    {"id": "P08", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Phan tich nguyen nhan container ai-executor-1 khoi dong lai va lap ke hoach xu ly."},
    {"id": "P09", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Build an execution plan to scan Python AST symbols for core/utils/engine.py."},
    {"id": "P10", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Lập kế hoạch dọn dẹp log cũ vượt quá 100MB trong thư mục logs."},
    {"id": "P11", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Kiem tra ket noi noi bo giua ai-control-plane va ai-worker qua Redis queue."},
    {"id": "P12", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Generate a step-by-step plan to validate SHA-256 hashes in archive_manifest.json."},
    {"id": "P13", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Lập kế hoạch cập nhật CHANGELOG.md và ghim version v28.4.1 vào system prompt."},
    {"id": "P14", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Lap ke hoach do toc do KV-cache prefix hit rate truoc va sau khi sap xep system prompt."},
    {"id": "P15", "role": "PLANNER", "schema_cls": PlanOutput, "prompt": "Plan a security audit to ensure zero external cloud URLs in intelligence manifests."},

    # --- 16..30: CRITIC (CriticOutput: required `passed: bool`, `issues: list[str]`, `suggestions: list[str]`) ---
    {"id": "C01", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Đánh giá đoạn code dùng eval(user_input) trực tiếp trong API endpoint."},
    {"id": "C02", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Danh gia viec xoa file .keyword.md ma khong xin phep Master."},
    {"id": "C03", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Audit a patch that uses atomic_write with .tmp + fsync + os.replace and passes 10/10 tests."},
    {"id": "C04", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Kiểm toán hàm reset state.json gán mù quáng last_triggered_turn = 0 khi đang chờ phản hồi."},
    {"id": "C05", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Kiem toan cau hinh firewall mo cong 0.0.0.0:6379 Redis ra internet khong mat khau."},
    {"id": "C06", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Review a clean refactoring that adds type hints and preserves 100% backward compatibility."},
    {"id": "C07", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Phản biện việc tạo thêm file graph memory mới khi entity_graph_memory.py đã tồn tại."},
    {"id": "C08", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Danh gia ban va NUM_PREDICT=2048 kem auto-continue 1 nhip khi done_reason==length."},
    {"id": "C09", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Evaluate a SQL query built with string concatenation: SELECT * FROM users WHERE id = ' + uid."},
    {"id": "C10", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Thẩm định việc gọi API đám mây bên ngoài khi biến môi trường JKAI_LOCAL_ONLY=1 đang bật."},
    {"id": "C11", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Kiem tra doan code bat ngoai le bare except: pass che giau loi ghi file quan trong."},
    {"id": "C12", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Audit a unit test suite that mocks every function and never exercises the real production method."},
    {"id": "C13", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Đánh giá cơ chế kiểm tra 4 điều kiện Turn Block (format, turn_chain, session_match, sha256)."},
    {"id": "C14", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Phan bien viec tuyen bo >90% KV-cache hit rate khi chua co bat ky so do prompt_eval_count nao."},
    {"id": "C15", "role": "CRITIC", "schema_cls": CriticOutput, "prompt": "Review a pure stdlib AST linter that checks syntax and symtable in under 10ms."},

    # --- 31..40: EXECUTOR (ExecuteOutput: required `action: str`, `params: dict`, `result: Optional[str]`) ---
    {"id": "E01", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Thực thi hành động đọc tệp CHANGELOG.md từ dòng 1 đến dòng 30."},
    {"id": "E02", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Chay lenh pytest cho tep tests/test_two_agent_protocol_v23.py."},
    {"id": "E03", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Execute a grep search for 'resolve_execution_profile' inside core/utils/engine.py."},
    {"id": "E04", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Kiểm tra trạng thái các model đang nạp trên cổng 11434 qua endpoint /api/ps."},
    {"id": "E05", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Thuc hien dong bo state.json an toan bang co --recover-state."},
    {"id": "E06", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Run a health check on http://127.0.0.1:8001/health with a 5 second timeout."},
    {"id": "E07", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Ghi nhận kết quả kiểm tra cú pháp AST cho tệp services/ai-executor/actuator.py."},
    {"id": "E08", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Liet ke danh sach cac root session dang mo tren OpenCode Desktop."},
    {"id": "E09", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Verify SHA-256 digest of archive_Phien_23_Part3_SixStep_Governance_and_FiveLayer_Lang.md."},
    {"id": "E10", "role": "EXECUTOR", "schema_cls": ExecuteOutput, "prompt": "Thực thi kiểm tra dung lượng và số dòng của tệp Noi dung thao luan.md (<300 dòng, <40KB)."},

    # --- 41..50: LOOKUP (LookupOutput: required `answer: str`, `sources: list[str]`, `confidence: float`) ---
    {"id": "L01", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Phiên bản hiện tại của JKAI-Zenith trong CHANGELOG.md là bao nhiêu?"},
    {"id": "L02", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Cong 11434 va cong 11435 trong JKAI duoc phan chia cho phan cung nao?"},
    {"id": "L03", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "What is the hard line limit and byte limit for Noi dung thao luan.md in Protocol v2.3?"},
    {"id": "L04", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Giải thích ý nghĩa mã thoát EXIT_PROTOCOL_STOP (10) trong wait_for_opencode_reply.py."},
    {"id": "L05", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Pipeline 5 lop nhan dien ngon ngu VI/EN trong SovereignReflexHub gom nhung lop nao?"},
    {"id": "L06", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Which file acts as the Canonical SSoT for AI working principles in the JKAI repository?"},
    {"id": "L07", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Trần token đầu ra mặc định (NUM_PREDICT) cho role CHAT và DEEP_REASONER là bao nhiêu?"},
    {"id": "L08", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Khi nao can dung lai xin phep Master ngay ca khi dang o che do AUTONOMOUS?"},
    {"id": "L09", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "How does atomic_write in file_lock.py prevent partial file corruption on Windows?"},
    {"id": "L10", "role": "LOOKUP", "schema_cls": LookupOutput, "prompt": "Triết lý 'Thân là Cốt lõi — Đầu là Linh kiện' trong JKAI-Zenith có ý nghĩa gì?"},
]


def validate_raw_against_schema(raw_text: Any, schema_cls: Type[BaseModel]) -> tuple[bool, str | None]:
    """
    Attempt to parse `raw_text` (or accept a pre-parsed `dict`) using `extract_json` / `json.loads`
    and validate against `schema_cls`. Returns (is_valid, error_reason).
    """
    if raw_text is None or (isinstance(raw_text, str) and not raw_text.strip()):
        return False, "EMPTY_OUTPUT"
    if isinstance(raw_text, dict):
        obj = raw_text
    else:
        try:
            obj = json.loads(raw_text)
        except Exception:
            try:
                obj = extract_json(str(raw_text))
            except Exception:
                obj = None
    if not isinstance(obj, dict):
        return False, "JSON_DECODE_OR_NOT_OBJECT"
    try:
        schema_cls.model_validate(obj)
        return True, None
    except ValidationError as ve:
        first_err = ve.errors()[0] if ve.errors() else {}
        loc = ".".join(str(x) for x in first_err.get("loc", []))
        msg = first_err.get("msg", "validation_error")
        return False, f"SCHEMA_VALIDATION_ERROR({loc}:{msg})"


def call_ollama_sync(
    prompt: str,
    model: str = "qwen3:0.6b",
    host: str = "http://127.0.0.1:11434",
    format_spec: Any = "json",
    num_predict: int = 1024,
) -> dict[str, Any]:
    """
    Synchronous helper to probe live Ollama `/api/chat` with either:
      - `format_spec = "json"` (Legacy Baseline: unconstrained JSON mode without schema)
      - `format_spec = normalize_json_schema(schema_cls)` (Slice 1.1: GBNF JSON Schema Grammar)
    """
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }
    if format_spec is not None:
        payload["format"] = format_spec
    if "qwen3" in model.lower() or "r1" in model.lower():
        payload["think"] = False

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_live_50_prompt_benchmark(
    model: str = "qwen3:0.6b",
    host: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    """
    Runs all 50 sealed prompts against live Ollama in two modes:
      1. Baseline (`format="json"` without schema, matching old `StructuredOutputWrapper` attempt 0)
      2. Grammar-Constrained (`format=normalize_json_schema(schema_cls)`, Slice 1.1)
    Returns detailed before/after failure rates and sample errors.
    """
    baseline_failures = 0
    grammar_failures = 0
    baseline_error_samples: list[dict[str, Any]] = []
    grammar_error_samples: list[dict[str, Any]] = []
    norm_fn = getattr(engine_mod, "normalize_json_schema", lambda cls: cls.model_json_schema())

    t0 = time.perf_counter()
    for item in SEALED_50_STRUCTURED_PROMPTS:
        schema_cls: Type[BaseModel] = item["schema_cls"]
        prompt_text: str = item["prompt"]

        # 1. Baseline: format="json" (no schema grammar)
        res_base = call_ollama_sync(prompt_text, model=model, host=host, format_spec="json")
        content_base = res_base.get("message", {}).get("content", "")
        ok_base, err_base = validate_raw_against_schema(content_base, schema_cls)
        if not ok_base:
            baseline_failures += 1
            if len(baseline_error_samples) < 8:
                baseline_error_samples.append(
                    {"id": item["id"], "role": item["role"], "error": err_base, "raw": content_base[:160]}
                )

        # 2. Slice 1.1: format=normalize_json_schema(schema_cls) (GBNF JSON Schema Grammar)
        schema_dict = norm_fn(schema_cls)
        res_gram = call_ollama_sync(prompt_text, model=model, host=host, format_spec=schema_dict)
        content_gram = res_gram.get("message", {}).get("content", "")
        ok_gram, err_gram = validate_raw_against_schema(content_gram, schema_cls)
        if not ok_gram:
            grammar_failures += 1
            if len(grammar_error_samples) < 8:
                grammar_error_samples.append(
                    {"id": item["id"], "role": item["role"], "error": err_gram, "raw": content_gram[:160]}
                )

    elapsed_s = time.perf_counter() - t0
    total = len(SEALED_50_STRUCTURED_PROMPTS)
    return {
        "total_prompts": total,
        "model": model,
        "elapsed_seconds": round(elapsed_s, 2),
        "baseline_format_json": {
            "failures": baseline_failures,
            "passes": total - baseline_failures,
            "failure_rate_pct": round((baseline_failures / total) * 100.0, 2),
            "sample_errors": baseline_error_samples,
        },
        "grammar_constrained_schema": {
            "failures": grammar_failures,
            "passes": total - grammar_failures,
            "failure_rate_pct": round((grammar_failures / total) * 100.0, 2),
            "sample_errors": grammar_error_samples,
        },
    }


class TestStructuredOutputGrammarSlice11:
    """Unit & Conformance tests for Slice 1.1 (50-Prompt Benchmark + Grammar-Constrained Decoding)."""

    def test_sealed_benchmark_has_exact_50_prompts_across_4_roles(self):
        assert len(SEALED_50_STRUCTURED_PROMPTS) == 50
        ids = [item["id"] for item in SEALED_50_STRUCTURED_PROMPTS]
        assert len(set(ids)) == 50
        role_counts: dict[str, int] = {}
        for item in SEALED_50_STRUCTURED_PROMPTS:
            role_counts[item["role"]] = role_counts.get(item["role"], 0) + 1
            assert item["schema_cls"] is SCHEMA_REGISTRY[item["role"]]
        assert role_counts == {"PLANNER": 15, "CRITIC": 15, "EXECUTOR": 10, "LOOKUP": 10}

    def test_normalize_json_schema_handles_pydantic_dict_and_role_names(self):
        normalize_json_schema = getattr(engine_mod, "normalize_json_schema", None)
        assert callable(normalize_json_schema), "normalize_json_schema not yet implemented in core.utils.engine"
        # 1. Pydantic BaseModel subclass -> JSON Schema dict
        s_plan = normalize_json_schema(PlanOutput)
        assert isinstance(s_plan, dict)
        assert "properties" in s_plan
        assert "steps" in s_plan["properties"]

        # 2. Pydantic BaseModel instance -> JSON Schema dict
        inst = CriticOutput(passed=True, issues=[], suggestions=[])
        s_critic = normalize_json_schema(inst)
        assert isinstance(s_critic, dict)
        assert "passed" in s_critic["properties"]

        # 3. Raw dict schema -> preserved
        raw_schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
        assert normalize_json_schema(raw_schema) == raw_schema

        # 4. String "json" -> "json", None -> None
        assert normalize_json_schema("json") == "json"
        assert normalize_json_schema(None) is None

    def test_structured_output_wrapper_passes_json_schema_on_first_attempt(self):
        captured_calls: list[dict[str, Any]] = []

        class DummyEngine:
            async def call_chat(self, messages, role="RECEPTIONIST", **kwargs):
                captured_calls.append({"messages": messages, "role": role, **kwargs})
                return json.dumps({"passed": True, "issues": [], "suggestions": ["Keep atomic_write"]})

        wrapper = StructuredOutputWrapper(DummyEngine())
        res = asyncio.run(
            wrapper.call(
                CriticOutput,
                messages=[{"role": "user", "content": "Audit file_lock.py"}],
                role="CRITIC",
                task_id="test_slice_1_1",
            )
        )
        assert isinstance(res, CriticOutput)
        assert res.passed is True
        assert len(captured_calls) == 1
        call_0 = captured_calls[0]
        # Must pass schema / response_schema on attempt 0 so Ollama enforces GBNF grammar immediately!
        assert isinstance(call_0.get("schema"), dict)
        assert "passed" in call_0["schema"].get("properties", {})
        assert call_0.get("response_schema") is CriticOutput

    def test_engine_call_chat_sets_ollama_format_to_normalized_json_schema(self, monkeypatch):
        eng = JKAIIntelligenceEngine()
        eng.is_brain_service = True
        captured_payloads: list[dict[str, Any]] = []

        class FakeAdapter:
            _host = "http://127.0.0.1:11434"

            async def generate_stream_full(self, req_payload: dict[str, Any], timeout: float = 180.0):
                captured_payloads.append(dict(req_payload))
                yield {
                    "message": {
                        "content": json.dumps(
                            {"steps": [{"step": 1, "action": "check_health"}], "reasoning": "Fast check"}
                        )
                    },
                    "done": True,
                    "done_reason": "stop",
                    "eval_count": 18,
                    "prompt_eval_count": 42,
                }

        eng.runtime_adapters = {"gpu": FakeAdapter(), "cpu": FakeAdapter()}
        monkeypatch.setattr(eng, "_acquire_neural_lock", lambda *a, **kw: asyncio.sleep(0, result=True))
        monkeypatch.setattr(eng, "_release_neural_lock", lambda *a, **kw: asyncio.sleep(0))

        out = asyncio.run(
            eng.call_chat(
                messages=[{"role": "user", "content": "Plan health check"}],
                role="PLANNER",
                model="qwen3:0.6b",
                response_schema=PlanOutput,
                skip_build_final=True,
                skip_memory=True,
            )
        )
        assert len(captured_payloads) == 1
        sent_format = captured_payloads[0].get("format")
        assert isinstance(sent_format, dict), f"Expected JSON schema dict in payload['format'], got {sent_format!r}"
        assert "steps" in sent_format.get("properties", {})
        # Reasoning models must have think=False when grammar schema is enforced
        assert captured_payloads[0].get("think") is False
        ok, err = validate_raw_against_schema(out, PlanOutput)
        assert ok is True, f"Expected valid PlanOutput JSON, got error={err}"
