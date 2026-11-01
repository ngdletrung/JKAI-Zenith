# -*- coding: utf-8 -*-
"""
C12 — Cache writer contract (fail-first).

After C11 moved the embedding cache to a model-qualified SHA-256 key, every
writer must go through the same owner. Mission Control's warmup still wrote
handcrafted md5 keys with its own model and endpoint, so its work was never read.

Corrected design: the service that owns embeddings (ai-brain) warms them;
the dashboard backend must not import the brain dependency stack at all.
"""

from pathlib import Path

import importlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
MC_WARMUP = ROOT / "services" / "mission-control" / "backend" / "mc_core" / "warmup.py"
AI_BRAIN_MAIN = ROOT / "services" / "ai-brain" / "main.py"
EMBED_WARMUP = ROOT / "services" / "ai-brain" / "runtime" / "warmup_manager.py"


def test_mission_control_does_not_own_embedding_warmup():
    source = MC_WARMUP.read_text(encoding="utf-8")
    assert "ks_cache:embed:" not in source, (
        "warmup must not handcraft embedding cache keys; CacheLayer owns the key format"
    )
    assert "EMBED_MODEL" not in source, (
        "warmup must use the resolved embedder model, not its own env var"
    )
    assert "core.utils.embed" not in source, (
        "the dashboard backend must not pull the brain embedding stack"
    )
    assert "_warmup_hot_embeddings" not in source


def test_ai_brain_warms_embeddings_through_shared_embedder(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("ai_brain_warmup_manager", EMBED_WARMUP)
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

    warmed = module.warm_hot_embeddings([str(hot)])

    assert warmed == 1
    assert seen == ["Kiến thức nóng"], "warmup must embed through the shared embedder"


def test_ai_brain_startup_wires_embedding_warmup():
    source = AI_BRAIN_MAIN.read_text(encoding="utf-8")
    assert "warm_hot_embeddings" in source, "ai-brain startup must warm the embedding cache"
