<!-- [ZENITH SOVEREIGN DIRECTIVE] - SINGLE SOURCE OF TRUTH (LEAN & LINKED-ONLY v20.5) -->
# 🧬 JKAI ZENITH: GIAO THỨC PHẦN CỨNG SINGULARITY v20.5 (CORE-DIRECTIVE)

## 🛠️ 1. Resource Strategy
- **CPU**: Intel Xeon E5-2699 v4 (22 Cores / 44 Threads)
- **RAM**: 64GB (High-Cap Reasoning Matrix)
- **GPU**: AMD Radeon RX 6600 (8GB VRAM - Vulkan Native)
- **AI_THREADS**: 20
- **CPU_RESERVE**: 2
- **GUARDIAN_INTERVAL**: 180

---

## 🎚️ 2.5. Neural Hardware Profiles
| Profile Name | num_ctx | num_thread | num_gpu | Temp | repeat_penalty | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MOE_SPLIT_APEX** | 8192 | 20 | 32 | 0.25 | 1.10 | 32 lớp Attention tối đa trong VRAM (~6.5GB VRAM RX 6600), 64GB RAM chuyên gia (Qwen3-30B MoE) |
| **FAST_RESPONSE** | 8192 | 0 | 100 | 0.20 | 1.10 | Nạp VRAM RX 6600 tối ưu tốc độ chớp mắt |
| **RAM_OPTIMIZED** | 8192 | 20 | 0 | 0.10 | 1.10 | 20 Luồng Xeon chuyên sâu quy trình Deep & Phản biện |
| **PREMIUM_RESPONSE** | 8192 | 0 | 100 | 0.10 | 1.10 | Thi công code chính xác trên GPU VRAM |
| **STABLE_SYNC** | 1024 | 0 | 0 | 0.00 | 1.00 | Đồng bộ chỉ mục đệm Embedder CPU/RAM |
| **ULTRA_ART** | 0 | 0 | 100 | 0.00 | 1.00 | Chuyên dụng sinh hình ảnh VRAM |

---

[OLLAMA_ENVIRONMENT]
OLLAMA_KEEP_ALIVE=10m
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
GPU_OLLAMA_NUM_PARALLEL=1
GPU_OLLAMA_MAX_LOADED_MODELS=3
GPU_OLLAMA_GPU_OVERHEAD=536870912
CPU_OLLAMA_NUM_PARALLEL=1
CPU_OLLAMA_MAX_LOADED_MODELS=12
CPU_OLLAMA_NUMA=1
CPU_OLLAMA_NUM_THREAD=20
CPU_OPENBLAS_NUM_THREADS=20
CPU_OMP_NUM_THREADS=20

---

## 🕹️ 3. Active Role Mapping
| Role | Active Model | Hardware | num_ctx | Temp | num_gpu | num_thread | top_p | repeat_penalty | KEEP_ALIVE | Active Profile | Capability | Quality |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RECEPTIONIST** | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.20 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning,tool_use | medium |
| **PLANNER** | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning,planning | high |
| **CRITIC** | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| **EXECUTOR** | qwen2.5-coder:3b | **GPU/VRAM** | 8192 | 0.00 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **EXECUTOR_ALPHA** | qwen2.5-coder:3b | **GPU/VRAM** | 8192 | 0.00 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **EXECUTOR_BETA** | qwen2.5-coder:3b | **GPU/VRAM** | 8192 | 0.00 | 100 | 20 | 0.85 | 1.05 | **-1** | FAST_RESPONSE | coding,tool_use | high |
| **DEEP_REASONER** | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | reasoning | high |
| **SUMMARIZER** | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.10 | 100 | 20 | 0.90 | 1.10 | **-1** | FAST_RESPONSE | general,reasoning,tool_use | medium |
| **EMBEDDER** | nomic-embed-text:latest | **CPU/RAM** | 2048 | 0.00 | 0 | 20 | 1.00 | 1.00 | **-1** | STABLE_SYNC | embedding | medium |
| **GRAPHIC_MASTER** | SDXL-Turbo-ROCm | **GPU/VRAM** | 0 | 0.00 | 100 | 0 | -1 | -1 | **0** | ULTRA_ART | | |
| **VISION** | moondream:latest | **CPU/RAM** | 2048 | 0.10 | 0 | 20 | 0.90 | 1.10 | **0** | RAM_OPTIMIZED | vision | medium |
| **VOICE** | faster-whisper | **CPU/RAM** | 512 | 0.00 | 0 | 0 | 1.00 | 1.00 | **0** | RAM_OPTIMIZED | | |





---

