# 🧬 JKAI ZENITH: GIAO THỨC PHẦN CỨNG SINGULARITY v1.0 (CORE-DIRECTIVE)
> "Phần cứng là thân thể, Phần mềm là linh hồn, Singularity là sự Nhất thể."

## 🛠️ 1. Resource Strategy (ROCm & Xeon Optimization)
- **CPU**: Intel Xeon E5-2699 v4 (22 Cores / 44 Threads)
- **RAM**: 128GB (High-Cap Reasoning Matrix)
- **GPU**: AMD Radeon RX 6600 (8GB VRAM - ROCm Native)
- **AI_THREADS**: 22 (Giới hạn tài nguyên thực thi AI)
- **CPU_RESERVE**: 4 (Dự phòng cho Tổng Giám Đốc và hệ điều hành)
- **GUARDIAN_INTERVAL**: 180 (Tần suất quét sức khỏe hệ thống - giây)
- **Strategy**: 
     - **Proactive Pulse**: Hệ thống Watchdog tự động quét tài nguyên và tự giải phóng VRAM khi phát hiện chồng lấn.

---

## 🏛️ 2. Model Tier Registry (Elite Tier)
> [!IMPORTANT]
> Đây là danh sách các mô hình "Elite" được ưu tiên nạp sẵn để duy trì sự ổn định của hệ thống.

| Model Name | Memory | Context | Temp | GPU Offload | top_p | repeat_penalty | Status | Target Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **qwen3.5:latest** | 6.6 GB | 8192 | 0.4 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | RESERVE AGENTS |
| **phi4-mini:latest** | 2.5 GB | 8192 | 0.3 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | SUMMARIZER |
| **deepseek-r1:latest** | 5.2 GB | 8192 | 0.0 | **100%** | 0.9 | 1.1 | **GPU/VRAM** | UNIFIED SOVEREIGN |
| **gemma4:latest** | 9.6 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | SUPREME CRITIC |
| **qwen2.5:1.5b** | 986 MB | 4096 | 0.2 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | DATA SCOUT |
| **moondream:latest** | 1.7 GB | 2048 | 0.2 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | NEURAL EYE |
| **gemini-3.5-flash** | Cloud | 1048576 | 0.4 | **OFFLINE** | 0.9 | 1.1 | **CLOUD** | CLOUD LONG CONTEXT |
| **claude-3-5-sonnet** | Cloud | 2000000 | 0.5 | **OFFLINE** | 0.9 | 1.1 | **CLOUD** | CLOUD COGNITIVE |

---

## 📦 2.1. Tổng Giám Đốc Model Library (Full Inventory)
> [!CAUTION]
> **TUYỆT ĐỐI KHÔNG XÓA MODEL.** Đây là kho lưu trữ tri thức hệ thống. Chỉ được phép hiệu chỉnh thông số hoặc bổ sung model mới. Mọi hành động xóa model sẽ bị ghi nhận vào Nhật ký Sự cố.

