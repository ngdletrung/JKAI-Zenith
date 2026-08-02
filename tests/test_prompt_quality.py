import pytest
import json
import logging
import os

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.getenv("JKAI_RUN_INTEGRATION_TESTS"),
        reason="Integration test: requires running Docker + Ollama. Set JKAI_RUN_INTEGRATION_TESTS=1 to run."
    ),
]

TEST_CASES = [
    {
        "id": "lookup_contract_sysme",
        "goal": "hợp đồng gần đây nhất của Sysme là mua gì ?",
        "role": "PLANNER",
        "expected_keywords": ["hợp đồng", "Sysme"],
        "check_json": False,
    },
    {
        "id": "lookup_quytrinh",
        "goal": "quy trình deploy JKAI là gì ?",
        "role": "RECEPTIONIST",
        "expected_keywords": [],
        "check_json": False,
    },
    {
        "id": "coding_fix_bug",
        "goal": "sửa lỗi 400 khi search Tavily",
        "role": "PLANNER",
        "expected_keywords": [],
        "check_json": False,
    },
    {
        "id": "json_plan_output",
        "goal": "lập kế hoạch kiểm tra hệ thống",
        "role": "PLANNER",
        "expected_keywords": [],
        "check_json": True,
    },
]

@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c["id"])
async def test_prompt_quality(case):
    goal = case["goal"]
    role = case["role"]

    response = await engine.call_chat(
        messages=[{"role": "user", "content": goal}],
        role=role,
        task_id=f"test_{case['id']}",
        json_mode=case["check_json"],
    )

    assert response, f"Empty response for {case['id']}"
    assert len(response) > 10, f"Response too short for {case['id']}: {response}"

    if case["expected_keywords"]:
        for kw in case["expected_keywords"]:
            assert kw.lower() in response.lower(), f"Missing keyword '{kw}' in response for {case['id']}"

    if case["check_json"]:
        try:
            if isinstance(response, str):
                json.loads(response)
            elif isinstance(response, dict):
                pass
            else:
                pytest.fail(f"Expected JSON response, got {type(response)}")
        except (json.JSONDecodeError, ValueError) as e:
            pytest.fail(f"Invalid JSON response for {case['id']}: {e}")

    logger.info(f"[PASS] {case['id']}: {len(response)} chars, role={role}")
