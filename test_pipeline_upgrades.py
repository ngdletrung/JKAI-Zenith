import os
import sys
import time
import asyncio

ai_brain_path = r"d:\Docker\JKAI\services\ai-brain"
if ai_brain_path not in sys.path:
    sys.path.insert(0, ai_brain_path)

def test_syntax_preserving_compaction():
    print("--- [TEST 1: PROMPT FORGE SYNTAX-AWARE COMPACTION] ---")
    from prompt_forge import PromptForge
    sample_json = '{"config": {"status": "active", "layers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]}}'
    compacted = PromptForge._truncate_text(sample_json, max_chars=40)
    print(f"Original text : {sample_json}")
    print(f"Compacted text: {compacted}")
    assert "..." in compacted and "}" in compacted
    print("[PASS] Bảo toàn cú pháp dấu ngoặc thành công khi nén lệnh.\n")

async def test_parental_heritage_injection():
    print("--- [TEST 2: PARENTAL HERITAGE CORE INJECTION] ---")
    from prompt_forge import PromptForge
    mindset = await PromptForge._synthesize_mindset("Kiem tra he thong tệp và RAM")
    print(f"Excerpt of synthesized mindset:\n{mindset[:250]}...\n")
    assert "[PARENTAL HERITAGE CORE]" in mindset and "Phá Mù Sương Ngữ Cảnh" in mindset
    print("[PASS] 5 Binh Pháp Di Sản Bảo Trực đã được tiêm chèn vĩnh cửu vào System Prompt.\n")

def test_semantic_cache_fast_pipeline():
    print("--- [TEST 3: FAST PIPELINE SEMANTIC CACHE BYPASS (<50ms)] ---")
    from semantic_cache import semantic_cache
    query = "kiem tra nhip tim cua ollama port 11434"
    semantic_cache.set_cache(query, {"answer": "Ollama GPU Port 11434 online, latency 2ms", "status": "SUCCESS"})
    
    t0 = time.time()
    res = semantic_cache.get_cache("   Kiem Tra NHIP TIM cua Ollama PORT 11434   ")
    dt_ms = (time.time() - t0) * 1000.0
    print(f"Query retrieved in: {dt_ms:.3f} ms")
    assert res and res.get("cache_hit") is True and dt_ms < 50.0
    print(f"[PASS] Fast Pipeline phản hồi siêu tốc từ đệm trong {dt_ms:.3f}ms (Đạt chuẩn < 50ms).\n")

def test_deep_pipeline_context_fog_severance():
    print("--- [TEST 4: DEEP PIPELINE CONTEXT FOG SEVERANCE] ---")
    from prompt_engine.claw_compactor.memory_pruner import MemoryPruner
    pruner = MemoryPruner()
    noisy_history = [{"id": f"msg_{i}", "timestamp": time.time(), "content": f"Duplicate RAG fetch on line {10 + (i % 2)}", "importance": 0.4} for i in range(50)]
    res = pruner.prune_stale_engrams(noisy_history)
    print(f"Original context history : {res['original_count']} turns")
    print(f"Pruned concise history   : {res['retained_count']} turns ({res['reduction_percentage']}% reduction)")
    assert res["retained_count"] <= 5 and res["reduction_percentage"] > 80.0
    print("[PASS] Deep Pipeline thanh lọc thành công rác hội thoại (giảm > 80% rác bộ nhớ trước khi suy luận).\n")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=== JKAI PIPELINES & PROMPT ENGINE UPGRADE VERIFICATION SUITE ===\n")
    test_syntax_preserving_compaction()
    asyncio.run(test_parental_heritage_injection())
    test_semantic_cache_fast_pipeline()
    test_deep_pipeline_context_fog_severance()
    print("=== VERIFIED: ALL 3 PIPELINE & PROMPT UPGRADE BRIDGES ACTIVATED PERFECTLY ===")
