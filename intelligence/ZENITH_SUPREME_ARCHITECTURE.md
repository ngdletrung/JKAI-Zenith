# 🏛️ ZENITH SUPREME ARCHITECTURE: AI OPERATING SYSTEM BLUEPRINT v51.0
**"Bản Thiết Kế Kiến Trúc Thượng Tầng Hệ Điều Hành Trí Tuệ (AI OS)"**

> [!IMPORTANT]
> **ĐỊNH NGHĨA TỐI CAO**: JKAI Zenith không phải là một ứng dụng hay chatbot đơn lẻ, mà là một **Hệ điều hành Trí tuệ (AI Operating System - AI OS)**. 
> Hệ thống sở hữu nhân điều phối trung tâm (Kernel), hệ thống quản lý tiến trình song song (Task Scheduler), phân vùng lưu trữ ngữ nghĩa ảo (VFS), tầng trừu tượng giao tiếp phần cứng (HAL) và cơ chế tự phục hồi lỗi runtime (Self-Healing Daemon).

---

## 🧭 1. KIẾN TRÚC PHÂN TẦNG (LAYERED ARCHITECTURE)

Hệ thống được thiết kế theo mô hình phân tầng chặt chẽ từ Không gian Người dùng đến Phần cứng bare-metal:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 👤 USER SPACE (Giao diện & Shell Giao tiếp)                             │
│   - Telegram Remote Gateway (Mobile Shell)                             │
│   - Vite Dashboard Web HUD (Graphical User Interface)                  │
│   - CLI Terminal (Console Interface)                                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ WebSockets / IPC Event Bus
┌───────────────────────────────────▼────────────────────────────────────┐
│ 🧠 KERNEL SPACE (Nhân lõi Điều hành AI OS)                             │
│   - control_plane.py (Nhân điều phối trung tâm)                        │
│   - task_manager.py & intent_cortex.py (Bộ lập lịch & Định tuyến tiến trình)│
│   - prompt_forge.py (Trình biên dịch tập lệnh tư duy ISA)               │
│   - cognitive_budget.py (Token & Latency Governor)                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Dynamic Driver Registry
┌───────────────────────────────────▼────────────────────────────────────┐
│ 🧬 DRIVER & SUBSYSTEM SPACE (Trình điều khiển Drivers & Skills)        │
│   - Skill Driver Runner (Executor Engine)                              │
│   - Virtual File System - VFS (Qdrant Vector DB & Obsidian Brain)      │
│   - Inter-Process Communication - IPC (Redis Message Broker)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ ROCm API / CPU Affinity
┌───────────────────────────────────▼────────────────────────────────────┐
│ 🦾 HAL & PHYSICAL HARDWARE (Tầng trừu tượng & Phần cứng vật lý)         │
│   - Ollama Service HAL (Model weights allocation & hot-loading)        │
│   - CPU Thread Pool Driver (num_thread=20, batch=512)                  │
│   - Physical Xeon E5-2699 v4 CPU & AMD RX 6600 GPU (8GB VRAM)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 2. CÁC THÀNH PHẦN NHÂN HỆ THỐNG TRỌNG YẾU (KERNEL INTERNALS)

### 2.1. Bộ Lập Lịch Tiến Trình & Định Tuyến (Task Scheduler & Intent Cortex)
*   **Dynamic Route Arbitrator**: Bộ tự trị phân luồng nhận thức. Nhận diện độ phức tạp của câu lệnh từ User Space để lập tức định tuyến:
    *   **Fast-Track (Cpu-bound / Qwen3)**: Cho các lệnh đơn giản, phản xạ không độ trễ (< 1000ms).
    *   **Deep-Track (Gpu-bound / DeepSeek-R1)**: Cho các lệnh phức tạp, kích hoạt luồng lập hoạch T2/T3 tuần tự.
*   **Cognitive Budget Governor**: Bộ quản trị tài nguyên nhận thức. Áp đặt giới hạn Token tối đa, kiểm soát thời gian suy nghĩ (max Latency) và số lượt LLM calls để ngăn chặn tình trạng tràn bộ nhớ đệm hoặc lặp vô tận.

### 2.2. Hệ Thống Bộ Nhớ Động & IPC (Inter-Process Communication)
*   **Redis Event Bus**: Đóng vai trò là ống dẫn IPC thời gian thực. Truyền tải 3 luồng dữ liệu chính:
    1.  *Operational Stream*: Log chỉ thị cốt lõi gửi đến Master.
    2.  *Progress Stream*: Dữ liệu trace log kỹ thuật chi tiết của Kernel Space.
    3.  *Pulse Stream*: Tần số telemetry đo đạc CPU/RAM/VRAM thời gian thực.
