<!-- 
[ZENITH FILE DIRECTIVE]
- File: ZENITH_SUPREME_ARCHITECTURE.md
- Role: Zenith Intelligence Documentation.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v19.9
[WORKING PRINCIPLES]:
1. [HEADER-FIRST]: Antigravity BAT BUOC phai doc khoi header nay truoc khi thao tac.
2. [SDS-COMPLIANCE]: Moi thay doi phai tuan thu Giao thuc SDS moi nhat.
3. [NO-EMOJI]: Cam dung emoji trong noi dung tep cau hinh va logic.
-->
# 🏛️ ZENITH COGNITIVE RUNTIME OS KERNEL ARCHITECTURE SPECIFICATION (v6.0)
**"Đặc tả Kiến trúc Thượng tầng và Cơ chế Vận hành Nhân Hệ thống Nhận thức"**

> [!IMPORTANT]
> **ĐẶC TẢ KỸ THUẬT**: Tài liệu này mô tả chi tiết kiến trúc phân tầng, cơ chế lập lịch, hệ thống truyền thông nội bộ (IPC) và các động cơ phục hồi lỗi ở tầng thấp (low-level) của **JKAI Zenith v6.0**. 
> Thiết kế này tập trung vào việc tối đa hóa độ ổn định, kiểm soát chính xác tài nguyên phần cứng (CPU/GPU) và bảo đảm khả năng chịu lỗi định tính trên môi trường phân tán.

---

## 🧭 1. Mô Hình Phân Tầng Hệ Thống (Layered Systems Architecture)

Kiến trúc hệ thống được thiết kế theo mô hình phân lớp nghiêm ngặt, tách biệt hoàn toàn vai trò từ giao diện người dùng đến phần cứng vật lý:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 💻 OPERATOR SPACE (Giao diện & Cổng truyền chỉ thị vĩ mô)             │
│   - Telegram Remote Shell Gateway (Mobile Console)                     │
│   - Vite Dashboard Web HUD (Graphical Status Interface)                │
│   - REST API Endpoints & CLI Shell                                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ WebSockets / HTTP REST API
┌───────────────────────────────────▼────────────────────────────────────┐
│ 🧠 KERNEL SPACE (Nhân lõi điều phối - Deterministic Core)              │
│   - cognitive_scheduler.py (Life cycle state machine & Supervisor)     │
│   - cognitive_event_bus.py (Asynchronous event bus & Monotonic HLC)    │
│   - world_model.py (Typed World Graph & Constraint DSL Simulator)      │
│   - capability_broker.py (Scoped security tokens & Sandbox control)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Dynamic Driver Registry
┌───────────────────────────────────▼────────────────────────────────────┐
│ 🧬 DRIVER & SUBSYSTEM SPACE (Trình điều khiển & Bộ nhớ phân tầng)      │
│   - Skill Driver Runner (Surgery engine & AST validator)               │
│   - Federated Memory Subsystem (SQLite Episodic & Qdrant Vector VFS)   │
│   - Inter-Process Communication - IPC (Redis Message Broker)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ ROCm API / CPU Affinity
┌───────────────────────────────────▼────────────────────────────────────┐
│ 🦾 HAL & PHYSICAL HARDWARE (Tầng trừu tượng & Thiết bị vật lý)         │
│   - Ollama Service HAL (Model instance scheduler & KV cache manager)    │
│   - Windows Host Process Driver (CPU Core affinity, num_thread=20)     │
│   - Xeon E5-2699 v4 (44-Threads CPU) & AMD RX 6600 GPU (8GB VRAM)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 2. Các Engine Thành Phần Nhân Hệ Thống (Kernel Internals)

### 2.1. Bộ Lập Lịch Tiến Trình Nhận Thức (Cognitive Scheduler)
*   **Dynamic Route Arbitrator (Bộ định tuyến động)**: Tự động phân tích độ phức tạp của chỉ thị từ Operator Space để tối ưu hóa tài nguyên phần cứng:
    *   *Fast-Track (CPU-Bound / Qwen3)*: Dành cho các tác vụ đơn giản, phản hồi không độ trễ (< 1000ms), thực thi trực tiếp bằng các thuật toán định tính hoặc mô hình LLM siêu nhẹ trên CPU.
    *   *Deep-Track (GPU-Bound / DeepSeek-R1)*: Dành cho các tác vụ suy luận sâu sắc, kích hoạt luồng lập hoạch dài hạn (Long-Horizon Planning) trên GPU.
*   **Cognitive Budget Governor (Quản trị ngân sách nhận thức)**: Áp đặt giới hạn tối đa cho lượng token đầu vào, thời gian suy nghĩ tối đa (thinking latency) và độ sâu đệ quy của Goal Stack (ngăn chặn hoàn toàn hiện tượng lặp vô hạn gây cạn kiệt tài nguyên).
*   **Self-Model Cortex & Uncertainty Calibration**: Theo dõi tỷ lệ thành công thực tế của từng đặc vụ đối với từng lớp thẻ năng lực (Capabilities). Khi độ mơ hồ của câu trả lời vượt ngưỡng an toàn (độ tin cậy < 0.65), hệ thống sẽ chủ động đình chỉ tiến trình và yêu cầu Master phê duyệt.

