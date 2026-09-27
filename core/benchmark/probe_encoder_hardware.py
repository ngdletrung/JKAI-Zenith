"""
Hardware Encoder Latency Probe for JKAI Sovereign Runtime.
Empirically measures in-process CPU inference latency and memory (RSS)
on Master's host machine (Intel Xeon E5-2699 v4 / PyTorch CPU).

Artifact requirement per Red Team Auditor Turn 84:
All latency claims must be reproducible via committed scripts and raw outputs.
"""

import os
import sys
import json
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import torch
    from transformers import BertConfig, BertModel
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def measure_model_latency(
    model: Any,
    dummy_input: Any,
    num_warmup: int = 5,
    num_runs: int = 50
) -> Dict[str, Any]:
    """Measures latency percentiles and memory delta for a PyTorch module."""
    if not TORCH_AVAILABLE:
        return {"error": "PyTorch not installed"}

    model.eval()

    # Warmup
    for _ in range(num_warmup):
        with torch.no_grad():
            _ = model(dummy_input)

    latencies: List[float] = []
    p = psutil.Process() if PSUTIL_AVAILABLE else None
    rss_before = (p.memory_info().rss / (1024 * 1024)) if p else 0.0

    for _ in range(num_runs):
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = model(dummy_input)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    rss_after = (p.memory_info().rss / (1024 * 1024)) if p else 0.0
    latencies.sort()

    n = len(latencies)
    p50 = latencies[n // 2]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    p99 = latencies[min(int(n * 0.99), n - 1)]

    return {
        "num_runs": num_runs,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "rss_before_mb": round(rss_before, 2),
        "rss_after_mb": round(rss_after, 2),
        "rss_delta_mb": round(rss_after - rss_before, 2),
    }


def run_hardware_probe(output_file: str = "core/benchmark/probe_hardware_raw_output.json") -> Dict[str, Any]:
    """Runs the complete hardware probe suite and saves raw JSON output."""
    system_env = {
        "python_version": sys.version,
        "torch_version": getattr(torch, "__version__", "N/A") if TORCH_AVAILABLE else "N/A",
        "torch_cuda_available": torch.cuda.is_available() if TORCH_AVAILABLE else False,
        "torch_num_threads": torch.get_num_threads() if TORCH_AVAILABLE else 0,
        "platform": sys.platform
    }

    results: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system_env": system_env,
        "benchmarks": {}
    }

    if not TORCH_AVAILABLE:
        print("[ERROR] Torch not available for hardware probe")
        return results

    # 1. Compact Encoder (~12M params: 4 layers, 256 hidden, 4 heads)
    print("Evaluating Compact Encoder (~12M params, seq=64)...")
    cfg_compact = BertConfig(vocab_size=30522, hidden_size=256, num_hidden_layers=4, num_attention_heads=4)
    model_compact = BertModel(cfg_compact)
    input_compact = torch.randint(0, 1000, (1, 64))
    res_compact = measure_model_latency(model_compact, input_compact, num_warmup=5, num_runs=50)
    results["benchmarks"]["compact_encoder_12m"] = {
        "params": "~12M (4L, 256H, 4A)",
        "seq_len": 64,
        "metrics": res_compact
    }

    # 2. Base Encoder (~110M params: 12 layers, 768 hidden, 12 heads)
    print("Evaluating Base Encoder (~110M params, seq=128)...")
    cfg_base = BertConfig(vocab_size=30522, hidden_size=768, num_hidden_layers=12, num_attention_heads=12)
    model_base = BertModel(cfg_base)
    input_base = torch.randint(0, 1000, (1, 128))
    res_base = measure_model_latency(model_base, input_base, num_warmup=5, num_runs=30)
    results["benchmarks"]["base_encoder_110m"] = {
        "params": "~110M (12L, 768H, 12A)",
        "seq_len": 128,
        "metrics": res_base
    }

    # 3. ModernBERT-Large declaration
    results["benchmarks"]["modernbert_large_395m"] = {
        "params": "~395M",
        "status": "UNMEASURED",
        "note": "Per Red Team Turn 84: No linear extrapolation accepted. Requires physical checkpoint on target device."
    }

    # Write raw output
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Hardware probe raw artifact saved to '{out_path}'")
    return results


if __name__ == "__main__":
    run_hardware_probe()
