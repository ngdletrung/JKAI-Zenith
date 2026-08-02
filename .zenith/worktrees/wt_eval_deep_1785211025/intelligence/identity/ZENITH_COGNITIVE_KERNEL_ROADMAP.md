<!-- 
[ZENITH FILE DIRECTIVE]
- File: ZENITH_COGNITIVE_KERNEL_ROADMAP.md
- Role: Zenith Intelligence Documentation.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v19.9
[WORKING PRINCIPLES]:
1. [HEADER-FIRST]: Antigravity BAT BUOC phai doc khoi header nay truoc khi thao tac.
2. [SDS-COMPLIANCE]: Moi thay doi phai tuan thu Giao thuc SDS moi nhat.
3. [NO-EMOJI]: Cam dung emoji trong noi dung tep cau hinh va logic.
-->
# ZENITH COGNITIVE KERNEL ROADMAP & RESEARCH CHARTER (v6.0)
**"Lộ trình Nghiên cứu Phát triển và Chuyển đổi Công nghệ Nhân Nhận thức"**

> [!IMPORTANT]
> **ĐỊNH HƯỚNG PHÁT TRIỂN**: Tài liệu này phác thảo lộ trình nghiên cứu và phát triển sản phẩm (R&D Roadmap) nhằm tiến hóa hệ thống JKAI Zenith từ một bộ điều phối đơn lẻ (Orchestrator) thành một **Hạ tầng Nhân Nhận thức Phân tán có khả năng chịu lỗi cao (Production-Grade Distributed Cognitive Substrate)**.
> Mọi bước tiến công nghệ đều tuân thủ nguyên lý Kỹ thuật hệ thống: ưu tiên độ ổn định, kiểm soát tài nguyên nghiêm ngặt và giải quyết các bài toán biên thực tế.

---

## 🧭 1. Các Cột Mốc Kỹ Thuật Đã Hoàn Thành (Completed Milestones)

Hệ thống đã trải qua quá trình tiến hóa nghiêm túc để đạt được độ trưởng thành về mặt kiến trúc như ngày hôm nay:

*   **Thế hệ v1.0 - v3.0 (Thiết lập Bộ khung Core)**: Phân rã cấu trúc hàm monolithic, module hóa các tiến trình lập lịch, xây dựng cơ chế lưu vết sự kiện cơ bản.
*   **Thế hệ v3.5 (Tối ưu hóa Tài nguyên Dual-Engine & Service Registry)**: Tách Ollama thành 2 luồng độc lập (GPU-only dành cho suy luận sâu, CPU-only dành cho điều phối phụ trợ). Phát triển `Service Registry` tập trung để triệt tiêu lỗi phân giải địa chỉ IP nội bộ Docker.
*   **Thế hệ v5.0 (Cân bằng Nội môi & Phân loại Lỗi)**: Tích hợp `homeostasis.py` giám sát ranh giới OOM, phát triển bảng phân loại lỗi hệ thống (`Advanced Failure Taxonomy`) hỗ trợ retry tự động.
*   **Thế hệ v6.0 (Kiến trúc Nhân Microkernel & Bảo mật Sandbox)**: 
    *   Thiết lập ranh giới cứng giữa **Kernel Space (Deterministic)** và **Cognitive Space (Probabilistic)**.
    *   Triển khai `CapabilityBroker` cấp Scoped Tokens và `PolicyProofEngine` kiểm duyệt tĩnh mã độc để chống thoát hộp cát (Sandbox Escape).
    *   Phát triển giao dịch nhận thức `Cognitive ACID` (tự động sao lưu và phục hồi từ `.bak` vật lý) đi kèm cây giám sát Erlang Supervisor.
    *   Tích hợp nhãn thời gian logic **Hybrid Logical Clock (HLC)** để đảm bảo trật tự nhân quả cho hệ thần kinh `CognitiveEventBus`.
    *   Xây dựng `DreamConsolidator` học tập chủ động dựa trên SQLite Event Store.

---

## 🚀 2. Lộ Trình Tiến Hóa 5 Giai Đoạn Tiếp Theo (Future R&D Roadmap)

Để nâng cấp sức mạnh thực tế của hệ thống tiệm cận cấp độ doanh nghiệp phân tán:

