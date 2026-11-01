# -*- coding: utf-8 -*-
"""
C19 — RAG ingest wiring (fail-first).

Audit findings, all the same failure class as the dead MC proxies:
- `dong_bo_tri_thuc` posted to /ingest/intelligence, which rag-service never exposed.
- `sync_pipeline`'s rag_ingest phase imported `rag.ingest.ingest_cron.run_ingest`;
  ai-brain has no /rag mount and the module defines no such function, so the phase
  could never run — yet the pipeline still counted it as OK.
- rag-service derived Qdrant point ids from Python's `hash()`, which is salted per
  process: every /ingest/scan duplicated the same chunks.

Contract:
1. The skill calls the real /ingest/scan route.
2. The pipeline calls rag-service over HTTP and does not import RAG code.
3. A skipped phase is not reported as OK.
4. Point ids are deterministic across processes.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_SKILL = ROOT / "services" / "tools" / "definitions" / "dong_bo_tri_thuc.py"
SYNC_PIPELINE = ROOT / "core" / "tools" / "sync_pipeline.py"
RAG_IDS = ROOT / "rag" / "ids.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_skill_uses_real_rag_route():
    source = SYNC_SKILL.read_text(encoding="utf-8")
    assert "/ingest/intelligence" not in source, "rag-service has no such route (404)"
    assert "/ingest/scan" in source


def test_pipeline_rag_phase_goes_over_http():
    source = SYNC_PIPELINE.read_text(encoding="utf-8")
    assert "rag.ingest.ingest_cron" not in source, (
        "ai-brain has no /rag mount; importing RAG internals can only fail"
    )
    assert "/ingest/scan" in source


def test_skipped_phase_is_not_counted_as_ok(monkeypatch):
    module = load_module("c19_sync_pipeline", SYNC_PIPELINE)

    async def all_skipped(phase, task_id):
        return {"status": "skipped", "msg": "unavailable"}

    monkeypatch.setattr(module, "_run_phase", all_skipped)
    result = asyncio.run(module.run_sync_pipeline("c19-probe"))
    assert result["total"] == len(module.PHASES)
    assert result["ok"] == 0, "a skipped phase must not inflate the success count"
    assert result["status"] == "partial"

    async def all_ok(phase, task_id):
        return {"status": "ok", "msg": "done"}

    monkeypatch.setattr(module, "_run_phase", all_ok)
    healthy = asyncio.run(module.run_sync_pipeline("c19-probe"))
    assert healthy["ok"] == len(module.PHASES)
    assert healthy["status"] == "ok"


def test_rag_point_ids_are_deterministic():
    module = load_module("c19_rag_ids", RAG_IDS)
    first = module.deterministic_point_id("nội dung", 0)
    second = module.deterministic_point_id("nội dung", 0)
    other_chunk = module.deterministic_point_id("nội dung", 1)
    assert isinstance(first, int) and first > 0
    assert first == second
    assert first != other_chunk


def test_rag_ingest_text_uses_deterministic_ids():
    source = (ROOT / "rag" / "app.py").read_text(encoding="utf-8")
    assert "abs(hash(" not in source, "Python hash() is salted per process; ids must be stable"
    assert "deterministic_point_id" in source