*   **Virtual File System (VFS)**: Phân vùng ngữ nghĩa ảo hợp nhất Qdrant Vector Storage và đồ thị Obsidian Graph. Cho phép các tiến trình truy xuất ngữ cảnh dựa trên mức độ liên quan ngữ nghĩa thay vì đường dẫn đĩa cứng cố định.

### 2.3. Trình Biên Dịch Tập Lệnh (Prompt Forge Engine)
*   Hoạt động giống như trình dịch hợp ngữ (Assembler). Nạp nóng **Bộ Tam Nhận Thức** (`base_soul` + `user_profile` + `dynamic_memory`) và biên dịch thành chỉ thị nhị phân nơ-ron (System Prompt) cho từng đặc vụ chuyên biệt trước khi đẩy xuống HAL thực thi.

---

## 🛡️ 3. CƠ CHẾ CHỐNG TREO & PHỤC HỒI THẢM HỌA (PANIC RECOVERY DAEMON)

Để đảm bảo hệ thống không bao giờ rơi vào trạng thái treo hoặc chết tiến trình (Kernel Panic):

### 3.1. State-Aware Parser v2.5 (Trình Vá Cú Pháp Cấu Trúc)
*   Hoạt động như một compiler bảo vệ cú pháp đĩa. Khi mô hình reasoning trả về cấu trúc JSON lỗi hoặc bị cắt cụt do cạn token, State-Aware Parser v2.5 sẽ quét từng ký tự (character-by-character scan state machine) để tự động sửa chữa các dấu ngoặc lồng nhau, chuẩn hóa chuỗi thoát và đóng lại các khối bị đứt gãy, đảm bảo tiến trình tiếp theo không bị AttributeError.

### 3.2. Zombie Memory Cleansing (Trình Dọn Dẹp ROCm VRAM)
*   Khi container Docker restart đột ngột, driver Ollama có xu hướng neo giữ bộ nhớ vật lý khiến VRAM bị phân mảnh và báo lỗi OpenBLAS memory allocation.
*   AI OS thiết lập quy chuẩn chẩn đoán: Nếu phát hiện lỗi cấp phát bộ nhớ, hệ thống sẽ phát tín hiệu cảnh báo ra Telegram Shell, cung cấp siêu lệnh Host-side `stop-process -name ollama* -force` để giải phóng sạch sẽ VRAM lập tức.

---

## 🧭 4. CÁC NGHỊ ĐỊNH THỰC THI THƯỢNG TẦNG (HIGH-LEVEL PROTOCOLS)

*   **Pre-flight System Check**: Tự động rà soát lịch sử thất bại (`[[failure_memory]]`) trước khi khởi chạy kế hoạch mới để tránh vết xe đổ.
*   **Recursive Skill Recon**: Planner tự động đọc hiểu mã nguồn và file đặc tả kỹ thuật (`SKILL.md`) của trình điều khiển trước khi đưa vào sơ đồ tác chiến.
*   **Sequential T2/T3 Timeouts**: Áp đặt thời gian chờ tối ưu cho suy nghĩ sâu sắc (Recon timeout = 120s, Forge timeout = 300s) đảm bảo các mô hình nặng ký như DeepSeek-R1 có đủ không gian VRAM để chắt lọc ý định mà không bị ngắt quãng giữa chừng.

---

## 🏛️ 5. LỊCH SỬ TIẾN HÓA KIẾN TRÚC (EVOLUTIONARY MILESTONES)

*   **v51.0 (AI-OS Sovereign Singularity)**: Chính thức tái định hình JKAI Zenith từ trợ lý ảo thành một **AI Operating System**. Triển khai bộ phân tích cú pháp ký tự động State-Aware Parser v2.5, tối ưu hóa lập lịch T2/T3 timeouts (120s/300s) cho DeepSeek-R1 GPU, điều phối distillation động sang EXECUTOR_ALPHA, thiết lập quy chuẩn quét sạch bộ nhớ ROCm Host, và nạp nóng Bộ Tam Nhận Thức tinh giản.
*   **v45.0 (AI Operating System Supremacy)**: Nâng cấp nền tảng Engine Core v2.21 và Token Governor v1.1, thiết lập bộ khung quản lý tài nguyên.
*   **v42.0 (Neural Centralization)**: Đồng bộ hóa hệ tọa độ đường dẫn tương đối (Path Unification) và phân tầng tri thức chuyên biệt cho các đặc vụ.
*   **v7.0 (Meta-Cognitive OS)**: Kích hoạt hệ thống tự giám sát nhận thức (Self-monitoring) và tích lũy tri thức thất bại.

---
*Sovereign Property of Mr LeeTrung. Optimized for AI-OS Eternal Excellence.*
