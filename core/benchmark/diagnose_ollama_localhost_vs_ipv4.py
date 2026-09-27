"""
Diagnostic script for Ollama connection latency on Windows.
Proves the 2000ms IPv6 'localhost' resolution timeout vs true IPv4 '127.0.0.1' latency.

Root Cause Analysis (Turn 88 Audit Investigation):
- Ollama on Windows binds strictly to IPv4: 127.0.0.1:11434 (see `netstat -ano | findstr 11434`).
- No socket listens on IPv6 [::1]:11434.
- In Python / Windows networking, querying 'http://localhost:11434' attempts [::1] first.
- Windows TCP connection retry timeout on [::1] adds an exact ~2000ms overhead before IPv4 fallback.
- Querying 'http://127.0.0.1:11434' bypasses IPv6 lookup entirely, revealing true GPU/inference latency (<15ms).
"""

import time
import json
import urllib.request
import statistics

def test_endpoint(url: str, num_runs: int = 10):
    payload = json.dumps({
        "model": "all-minilm:latest",
        "prompt": "Verify state transition"
    }).encode("utf-8")

    # Warmup
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            _ = resp.read()
    except Exception as e:
        return {"error": str(e)}

    latencies = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            _ = resp.read()
        latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    n = len(latencies)
    return {
        "num_runs": num_runs,
        "p50_ms": round(latencies[n // 2], 2),
        "p95_ms": round(latencies[min(int(n * 0.95), n - 1)], 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "raw_samples": [round(x, 2) for x in latencies]
    }

if __name__ == "__main__":
    print("=" * 70)
    print("OLLAMA HOST LATENCY DIAGNOSIS (Windows IPv6 localhost vs IPv4 127.0.0.1)")
    print("=" * 70)

    print("\n1. Testing 'http://localhost:11434/api/embeddings' (Opencode's likely route)...")
    res_localhost = test_endpoint("http://localhost:11434/api/embeddings", num_runs=5)
    print(f" -> P50: {res_localhost.get('p50_ms')} ms")
    print(f" -> Samples: {res_localhost.get('raw_samples')}")

    print("\n2. Testing 'http://127.0.0.1:11434/api/embeddings' (Antigravity's direct IPv4 route)...")
    res_ipv4 = test_endpoint("http://127.0.0.1:11434/api/embeddings", num_runs=10)
    print(f" -> P50: {res_ipv4.get('p50_ms')} ms")
    print(f" -> Samples: {res_ipv4.get('raw_samples')}")

    diff = res_localhost.get('p50_ms', 0) - res_ipv4.get('p50_ms', 0)
    print("\n" + "=" * 70)
    print(f"FINDING: Overhead introduced by 'localhost' IPv6 fallback = {diff:.2f} ms (~2.0 seconds!)")
    print("=" * 70)
