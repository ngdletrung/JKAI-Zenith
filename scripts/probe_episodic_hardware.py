#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/probe_episodic_hardware.py
Đo đạc độ trễ phần cứng thực tế (Hardware Latency Probe) cho Bộ Não Ngoài:
1. Ollama MiniLM Embedding RTT qua host.docker.internal / 127.0.0.1
2. Qdrant Search RTT qua qdrant:6333 / 127.0.0.1
3. Task Taxonomy Classifier CPU execution time
Xuất kết quả thô ra scripts/probe_hardware_raw_output.json để làm artifact bằng chứng.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error

# Tự động nạp repo root vào sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if "/shared" not in sys.path and os.path.exists("/shared"):
    sys.path.insert(0, "/shared")


def probe_hardware():
    is_docker = os.path.exists('/.dockerenv')
    ollama_host = "http://host.docker.internal:11434" if is_docker else "http://127.0.0.1:11434"
    qdrant_host = "http://qdrant:6333" if is_docker else "http://127.0.0.1:6333"

    sample_prompt = "240 thùng hàng cần chuyển xe tải 30 thùng phí xăng 400k"
    
    # 1. Đo Ollama Embedding RTT
    ollama_latencies = []
    embed_vector = None
    for _ in range(5):
        t0 = time.perf_counter()
        payload = json.dumps({"model": "all-minilm:latest", "prompt": sample_prompt}).encode("utf-8")
        req = urllib.request.Request(
            f"{ollama_host}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                embed_vector = data.get("embedding")
                t_rtt = (time.perf_counter() - t0) * 1000.0
                ollama_latencies.append(t_rtt)
        except Exception as e:
            ollama_latencies.append(-1.0)

    # 2. Đo Qdrant Search RTT
    qdrant_latencies = []
    if embed_vector:
        search_query = {
            "vector": embed_vector,
            "limit": 2,
            "with_payload": True,
            "filter": {"must": [{"key": "task_code", "match": {"value": "OFFICE_DOC"}}]}
        }
        for _ in range(5):
            t0 = time.perf_counter()
            req = urllib.request.Request(
                f"{qdrant_host}/collections/jkai_episodic_memory/points/search",
                data=json.dumps(search_query).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp.read()
                    t_rtt = (time.perf_counter() - t0) * 1000.0
                    qdrant_latencies.append(t_rtt)
            except Exception as e:
                qdrant_latencies.append(-1.0)

    # 3. Đo Task Taxonomy Classifier CPU execution time
    from core.memory.episodic_brain import classify_task
    clf_latencies = []
    test_queries = [
        "Cấu hình DHCP server trên RouterOS MikroTik",
        "Viết controller Spring Boot Java",
        "Sửa script Python và thêm pytest",
        "240 thùng hàng phí xăng hết bao nhiêu",
        "Tạo VLAN 20 trên switch Cisco"
    ]
    for q in test_queries:
        t0 = time.perf_counter()
        code = classify_task(q)
        t_clf = (time.perf_counter() - t0) * 1000.0
        clf_latencies.append({"query": q, "task_code": code, "latency_ms": round(t_clf, 4)})

    valid_ollama = [x for x in ollama_latencies if x > 0]
    valid_qdrant = [x for x in qdrant_latencies if x > 0]

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": "container_ai_brain" if is_docker else "host",
        "ollama_endpoint": ollama_host,
        "qdrant_endpoint": qdrant_host,
        "ollama_rtt_runs_ms": [round(x, 2) for x in ollama_latencies],
        "ollama_rtt_avg_ms": round(sum(valid_ollama) / len(valid_ollama), 2) if valid_ollama else None,
        "qdrant_search_rtt_runs_ms": [round(x, 2) for x in qdrant_latencies],
        "qdrant_search_rtt_avg_ms": round(sum(valid_qdrant) / len(valid_qdrant), 2) if valid_qdrant else None,
        "classifier_runs": clf_latencies,
        "classifier_avg_ms": round(sum([x["latency_ms"] for x in clf_latencies]) / len(clf_latencies), 4)
    }

    out_path = os.path.join(os.path.dirname(__file__), "probe_hardware_raw_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    probe_hardware()