| Model Name | Memory | Context | Temp | GPU Offload | top_p | repeat_penalty | Status | Target Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **llama3.1:8b** | 4.9 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | GENERAL_PURPOSE |
| **granite4:tiny-h** | 4.2 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | RESEARCH_MINI |
| **qwen2.5-coder:14b** | 9.0 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | CODE_EXPERT |
| **qwen2.5:0.5b** | 397 MB | 4096 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | FAST_HELPER |
| **moondream:latest** | 1.7 GB | 2048 | 0.2 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | NEURAL EYE |
| **nomic-embed-text:latest** | 274 MB | 2048 | 0.0 | **GPU/VRAM** | 1.0 | 1.0 | **ONLINE** | EMBEDDER |
| **all-minilm:latest** | 45 MB | 2048 | 0.0 | **OFFLINE** | 1.0 | 1.0 | **CPU/RAM** | EMBEDDER_MINI |
| **gemma4:e2b** | 7.2 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | REASONING_LITE |
| **granite-code:3b** | 2.0 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | CODE_LITE |
| **qwen2.5:1.5b** | 986 MB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | FAST_RESPONSE |
| **qwen3.5:0.8b** | 1.0 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | FAST_RESPONSE |
| **lfm2.5-thinking:1.2b** | 731 MB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | THINKING_LITE |
| **phi4-mini:latest** | 2.5 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | SUMMARIZER |
| **gemma4:latest** | 9.6 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | SUPREME CRITIC |
| **gemma4-opt:latest** | 9.6 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | STRICT_CRITIC |
| **deepseek-r1-32b-opt:latest** | 19 GB | 16384 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | SUPREME STRATEGIST |
| **qwen25-coder-14b-opt:latest** | 9.0 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | CODE_EXPERT |
| **qwen3.5:latest** | 6.6 GB | 8192 | 0.4 | **ONLINE** | 0.9 | 1.1 | **GPU/VRAM** | PRIMARY EXECUTOR |
| **deepseek-r1:latest** | 5.2 GB | 8192 | 0.0 | **ONLINE** | 0.9 | 1.1 | **GPU/VRAM** | REASONING_EXPERT |
| **Qwen3:8b** | 5.2 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | GENERAL_PURPOSE |
| **mistral-nemo:latest** | 7.1 GB | 8192 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | GENERAL_PURPOSE |
| **deepseek-r1:32b** | 19 GB | 16384 | 0.0 | **OFFLINE** | 0.9 | 1.1 | **CPU/RAM** | SUPREME STRATEGIST |
| **gemini-3.5-flash** | Cloud | 1048576 | 0.4 | **OFFLINE** | 0.9 | 1.1 | **CLOUD** | CLOUD LONG CONTEXT |
| **claude-3-5-sonnet** | Cloud | 2000000 | 0.5 | **OFFLINE** | 0.9 | 1.1 | **CLOUD** | CLOUD COGNITIVE |
| **gpt-4o** | Cloud | 128000 | 0.5 | **OFFLINE** | 0.9 | 1.1 | **CLOUD** | CLOUD GENERALIST |
| **deepseek-chat** | Cloud | 64000 | 0.2 | **OFFLINE** | 0.9 | 1.1 | **CLOUD** | CLOUD REASONER |

---

## 🎚️ 2.5. Neural Hardware Profiles (Preset Registry)
> [!TIP]
> Các Profile này định nghĩa "phong cách" sử dụng phần cứng. Hệ thống sẽ ưu tiên thông số trong bảng Mapping, nếu để "Profile" thì sẽ lấy theo Preset tại đây .

| Profile Name | num_ctx | num_thread | num_gpu | Temp | repeat_penalty | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PREMIUM_RESPONSE** | 8192 | 0 | 100 | 0.4 | 1.2 | Độ chính xác cao, GPU Native |
| **FAST_RESPONSE** | 4096 | 0 | 100 | 0.7 | 1.1 | Phản hồi siêu tốc, GPU Offload |
| **ELITE_REASONING** | 8192 | 0 | 100 | 0.0 | 1.1 | Tư duy sâu, GPU cực đại |
| **STABLE_SYNC** | 2048 | 4 | 100 | 0.0 | 1.0 | Ổn định, tiết kiệm tài nguyên |
| **ULTRA_ART** | 0 | 0 | 100 | 0.0 | 1.0 | Chuyên dụng hình ảnh |
| **OFFLINE_RESERVE** | 2048 | 14 | 0 | 0.2 | 1.1 | Dự phòng CPU |
| **GLOBAL_FLUID** | 8192 | 0 | 100 | 0.3 | 1.1 | Chuyển ngữ GPU Optimization |
| **UNIFIED_ELITE** | 8192 | 14 | 0 | 0.3 | 1.1 | Tổng hợp đa tầng |
| **STRICT_CRITIC** | 8192 | 14 | 0 | 0.0 | 1.1 | Phản biện logic |
| **RAM_OPTIMIZED** | 8192 | 8 | 0 | 0.3 | 1.1 | Tối ưu hóa cho CPU/RAM |
| **REFLEX_GALAXY** | 4096 | 0 | 100 | 0.1 | 1.1 | Phản xạ nhanh, GPU |

