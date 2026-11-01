# -*- coding: utf-8 -*-
"""
C13 — Warmup ownership and honest reporting (fail-first).

Evidence that motivated this:
- Mission Control warmup wrote `ks_cache:file:*` keys that no code ever reads,
  using `/workspace/intelligence/...` paths that do not exist in its container.
- Its log claimed "Pre-cached 5 hot files" regardless of how many were cached.
- The dashboard's Warmup button posts to `${AI_BRAIN_URL}/warmup`, a route
  ai-brain never exposed, so it could only ever fail (or time out after 5s).

Contract:
1. Warmup lives in ai-brain, one module for hot-path resolution and priming.
2. ai-brain exposes POST /warmup and reports the real number of warmed files.
3. Mission Control keeps no dead warmup paths or raw cache writes.
4. Mission Control's proxy surfaces the real count instead of a canned success.
"""

from pathlib import Path

import importlib

ROOT = Path(__file__).resolve().parents[1]
MC_WARMUP = ROOT / "services" / "mission-control" / "backend" / "mc_core" / "warmup.py"
MC_MAIN = ROOT / "services" / "mission-control" / "backend" / "main.py"
AI_BRAIN_MAIN = ROOT / "services" / "ai-brain" / "main.py"
WARMUP_MANAGER = ROOT / "services" / "ai-brain" / "runtime" / "warmup_manager.py"


def test_mission_control_keeps_no_dead_warmup():
    source = MC_WARMUP.read_text(encoding="utf-8")
    assert "ks_cache:file:" not in source, "no reader exists for these keys; stop writing them"
    assert "/workspace/intelligence" not in source, "path does not exist in the MC container"
    assert "00_Import" not in source, "Import zone lives in ai-brain, not Mission Control"


def test_warmup_manager_primes_shared_embedding_cache(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("ai_brain_warmup_manager", WARMUP_MANAGER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    hot = tmp_path / "hot.md"
    hot.write_text("Kiến thức nóng", encoding="utf-8")

    seen = []

    def fake_embed(text):
        seen.append(text)
        return [0.1, 0.2]

    import core.utils.embed as embed_mod
    monkeypatch.setattr(embed_mod, "embed", fake_embed)

    assert module.warm_hot_embeddings([str(hot)]) == 1
    assert seen == ["Kiến thức nóng"]


def test_ai_brain_exposes_warmup_route():
    source = AI_BRAIN_MAIN.read_text(encoding="utf-8")
    assert "'/warmup'" in source or '"/warmup"' in source
    assert "warm_hot_embeddings" in source


def test_mission_control_proxy_reports_real_count():
    source = MC_MAIN.read_text(encoding="utf-8")
    assert "/warmup" in source
    assert "warmed" in source, "proxy must report how many files ai-brain warmed"
