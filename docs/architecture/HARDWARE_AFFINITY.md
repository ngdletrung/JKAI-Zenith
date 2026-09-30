# ⚙️ JKAI Zenith: Hardware Affinity & Low-Latency Execution Architecture
**Specification: NCNN-Inspired Hardware Affinity & Substrate Resource Acceleration**  
*Author: Master LeeTrung | Engineering: JKAI Sovereign Core*

---

## 1. Physical Hardware Matrix
JKAI Zenith is engineered to run on asymmetric consumer-grade/workstation hardware with zero cloud dependencies:

| Component | Physical Specification | Workload Allocation | Affinity Configuration |
|:---|:---|:---|:---|
| **CPU** | Intel Xeon E5-2699 v4 (22 Cores / 44 Threads, 55MB L3 Cache) | Heavy reasoning models, background DAG execution, embeddings | `num_thread=20`, NUMA Node 0/1 pinned, AVX2 vectorization |
| **System RAM** | 64GB DDR4 ECC Quad-Channel | Model weights memory (CPU offloading), KV-cache, Qdrant in-memory vector index | Zero-copy MMAP backing |
| **GPU** | AMD Radeon RX 6600 (8GB GDDR6 VRAM, PCIe 4.0 x8) | Fast Receptionist, Vision, VLM screenshot OCR, Code Executor | Vulkan/ROCm runtime, `num_gpu=100` for active role, 32 Attention layers capped |
| **Storage** | NVMe SSD PCIe Gen3/Gen4 | Event Sourcing SQLite/JSONL, Model checkpoints, Checksum journal | Direct unbuffered I/O |

---

## 2. NCNN-Inspired Hardware Principles

### 2.1. Sovereign Routing (Định tuyến Tuyệt đối)
The engine routes queries based on rigid physical boundaries (Hardware Columns) rather than optional soft variables. GPU and CPU workloads are strictly segmented:
- **GPU Column**: Sub-second fast reactive queries, small-context tool calling, vision perception.
- **CPU Column**: Large-context multi-step reasoning, offline code refactoring, background distillation.

### 2.2. NUMA-Aware Memory Pinning
In multi-socket / multi-cluster Xeon E5 systems, memory latency across the QPI (QuickPath Interconnect) bus degrades throughput by 30–50%.
- `CPU_OLLAMA_NUMA=1`: Forces memory allocation and thread affinity to reside on the same Cluster-on-Die / NUMA node.
- Context switching overhead is strictly minimized.

### 2.3. Zero-Copy MMAP Backing
CPU-offloaded models (such as `Q4_K_M` quantizations) utilize memory-mapped file I/O (`mmap=True`). NVMe storage and RAM form a contiguous unified buffer, eliminating user-space memory duplication and reducing cold-boot latency to near zero.

### 2.4. Thread Locking (Thread Affinitization)
By locking active worker threads (`CPU_OLLAMA_NUM_THREAD=20`) and reserving 2 cores for Host OS / Guardian background telemetry (`CPU_RESERVE=2`), CPU thread thrashing is eliminated, maintaining a "hot" L1/L2/L3 cache state during intensive GEMM (General Matrix Multiply) operations.

---

## 3. INT8 Quantization & L3 Cache Optimization

### 3.1. INT8 KV Cache (`OLLAMA_KV_CACHE_TYPE=q8_0`)
- Activations and key-value cache states are quantized to 8-bit integers (`q8_0`).
- Enables AVX2 fused multiply-add directly on integer representations (INT8 x INT8 $\to$ INT32), bypassing the memory wall and saving ~50% RAM/VRAM bandwidth with negligible precision degradation.

### 3.2. Cache Thrashing Prevention
- Xeon Broadwell-EP contains 55MB of shared L3 cache.
- Hard limit on concurrent CPU models: `CPU_OLLAMA_NUM_PARALLEL=1`, `CPU_OLLAMA_MAX_LOADED_MODELS=12`.
- Prevents multiple heavy threads from evicting each other's weights from the cache line.

---

## 4. Hardware Telemetry & Heartbeat Monitoring
The `Zenith_Guardian.ps1` daemon monitors resource pressure every 180 seconds (`GUARDIAN_INTERVAL=180`):
- VRAM usage $> 90\%$ triggers automatic eviction of idle non-resident models.
- VRAM fragmentation triggers graceful worker restart (`stop-process -name ollama* -force`) followed by immediate memory re-allocation with zero state loss.