## 🏛️ 4. AMG v2 Dynamic Capability Routing Syntax (`auto`)
- **Explicit Routing**: Đặt tên model cụ thể trong cột `Active Model` (ví dụ `qwen2.5-coder:3b`).
- **Dynamic Auto Routing**: Đặt `auto` trong cột `Active Model` để kích hoạt Adaptive Model Governor (AMG v2).
  - Ví dụ cú pháp: `PLANNER | auto | auto | 8192 | 0.05 | ...`
  - Cột `Capability` (tùy chọn): Định nghĩa yêu cầu nơ-ron: `reasoning`, `coding`, `vision`, `embedding`, `tool_use`.
  - Cột `Quality` (tùy chọn): Mức chất lượng mục tiêu: `low` | `medium` | `high`.
- **Bất biến Kiến trúc (AMG v2 Invariant)**: AMG v2 tự động quét metadata `/api/show`, phân tích `ModelMemoryProfile` (MoE-correct), đo lường `HardwareState` thời gian thực, tính điểm `ModelScore` và xuất `ExecutionProfile` tiêu chuẩn cho Engine mà **không cứng hóa tên model hay kích thước trong code**.

---

## ⚖️ 5. AMG v2 Bootstrap & Infrastructure Constitutional Principles
- **Separation of Planes**:
  - **Infrastructure Plane (`Start_JKAI_Zenith.bat`, `Zenith_Guardian.ps1`)**: Chỉ chịu trách nhiệm kiểm tra môi trường, khởi động Ollama/Docker services, và báo sẵn sàng. **Tuyệt đối không chứa logic chọn model, tên model, hay tham số sinh nơ-ron (`num_gpu`, `num_ctx`, `temperature`, `keep_alive`).**
  - **Decision Plane (`core/runtime/amg_boot.py`, AMG v2)**: Quyết định toàn bộ việc chọn model, định tuyến phần cứng, tính VRAM budget, xuất `ExecutionProfile`, và quản lý Lifecycle (`WARM`, `LAZY`, `EVICTABLE`).
  - **Execution Plane (`Engine`)**: Tiêu thụ `ExecutionProfile` tiêu chuẩn mà không suy luận hay phân nhánh theo tên model.
- **Constitutional Directive**: *"Bootstrapper may start a runtime, but it must never select a model. Model selection and model lifecycle belong exclusively to the Adaptive Model Governor."*

---

## ⚙️ 6. Kiến Trúc Tối Ưu Phần Cứng (NCNN-Inspired Hardware Affinity)
1. **Sovereign Routing (Định tuyến Tuyệt đối)**: Engine định tuyến dựa trên ranh giới vật lý cứng (Hardware Column) thay vì các biến số tùy chọn, đảm bảo GPU và CPU không bao giờ dẫm chân lên nhau.
2. **NUMA-Awareness**: Tôn trọng cấu trúc đa vi xử lý (Xeon E5). Bắt buộc Memory Allocation phải nằm trên cùng một khe cắm (NUMA Node) với luồng thực thi để tránh thắt cổ chai bus (QPI).
3. **Zero-Copy MMAP**: Sử dụng MMAP cho các tầng Model CPU (Q4_K_M) để biến NVMe/RAM thành một bộ đệm liền mạch, triệt tiêu I/O Overhead giống triết lý INT8 của NCNN.
4. **Thread Locking**: Đóng băng số lượng luồng thực thi CPU (20 luồng) để chặn đứng hành vi Context Switching của Hệ điều hành, giữ cache luôn 'nóng' (Hot Cache) trong quá trình nhân ma trận.
5. **Lượng Tử Hóa Activations (KV Cache)**: Bật cờ `OLLAMA_KV_CACHE_TYPE=q8_0` cho toàn bộ hệ thống để ép KV Cache (dữ liệu trung gian của LLM) về định dạng INT8. Giúp Xeon tính toán ma trận trực tiếp INT8 x INT8 -> INT32 bằng tập lệnh AVX2, triệt tiêu Memory Wall và tiết kiệm 50% băng thông RAM/VRAM.
6. **Triệt tiêu Cache Thrashing**: Giới hạn CPU Engine tải tối đa `CPU_OLLAMA_NUM_PARALLEL=1` và `CPU_OLLAMA_MAX_LOADED_MODELS=12`. Đảm bảo luồng xử lý không tranh giành và đẩy bật lẫn nhau ra khỏi bộ nhớ đệm 55MB L3 Cache cực kỳ quý giá của Xeon Broadwell-EP.
7. **Pinning NUMA Node**: Kích hoạt `CPU_OLLAMA_NUMA=1` để khóa luồng thực thi (Threads) và Memory Allocation vào cùng một phân mảnh (Cluster-on-Die / NUMA Node) của Xeon E5. Giảm 30-50% độ trễ QPI (QuickPath Interconnect).

---
*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence.*



