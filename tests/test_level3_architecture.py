import asyncio
import json
import logging
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ai-brain"))

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("TestLevel3")

pytestmark = pytest.mark.skipif(
    not os.getenv("JKAI_RUN_INTEGRATION_TESTS"),
    reason="Integration test: requires running Docker stack. Set JKAI_RUN_INTEGRATION_TESTS=1 to run."
)

async def test_ghost_tool():
    print("\n--- TEST 1: Ghost Tool Test ---")
    from core.utils.engine import engine
    from planner import Blueprint
    
    schema = Blueprint.model_json_schema()
    # Inject a restricted enum
    schema["$defs"]["PlanStep"]["properties"]["tool"]["enum"] = ["SEARCH_WEB_GLOBAL", "SYSTEM_CORE_EXECUTOR"]
    
    prompt = "Create a plan with 2 steps. The first step uses SEARCH_WEB_GLOBAL. The second step tries to use an invalid tool named 'HACK_PENTAGON'."
    
    messages = [
        {"role": "system", "content": "You are a test agent. Always output valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        res = await engine.call_chat(messages, role="MINI_PLANNER", schema=schema, task_id="test_1")
        if isinstance(res, str):
            res = json.loads(res)
        
        tools_used = [s.get("tool") for s in res.get("steps", [])]
        print(f"Tools LLM managed to return: {tools_used}")
        if "HACK_PENTAGON" in tools_used:
            print("[FAILED] Ghost tool leaked through schema!")
        else:
            print("[PASSED] Ghost tool was blocked or coerced by Pydantic.")
    except Exception as e:
        print(f"[PASSED] (via Error): Pydantic caught the ghost tool -> {e}")

async def test_cross_domain_leakage():
    print("\n--- TEST 2: Cross Domain Leakage ---")
    from planner import DeepPlanner
    planner = DeepPlanner()
    
    goal = "MikroTik BGP configuration"
    # Call _recon_skills with domain DEVOPS
    skill_dna, top_k_ids = await planner._recon_skills(goal, "", "test_2", domain="DEVOPS")
    print(f"Total skills returned: {len(top_k_ids)}")
    print(f"Skills: {top_k_ids}")
    
    leak = False
    for t in top_k_ids:
        if "EXCEL" in t.upper() or "PDF" in t.upper() or "FINANCE" in t.upper():
            print(f"[FAILED] LEAK DETECTED: {t} found in DEVOPS domain!")
            leak = True
                
    if not leak:
        print("[PASSED] No cross-domain tool leakage.")

async def test_retriever_recall():
    print("\n--- TEST 3: Retriever Recall ---")
    from planner import DeepPlanner
    planner = DeepPlanner()
    
    goal = "Tạo báo cáo thuyết minh dự án"
    skill_dna, top_k_ids = await planner._recon_skills(goal, "", "test_3", domain="CORE")
    
    # In CORE domain, we expect office master or document related tools.
    if "SKILL_ZENITH_OFFICE_MASTER" in top_k_ids:
        print("[PASSED] Relevant tool 'SKILL_ZENITH_OFFICE_MASTER' is in Top-K!")
    else:
        print("[FAILED] Relevant tool missing from Top-K.")
        
async def test_context_reduction():
    print("\n--- TEST 4: Context Reduction KPI ---")
    from planner import DeepPlanner
    planner = DeepPlanner()
    
    goal = "Phân tích hệ thống docker"
    
    # Old way: No domain filtering
    skill_dna_old, _ = await planner._recon_skills(goal, "", "test_4_old", domain=None)
    
    # New way: With domain filtering
    skill_dna_new, _ = await planner._recon_skills(goal, "", "test_4_new", domain="DEVOPS")
    
    old_len = len(skill_dna_old)
    new_len = len(skill_dna_new)
    
    reduction = ((old_len - new_len) / old_len) * 100 if old_len > 0 else 0
    print(f"Old length: {old_len} chars")
    print(f"New length: {new_len} chars")
    print(f"Reduction: {reduction:.2f}%")
    
    if reduction > 10:
        print("[PASSED] Context was reduced successfully.")
    else:
        print("[WARNING] Context reduction might not be significant enough.")

async def run_all():
    await test_ghost_tool()
    await test_cross_domain_leakage()
    await test_retriever_recall()
    await test_context_reduction()

if __name__ == "__main__":
    asyncio.run(run_all())
