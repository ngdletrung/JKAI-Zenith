<!-- [ZENITH SOVEREIGN DIRECTIVE] - SINGLE SOURCE OF TRUTH (LEAN & LINKED-ONLY v20.5) -->
# 🧬 JKAI ZENITH: GIAO THỨC PHẦN CỨNG SINGULARITY v20.5 (CORE-DIRECTIVE)

## 🛠️ 1. Resource Strategy
- **CPU**: Intel Xeon E5-2699 v4 (22 Cores / 44 Threads)
- **RAM**: 128GB (High-Cap Reasoning Matrix)
- **GPU**: AMD Radeon RX 6600 (8GB VRAM - Vulkan Native)
- **AI_THREADS**: 20
- **CPU_RESERVE**: 2
- **GUARDIAN_INTERVAL**: 180

---

## 🎚️ 2.5. Neural Hardware Profiles
| Profile Name | num_ctx | num_thread | num_gpu | Temp | repeat_penalty | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MOE_SPLIT_APEX** | 8192 | 20 | 20 | 0.25 | 1.10 | 20 lớp Attention trong VRAM, 128GB RAM chuyên gia (Qwen3-30B MoE) |
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
GPU_OLLAMA_NUM_PARALLEL=2
GPU_OLLAMA_MAX_LOADED_MODELS=5
GPU_OLLAMA_GPU_OVERHEAD=536870912
CPU_OLLAMA_NUM_PARALLEL=2
CPU_OLLAMA_MAX_LOADED_MODELS=12
CPU_OLLAMA_NUMA=1
CPU_OLLAMA_NUM_THREAD=20
CPU_OPENBLAS_NUM_THREADS=20
CPU_OMP_NUM_THREADS=20

---

## 🕹️ 3. Active Role Mapping
| Role | Active Model | Hardware | num_ctx | Temp | num_gpu | num_thread | top_p | repeat_penalty | KEEP_ALIVE | Active Profile |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| RECEPTIONIST | hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:UD-Q4_K_XL | **GPU/RAM (MoE)** | 8192 | 0.25 | 20 | 20 | 0.90 | 1.10 | **-1** | MOE_SPLIT_APEX |
| PLANNER | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.05 | 100 | 0 | 0.90 | 1.05 | **0** | PREMIUM_RESPONSE |
| EXECUTOR | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.05 | 100 | 0 | 0.85 | 1.05 | **0** | PREMIUM_RESPONSE |
| EXECUTOR_ALPHA | qwen2.5-coder:3b | **CPU/RAM** | 8192 | 0.00 | 0 | 20 | 0.85 | 1.05 | **0** | RAM_OPTIMIZED |
| EXECUTOR_BETA | qwen3.5:4b | **GPU/VRAM** | 8192 | 0.20 | 100 | 0 | 0.90 | 1.10 | **0** | FAST_RESPONSE |
| CRITIC | hf.co/bartowski/google_gemma-4-E2B-it-GGUF:Q4_K_M | **GPU/VRAM** | 8192 | 0.10 | 100 | 20 | 0.90 | 1.10 | **0** | RAM_OPTIMIZED |
| SUMMARIZER | hf.co/bartowski/google_gemma-4-E2B-it-GGUF:Q4_K_M | **GPU/VRAM** | 8192 | 0.10 | 100 | 20 | 0.90 | 1.10 | **0** | RAM_OPTIMIZED |
| EMBEDDER | nomic-embed-text:latest | **CPU/RAM** | 1024 | 0.00 | 0 | 20 | 1.00 | 1.00 | **-1** | STABLE_SYNC |
| GRAPHIC_MASTER | SDXL-Turbo-ROCm | **GPU/VRAM** | 0 | 0.00 | 100 | 0 | -1 | -1 | **0** | ULTRA_ART |
| VISION | moondream:latest | **CPU/RAM** | 2048 | 0.10 | 0 | 20 | 0.90 | 1.10 | **0** | RAM_OPTIMIZED |
| VOICE | faster-whisper | **CPU/RAM** | 512 | 0.00 | 0 | 0 | 1.00 | 1.00 | **0** | RAM_OPTIMIZED |

---
*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence.*