### 📊 GIAI ĐOẠN 1: Hệ Thống Phân Phối Chú Ý Và Ngắt Tiến Trình Chủ Động (Attention Arbitration)
*   **Mục tiêu**: Xây dựng module `AttentionArbitrator` tại tầng Kernel để quản lý tập trung mức độ ưu tiên chú ý của hệ thống.
*   **Giải pháp**:
    *   Tính toán trọng số Saliency (độ khẩn cấp) của từng sự kiện đầu vào.
    *   Kích hoạt cơ chế **Active Preemption (Ngắt tiến trình chủ động)**: Khi phát hiện tín hiệu nguy cấp từ Operator hoặc hệ thống (ví dụ: cảnh báo rò rỉ bảo mật), Kernel sẽ lập tức tạm dừng (`SUSPENDED`) các luồng suy luận dài hạn đang chạy để nhường tài nguyên GPU/VRAM xử lý tác vụ khẩn cấp.

### 🔀 GIAI ĐOẠN 2: Chuyển Đổi Ngăn Xếp Mục Tiêu Thành Đồ Thị DAG (Goal Directed Acyclic Graph)
*   **Mục tiêu**: Nâng cấp cấu trúc tuyến tính `GoalStack` thành đồ thị định hướng không chu trình `GoalDAG`.
*   **Giải pháp**:
    *   Cho phép phân rã một mục tiêu chiến lược vĩ mô thành nhiều mục tiêu nhánh song song có liên kết nhân quả.
    *   Hỗ trợ thực thi đa luồng nhận thức song song (Parallel Cognition Flow) và đồng bộ trạng thái ở các mốc kiểm chuẩn (Milestone Checkpoints).
    *   Tối ưu hóa khả năng hồi phục từ reboot: nếu máy chủ sập nguồn, hệ thống có thể nạp lại đồ thị GoalDAG từ đĩa và tiếp tục chạy các node dở dang mà không phải bắt đầu lại từ đầu.

### 🌐 GIAI ĐOẠN 3: Hạ Tầng Nhận Thức Phân Tán Đa Node - v7.0 (Distributed Thought Fabric)
*   **Mục tiêu**: Kết nối nhiều máy chủ vật lý chạy Zenith thành một Swarm nhận thức đồng thuận.
*   **Giải pháp**:
    *   Sử dụng thuật toán đồng thuận **Raft** để đồng bộ hóa bản đồ thế giới quan (`TypedWorldGraph`) và World State giữa các node.
    *   Triển khai lớp truyền thông **Cognitive RPC (cRPC)** bảo mật, mã hóa AES-256 để các đặc vụ trên các máy chủ khác nhau có thể chia sẻ vùng nhớ ngắn hạn hoặc gọi kỹ năng chéo node (Cross-Node Skill Calling).

### 🦾 GIAI ĐOẠN 4: Tự Động Hóa Định Tuyến Trọng Số Mô Hình (Dynamic Model Offloading)
*   **Mục tiêu**: Tối ưu hóa sâu sắc hơn nữa cho card đồ họa AMD RX 6600 (8GB VRAM) và các dòng phần cứng hạn chế.
*   **Giải pháp**:
    *   Phát triển trình điều khiển HAL tự động nạp/rút (hot-swap) mô hình dựa trên độ phức tạp tức thời của tiến trình tư duy.
    *   Tận dụng thư viện ROCm API để đọc trực tiếp ranh giới phân mảnh bộ nhớ của GPU và kích hoạt bộ gom rác (garbage collection) trước khi lỗi OOM của trình điều khiển phần cứng xảy ra.

---

## 🛠️ Nguyên Tắc Thiết Kế Không Thay Đổi (Design Principles)

1.  **Systems-First Over AI-First**: Ưu tiên sự an toàn, khả năng chịu lỗi và tính deterministic của hệ thống lên trên kỳ vọng ma thuật vào LLM. LLM là công cụ đề xuất giả thuyết, Kernel mới là thực thể ra lệnh.
2.  **Chết Một Cách Dự Báo Được (Fail Predictably)**: Mọi sự cố, ngoại lệ bắt buộc phải được bẫy lỗi tĩnh, định danh rõ ràng kèm cờ phục hồi, tuyệt đối không được phép để xảy ra hiện tượng crash không kiểm soát làm sập toàn bộ hệ điều hành.
3.  **Tối Ưu Hóa Sâu Sắc Cho Phần Cứng Thực Tế**: Thiết kế hệ thống phải tôn trọng giới hạn vật lý của máy chủ hiện tại (Xeon 44-Thread & RX 6600 8GB). Mọi thuật toán quản lý bộ nhớ đệm bắt buộc phải ưu tiên tính gọn nhẹ.

---
*Cognitive Substrate Roadmap. v6.0. Technical Vision & R&D Charter. Forged for Reliable Automation.* 🏛️⚙️🛡️
