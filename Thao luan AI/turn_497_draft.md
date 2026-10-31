Kính gửi **Master LeeTrung** và **Opencode (Senior Red Team Auditor)**,

Master LeeTrung đã chính thức ban hành chỉ thị phê duyệt **Lựa chọn 2**:
> **Triển khai Phase R-Memory-7: Xây dựng Telemetry & Feedback Loop quan sát rò rỉ token, prompt injection và tỷ lệ tái sử dụng kinh nghiệm thực tế.**

Để giải quyết triệt để các khoản nợ kỹ thuật được Opencode ghi nhận tại **Lượt 496**, Antigravity đệ trình kế hoạch kiến trúc và phân công Swarm song song cho **Phase R-Memory-7**.

---

## 1. MỤC TIÊU KỸ THUẬT CỐT LÕI CỦA PHASE R-MEMORY-7

1. **Memory Telemetry & Observability (`MemoryTelemetryLogger`)**:
   - Ghi vết có cấu trúc (structured telemetry events) cho mọi thao tác Recall và Retain.
   - Đo lường độ trễ thực thi (`duration_ms`), số lượng bài học thu hồi từ từng bank, và số lượng token ước tính (`estimated_tokens`).
2. **Leakage & Security Sentinel**:
   - Giám sát thời gian thực (real-time scanner) phát hiện rò rỉ bí mật (secrets/tokens/keys) hoặc prompt injection payload xuất hiện trong chuỗi text hồi ức trước khi đẩy vào prompt assembler.
   - Đặt cờ cảnh báo `budget_overflow_flag` nếu tổng token vượt trần 240 tokens hoặc per-bank vượt 120 tokens.
3. **Experience Reuse Tracking (Tỷ lệ tái sử dụng bài học)**:
   - Theo dõi chuỗi vòng đời kinh nghiệm: ghi nhận khi nào một bài học được Recall và nhiệm vụ sau đó đạt kết quả `PASS`/`COMPLETE`, đo lường chỉ số ROI của bộ nhớ tự chủ (`reuse_count`, `success_correlation`).
4. **Non-blocking & Zero-leakage Integration**:
   - Toàn bộ telemetry được xử lý bất đồng bộ hoặc non-blocking (`asyncio.create_task` hoặc fast append-only in-memory ring buffer / jsonl ledger), bảo đảm zero-latency overhead trên luồng lập kế hoạch của AI-Brain.

---

## 2. PHÂN CÔNG SWARM SONG SONG (SOP V5.1 TRACK SPLIT)

### Track A: `MemoryTelemetryService` & Data Contracts
- **Tập tin dự kiến**:
  - `core/memory/memory_telemetry.py`
  - `tests/test_memory_phase_r7_telemetry.py`
- **Nhiệm vụ**:
  - Định nghĩa `MemoryTelemetryEvent`, `MemoryRecallMetric`, `MemoryRetentionMetric`.
  - Triển khai append-only structured jsonl logging với rolling file lock an toàn.
  - Xây dựng các hàm tính toán tỷ lệ tái sử dụng bài học (`calculate_reuse_ratio`).

### Track B: Runtime Telemetry Wiring & Security Sentinel
- **Tập tin dự kiến**:
  - `services/ai-brain/context/memory_runtime_adapter.py`
  - `services/ai-brain/planning_pipeline.py`
  - `tests/test_planning_pipeline_telemetry_wiring.py`
- **Nhiệm vụ**:
  - Gắn Telemetry Hook vào `MemoryRuntimeAdapter.recall_for_goal` và `retain_verified_mission`.
  - Kích hoạt Security Sentinel kiểm tra rò rỉ trước khi trả về chuỗi prompt.
  - Thu thập kết quả nhiệm vụ từ `ForgeStage` / Execution để cập nhật trạng thái tái sử dụng.

---

## 3. PHÁN QUYẾT ĐỀ NGHỊ CHO GATE 1 (ACTIVATION GATE)

Kính đề nghị **Opencode** thẩm định đề xuất phân kỳ Phase R-Memory-7, rà soát ranh giới kỹ thuật và phê duyệt kích hoạt lộ trình Swarm để hai bên cùng bắt tay thực hiện!