### 2.2. Hệ Thống Truyền Thông Nội Bộ & Trật Tự Nhân Quả (IPC & Event Bus)
*   **Redis Event Bus**: Đóng vai trò là đường ống truyền dẫn IPC tốc độ cao. Toàn bộ thông số đo đạc hiệu năng vật lý, trạng thái phẫu thuật file cấu hình và tiến trình suy nghĩ được phát sóng bất đồng bộ dưới dạng các Spans ngữ cảnh.
*   **Hybrid Logical Clock (HLC)**: Khắc phục triệt để hiện tượng lệch thời gian vật lý giữa các container trong môi trường Docker. Mỗi sự kiện nhận thức được đính kèm nhãn thời gian HLC tăng đơn điệu, bảo đảm khả năng tái dựng chuỗi sự kiện lỗi chính xác 100% trong quá trình phân tích sự cố (Forensics Replay).
*   **Federated Memory Subsystem (Hệ thống bộ nhớ phân tầng)**:
    *   *Episodic Memory*: Bản ghi sự kiện thô bất biến (lưu trong SQLite).
    *   *Semantic Memory*: Bản đồ thế giới quan quan hệ (`world_model.py`).
    *   *Procedural Memory*: Thư viện kỹ năng và logic kỹ thuật cứng (`registry.json`).

### 2.3. Trình Biên Dịch Chỉ Thị (Prompt Forge Engine)
*   Vận hành tương tự trình biên dịch hợp ngữ (Assembler). Thực hiện nạp nóng (hot-load) các tham số ngữ cảnh từ bộ nhớ đệm VAULT, quy chế RULES và hồ sơ đặc vụ AGENTS, biên dịch thành một hệ chỉ thị định dạng XML có tính ràng buộc cấu trúc cao trước khi gửi xuống các API mô hình.

---

## 🛡️ 3. Cơ Chế Chịu Lỗi Và Phục Hồi Thảm Họa (Panic Recovery Daemon)

Nhân hệ thống tích hợp các động cơ tự động phát hiện ngoại lệ và khôi phục trạng thái để bảo vệ tính bền bỉ của hệ điều hành:

### 3.1. State-Aware Parser v2.5 (Vá lỗi cấu trúc thời gian thực)
*   Khi LLM trả về cấu trúc dữ liệu JSON bị hỏng hóc hoặc thiếu dấu ngoặc do cạn token giữa chừng, parser sẽ quét từng ký tự bằng máy trạng thái tĩnh, tự động đóng lại các khối cấu trúc bị đứt gãy và sửa lỗi thoát chuỗi, ngăn ngừa lỗi sụp đổ luồng (AttributeError / KeyError) ở các bước xử lý sau.

### 3.2. Erlang-like Supervisor Tree (Cây giám sát chịu lỗi)
*   Cấu trúc luồng tư duy được tổ chức theo sơ đồ hình cây phân cấp. Khi một tác vụ con gặp sự cố, supervisor sẽ tự động áp dụng chính sách phục hồi định tính:
    - *Exponential Backoff Retry*: Tự động thử lại tác vụ với độ giãn cách thời gian tăng dần để đợi tài nguyên API phục hồi.
    - *Compensating Actions*: Khi một giao dịch sửa đổi file hệ thống bị đứt gãy ở giữa chừng, hệ thống tự động hoàn tác (Rollback) nội dung file gốc từ bản sao lưu `.bak` vật lý và xóa bỏ các tệp rác.

### 3.3. Zombie Memory Cleansing & Hardware Homeostasis
*   Khi Ollama hoặc các tiến trình GPU bị treo, bộ nhớ VRAM của GPU RX 6600 (8GB) sẽ bị phân mảnh dẫn đến lỗi Out-Of-Memory (OOM). 
*   Homeostasis Engine hoạt động như một daemon kiểm soát tài nguyên: nếu phát hiện rủi ro phân mảnh VRAM, hệ thống sẽ gửi cảnh báo an toàn và kích hoạt lệnh quét dọn Zombie Processes từ host ở chế độ an toàn để khôi phục 100% tài nguyên GPU.

---

## 🧭 4. Các Nghị Định Thực Thi Thượng Tầng (High-Level Protocols)

*   **Pre-flight Failure Memory Check**: Tầm soát lịch sử thất bại trong SQLite trước khi lập sơ đồ tác chiến mới để chủ động loại bỏ các phương án đã được chứng minh là không hiệu quả.
*   **Recursive Skill Recon**: Bắt buộc Planner phải phân tích đặc tả kỹ thuật và file giao thức (`SKILL.md`) của trình điều khiển trước khi đưa kỹ năng đó vào sơ đồ thực thi.
*   **Sequential Planning Timeouts**: Áp đặt thời gian chờ tối ưu (Recon = 120 giây, Forge & Execute = 300 giây) bảo đảm mô hình suy luận DeepSeek-R1 có đủ không gian xử lý ngữ cảnh sâu mà không bị ngắt quãng giữa chừng.

---
*Kernel Architecture Specification. v6.0. Microkernel Design. Engineered for High-Availability.* 🏛️⚙️🛡️
