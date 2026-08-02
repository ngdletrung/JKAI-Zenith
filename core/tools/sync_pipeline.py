import os
import time
import asyncio
import logging

logger = logging.getLogger("SYNC_PIPELINE")

PHASES = [
    "knowledge_sources",
    "assimilate",
    "distill",
    "rag_ingest",
    "registry",
    "cleanup",
]


async def run_sync_pipeline(task_id: str = "sync_pipeline") -> dict:
    phases_results = {}
    total_phases = len(PHASES)
    started_at = time.time()

    for i, phase in enumerate(PHASES):
        try:
            result = await _run_phase(phase, task_id)
            phases_results[phase] = {"status": "ok", "result": result}
        except Exception as e:
            logger.error(f"[PIPELINE-ERR] Phase {phase}: {e}")
            phases_results[phase] = {"status": "error", "error": str(e)}

    elapsed = time.time() - started_at
    ok_count = sum(1 for v in phases_results.values() if v["status"] == "ok")
    return {
        "status": "ok" if ok_count == total_phases else "partial",
        "phases": phases_results,
        "ok": ok_count,
        "total": total_phases,
        "elapsed": f"{elapsed:.1f}s",
        "msg": f"Sync pipeline: {ok_count}/{total_phases} phases OK in {elapsed:.1f}s",
    }


async def _run_phase(phase: str, task_id: str) -> dict:
    if phase == "knowledge_sources":
        try:
            from core.knowledge_sources.manager import knowledge_sources
            return await knowledge_sources.sync_all(task_id=task_id)
        except Exception as e:
            return {"status": "skipped", "msg": f"KnowledgeSources pipeline unavailable: {e}"}

    if phase == "assimilate":
        try:
            from skills.CORE.SYNC_KNOWLEDGE_QUANTUM.logic import run_assimilation
            return await run_assimilation(task_id=task_id)
        except Exception as e:
            return {"status": "skipped", "msg": f"Assimilator unavailable: {e}"}

    if phase == "distill":
        try:
            import sys, os
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            brain_path = os.path.join(root_dir, "services", "ai-brain")
            if brain_path not in sys.path:
                sys.path.insert(0, brain_path)
            
            from experience_distiller import distiller
            return await distiller.distill(task_id=task_id)
        except Exception as e:
            return {"status": "skipped", "msg": f"Distiller unavailable: {e}"}

    if phase == "rag_ingest":
        try:
            import sys, os
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
                
            from rag.ingest.ingest_cron import run_ingest
            await run_ingest(task_id=task_id)
            return {"status": "ok", "msg": "RAG ingest triggered"}
        except Exception as e:
            return {"status": "skipped", "msg": f"RAG ingest unavailable: {e}"}

    if phase == "registry":
        from core.utils.skill_deck_index import SkillDeckIndex
        return SkillDeckIndex.get().sync_registry_deck_numbers(write=True)

    if phase == "cleanup":
        return await _flush_caches(task_id)

    return {"status": "error", "msg": f"Unknown phase: {phase}"}


async def _flush_caches(task_id: str) -> dict:
    flushed = []
    try:
        from core.utils.engine import engine
        redis = engine._get_redis()
        count = 0
        for key in redis.scan_iter(match="brain_cache:*"):
            redis.delete(key)
            count += 1
        flushed.append(f"redis: {count} keys")
    except Exception as e:
        flushed.append(f"redis: {e}")

    try:
        import gc
        gc.collect()
        flushed.append("gc: ok")
    except Exception as e:
        flushed.append(f"gc: {e}")

    return {"status": "ok", "msg": "; ".join(flushed)}