---

## 🕹️ 3. Active Role Mapping (NGUỒN TRI THỨC DUY NHẤT)

> CRITICAL: engine.py tim chinh xac chuoi "3. Active Role Mapping" de bat dau parse bang nay (engine.py dong 395).
> Moi thay doi ten section phai dong bo voi engine.py.

| Role | Active Model | Hardware | num_ctx | Temp | num_gpu | top_p | repeat_penalty | KEEP_ALIVE | Active Profile | num_thread |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| EMBEDDER | nomic-embed-text:latest | **GPU/VRAM** | 1024 | 0.0 | 100 | 1.0 | 1.0 | **-1** | STABLE_SYNC | 0 |
| RECEPTIONIST | qwen3:4b  | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| CHAT | qwen3:4b  | **CPU/RAM** | 8192 | 0.55 | 0 | 0.92 | 1.08 | **-1** | RAM_OPTIMIZED | 8 |
| SUMMARIZER | deepseek-r1:latest | **GPU/VRAM** | 4096 | 0.05 | 100 | 0.80 | 1.10 | **-1** | ELITE_REASONING | 0 |
| DISPATCHER | qwen3:4b  | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| CRITIC | qwen3:4b  | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| PLANNER | deepseek-r1:latest | **GPU/VRAM** | 4096 | 0.05 | 100 | 0.85 | 1.05 | **-1** | ELITE_REASONING | 0 |
| CRITIC_ALPHA | deepseek-r1:latest | **GPU/VRAM** | 4096 | 0.05 | 100 | 0.80 | 1.10 | **-1** | ELITE_REASONING | 0 |
| CRITIC_BETA | qwen3:4b  | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| DATA_SCOUT | qwen3:4b  | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| EXECUTOR_ALPHA | deepseek-r1:latest | **GPU/VRAM** | 4096 | 0.0 | 100 | 0.85 | 1.05 | **-1** | ELITE_REASONING | 0 |
| EXECUTOR_BETA | qwen3:4b | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| EXECUTOR | qwen3:4b | **CPU/RAM** | 8192 | 0.30 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| RESERVE_AGENT | qwen3:4b | **CPU/RAM** | 8192 | 0.45 | 0 | 0.92 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| COMPRESSOR | qwen3:0.6b | **GPU/VRAM** | 4096 | 0.1 | 100 | 0.90 | 1.10 | **-1** | REFLEX_GALAXY | 0 |
| VISION | moondream:latest | **CPU/RAM** | 2048 | 0.1 | 0 | 0.90 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| VOICE | faster-whisper | **CPU/RAM** | 1024 | 0.0 | 0 | 1.0 | 1.0 | **-1** | STABLE_SYNC | 8 |
| TRANSLATOR | qwen3.5:latest | **CPU/RAM** | 8192 | 0.2 | 0 | 0.88 | 1.10 | **-1** | RAM_OPTIMIZED | 8 |
| GRAPHIC_MASTER | SDXL-Turbo-ROCm | **GPU/VRAM** | 0 | 0.0 | 100 | -1 | -1 | 0 | ULTRA_ART | 0 |

---

## 🛰️ 4. Danh mục Điều phối Đặc vụ & Kỹ năng (Orchestration Matrix)

| Đặc vụ / Kỹ năng | Profile Khuyến nghị | Mục đích | Ưu tiên GPU |
| :--- | :--- | :--- | :--- |
| **Neural Eye** | OFFLINE_RESERVE | Giám sát thị giác và Audit Dashboard. | **CAO (Vision)** |
| **Skill Forge** | ELITE_REASONING | Tự kiến tạo và đúc kỹ năng mới. | Thấp (RAM) |
| **Instant Memory** | STABLE_SYNC | Index tri thức tức thì vào Qdrant. | Trung bình |
| **Watchdog** | UNIFIED_ELITE | Vệ binh chủ động tầm soát sự cố. | Thấp (CPU) |

---
*Sovereign Property of Tổng Giám Đốc LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 🌌🏛️🔥🦾👑🔗*
