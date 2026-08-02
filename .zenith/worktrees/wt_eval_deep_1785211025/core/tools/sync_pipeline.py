import os
import time
import asyncio
import shutil
import logging
from pathlib import Path

from core.config import settings
from core.utils import path_manager
from core.tools.import_pipeline import _detect_category, SUPPORTED_EXTS, MIN_CONTENT_LEN, CHUNK_SIZE, WIKI_CATEGORIES

logger = logging.getLogger("SYNC_PIPELINE")

PHASES = [
    "migrate",
    "import",
    "assimilate",
    "knowledge_brain",
    "distill",
    "rag_ingest",
    "registry",
    "map_graph",
    "cleanup",
]

MIGRATE_MARKER = ".migrated_done"
OLD_SOURCES = ["knowledge", "vault/01_Knowledge"]


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
    if phase == "migrate":
        return await _run_migrate(task_id)

    if phase == "import":
        from core.tools.import_pipeline import run_import_pipeline
        return await run_import_pipeline(task_id)

    if phase == "assimilate":
        try:
            from skills.CORE.SYNC_KNOWLEDGE_QUANTUM.logic import run_assimilation
            return await run_assimilation(task_id=task_id)
        except Exception as e:
            return {"status": "skipped", "msg": f"Assimilator unavailable: {e}"}

    if phase == "knowledge_brain":
        from core.utils.knowledge_brain import knowledge_brain
        return await knowledge_brain.sync_all(task_id=task_id)

    if phase == "distill":
        try:
            from services.ai_brain.experience_distiller import distiller
            return await distiller.distill(task_id=task_id)
        except Exception as e:
            return {"status": "skipped", "msg": f"Distiller unavailable: {e}"}

    if phase == "rag_ingest":
        try:
            from rag.ingest.ingest_cron import run_ingest
            await run_ingest(task_id=task_id)
            return {"status": "ok", "msg": "RAG ingest triggered"}
        except Exception as e:
            return {"status": "skipped", "msg": f"RAG ingest unavailable: {e}"}

    if phase == "registry":
        from core.utils.skill_deck_index import SkillDeckIndex
        return SkillDeckIndex.get().sync_registry_deck_numbers(write=True)

    if phase == "map_graph":
        try:
            import sys
            from core.utils import path_manager
            root_dir = path_manager.get_root()
            brain_dir = os.path.join(root_dir, "services", "ai-brain")
            if brain_dir not in sys.path:
                sys.path.append(brain_dir)
                
            from knowledge_graph import get_universal_graph
            g = get_universal_graph()
            
            custom_dir = os.path.join(root_dir, "JKAI_MAP")
            
            dirs = [
                os.path.join(root_dir, "core"),
                os.path.join(root_dir, "services"),
                os.path.join(root_dir, "intelligence"),
                os.path.join(root_dir, "scripts")
            ]
            await g.build_and_sync(dirs, obsidian_vault=custom_dir)
            return {"status": "ok", "msg": "Neuron Map (Universal Graph) đồng bộ thành công thưa Master."}
        except Exception as e:
            return {"status": "skipped", "msg": f"Bản đồ Nơ-ron không khả dụng: {e}"}

    if phase == "cleanup":
        return await _flush_caches(task_id)

    return {"status": "error", "msg": f"Unknown phase: {phase}"}


async def _run_migrate(task_id: str) -> dict:
    intel_dir = settings.INTELLIGENCE_DIR or path_manager.get("INTELLIGENCE_DIR") or os.path.join(path_manager.get_root(), "intelligence")
    wiki_dir = os.path.join(intel_dir, "wiki")
    marker = os.path.join(intel_dir, MIGRATE_MARKER)

    if os.path.exists(marker):
        return {"status": "skipped", "msg": "Da migrage tu dot truoc."}

    from core.utils.converter import converter
    from core.utils.engine import engine
    from core.qdrant_client import qdrant_client

    # Dem tong so file de hien thi progress
    total_files = 0
    for src_rel in OLD_SOURCES:
        src_dir = os.path.join(intel_dir, src_rel)
        if os.path.isdir(src_dir):
            for root, _, files in os.walk(src_dir):
                total_files += sum(1 for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS)
    engine.publish_mission_log("MIGRATE", f"Bat dau migrate {total_files} file tu knowledge/vault vao wiki/...", task_id)

    migrated = 0
    skipped = 0
    errors = []
    log_interval = max(1, total_files // 20) if total_files > 0 else 10

    for src_rel in OLD_SOURCES:
        src_dir = os.path.join(intel_dir, src_rel)
        if not os.path.isdir(src_dir):
            skipped += 1
            continue

        for root, _, files in os.walk(src_dir):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXTS:
                    continue
                src_path = os.path.join(root, fname)
                try:
                    content = await converter.to_markdown(src_path, task_id=task_id)
                    if not content or len(content.strip()) < MIN_CONTENT_LEN:
                        continue

                    cat = _detect_category(fname, content)
                    dest_dir = os.path.join(wiki_dir, cat)
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, fname)

                    counter = 1
                    while os.path.exists(dest_path):
                        stem, suffix = os.path.splitext(fname)
                        dest_path = os.path.join(dest_dir, f"{stem}_{counter}{suffix}")
                        counter += 1

                    shutil.move(src_path, dest_path)
                    migrated += 1
                    logger.info(f"[MIGRATE] {fname} -> {cat}/")
                    if migrated % log_interval == 0:
                        engine.publish_mission_log("MIGRATE", f"Da migrate {migrated}/{total_files} file... ({cat}: {fname})", task_id)

                    try:
                        chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
                        embeddings = await asyncio.gather(
                            *[engine.get_embeddings(chunk) for chunk in chunks],
                            return_exceptions=True
                        )
                        collection = "jkai_wiki"
                        try:
                            await qdrant_client.ensure_collection(collection)
                        except Exception:
                            pass
                        for chunk, emb in zip(chunks, embeddings):
                            if isinstance(emb, Exception) or not emb:
                                continue
                            await qdrant_client.upsert_intel(
                                text=chunk,
                                embedding=emb,
                                collection=collection,
                                metadata={"filename": fname, "source": src_path, "migrated": True, "imported_at": time.time(), "task_id": task_id},
                            )
                    except Exception:
                        logger.warning(f"[MIGRATE] Qdrant index failed for {fname}, file copied anyway")
                except Exception as e:
                    errors.append(f"{fname}: {e}")

    try:
        Path(marker).write_text(time.ctime(), encoding="utf-8")
    except Exception:
        pass

    engine.publish_mission_log("MIGRATE", f"Hoan tat migrate {migrated}/{total_files} file vao wiki/.", task_id)
    msg = f"Da migrage {migrated} file tu knowledge/vault vao wiki/."
    if errors:
        msg += f" Loi: {'; '.join(errors[:5])}"
    return {"status": "ok", "migrated": migrated, "errors": errors, "msg": msg}


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
