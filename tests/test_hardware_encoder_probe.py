"""
Test suite for Hardware Encoder Probe and Reproducible Artifacts.
Verifies compliance with Red Team Turn 84 audit mandates:
1. Probe raw artifact exists and contains reproducible measurements.
2. Compact encoder meets CPU latency envelope (P50 < 50ms).
3. ModernBERT-Large 395M is honestly declared UNMEASURED without linear extrapolation.
"""

import json
from pathlib import Path
import pytest


def test_probe_raw_artifact_exists_and_valid():
    artifact_path = Path("core/benchmark/probe_hardware_raw_output.json")
    assert artifact_path.exists(), "Hardware probe raw artifact must exist and be committed"
    
    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "system_env" in data
    assert "benchmarks" in data
    benchmarks = data["benchmarks"]
    
    assert "compact_encoder_12m" in benchmarks
    assert "base_encoder_110m" in benchmarks
    assert "modernbert_large_395m" in benchmarks


def test_compact_encoder_cpu_latency_envelope():
    artifact_path = Path("core/benchmark/probe_hardware_raw_output.json")
    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    compact = data["benchmarks"]["compact_encoder_12m"]
    metrics = compact["metrics"]
    
    # Assert CPU latency is within plausible bounds (<50ms for 12M on modern CPU)
    assert metrics["p50_ms"] < 50.0, f"Compact encoder P50 too high: {metrics['p50_ms']}ms"
    assert metrics["p95_ms"] < 80.0, f"Compact encoder P95 too high: {metrics['p95_ms']}ms"
    assert metrics["num_runs"] >= 30


def test_modernbert_large_is_honestly_unmeasured():
    artifact_path = Path("core/benchmark/probe_hardware_raw_output.json")
    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    m395 = data["benchmarks"]["modernbert_large_395m"]
    assert m395["status"] == "UNMEASURED", "395M model must be declared UNMEASURED until physical checkpoint is loaded"
    assert "p50_ms" not in m395, "Must not contain invented or extrapolated latency figures"
