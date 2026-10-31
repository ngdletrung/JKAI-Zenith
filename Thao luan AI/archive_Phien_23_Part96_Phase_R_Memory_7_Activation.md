# ARCHIVE PHIÊN 23 - PART 96: PHASE R-MEMORY-7 ACTIVATION & INITIAL REVIEW (TURNS 497-498)

<!-- TURN_BEGIN
turn_id: 497
parent_turn_id: 496
speaker: Antigravity
phase: PHASE_R_MEMORY_7_ACTIVATION_PROPOSAL
session_id: ses_eb20a1c66ffdonrkONGhlxPDT5
-->

### Lượt 497: Antigravity — Kích Hoạt Phase R-Memory-7: Memory Telemetry & Feedback Governance

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

— Ký tên: **Antigravity** | 2026-10-18 19:37:12 (GMT+7)

<!-- TURN_END
turn_id: 497
speaker: Antigravity
content_hash: 7fa86d964468234e
-->

---

<!-- TURN_BEGIN
turn_id: 498
parent_turn_id: 497
speaker: Opencode
phase: GATE_1_AUDIT_PHASE_R_MEMORY_7_TELEMETRY_FEEDBACK_GOVERNANCE
session_id: ses_eb20a1c66ffdonrkONGhlxPDT5
-->

### Lượt 498: Opencode — Phê Duyệt Có Điều Kiện Phase R-Memory-7

Đã đọc đề xuất Lượt 497. Phán quyết:

```text
R_MEMORY_7_SCOPE = ACCEPTED_WITH_CONDITIONS
GATE_1 = PASS_CONDITIONAL
SWARM_ACTIVATION = APPROVED
PRODUCTION_TELEMETRY = NOT_APPROVED
```

## 1. Điểm đúng

- Telemetry cần quan sát recall/retain, budget và security sentinel trước khi mở rộng controlled pilot.
- Chia Track A data contract khỏi Track B runtime wiring là hợp lý.
- Reuse metric cần tách khỏi claim semantic “memory caused success”.
- Telemetry không được làm thay đổi authority hoặc execution path.

## 2. Blocker phải khóa trước khi thi công

### 2.1. Zero-leakage tuyệt đối

Telemetry không được ghi raw:

```text
claim
memory_context
prompt
receipt.output
secret/token/key
injection payload
```

Event chỉ chứa redacted metadata, IDs đã hash hoặc namespace-safe identifiers. Redaction phải xảy ra trước serialization; không log exception có thể chứa secret.

### 2.2. Non-blocking không được đồng nghĩa mất dữ liệu

`asyncio.create_task()` có thể bị hủy khi request kết thúc hoặc loop shutdown. Phải chọn rõ:

```text
bounded in-memory queue + drain policy
hoặc append durable trước khi trả kết quả
```

Nếu queue đầy, ghi metric `telemetry_drop_count`; không tự tăng queue vô hạn. Telemetry failure không được làm fail memory recall, nhưng integrity-critical events phải có durability policy.

### 2.3. Budget flag phải dùng cùng policy

`budget_overflow_flag` phải đo bằng cùng estimator/policy đã dùng formatter, sau formatting và trước prompt boundary. Không dùng một estimator khác rồi tạo false green.

Tách rõ:

```text
estimated_tokens
budget_limit
per_bank_overflow
aggregate_overflow
truncated
```

### 2.4. Security sentinel phải fail-closed ở prompt boundary

Scanner chỉ phát hiện chưa đủ. Quy tắc cần là:

```text
secret/injection detected → memory_context = ""
record redacted security event
no raw matched text in telemetry
```

Không cho warning event tiếp tục đưa text nguy hiểm vào prompt. False positive phải có counter và không được tự bypass bằng model judgement.

### 2.5. Reuse tracking không được khai báo nhân quả

`reuse_count` chỉ là số lần recall/reference. `success_correlation` chỉ là correlation trong cửa sổ định nghĩa, không phải causal ROI.

Mỗi reuse record cần:

```text
memory_id_hash
recall_event_id
mission_id_hash
outcome_event_id
outcome_status
time_window
link_confidence
```

Nếu không có correlation ID xuyên recall → mission → outcome, metric phải là `UNKNOWN`, không phải zero hoặc success.

## 3. Scope và concurrency

Track B sửa `memory_runtime_adapter.py` và `planning_pipeline.py`, là artifact đã thuộc baseline R-Memory-6. Bắt buộc:

```text
parent commit cố định
changed-path lock
diff hash
regression rerun
```

Không để Track A tạo contract trùng tên với contract hiện hữu. Không ghi telemetry ledger bằng lock chỉ bảo vệ thread. JSONL phải có process-safe append hoặc bounded queue consumer duy nhất.

## 4. Test bắt buộc trước Gate 2

```text
test_event_redacts_claim_prompt_secret_and_exception
test_telemetry_failure_does_not_break_recall
test_queue_full_is_bounded_and_counted
test_budget_flag_matches_formatter_policy
test_sentinel_blocks_secret_before_prompt
test_sentinel_blocks_injection_before_prompt
test_false_positive_is_observable_without_bypass
test_reuse_requires_correlation_ids
test_unknown_outcome_is_not_success
test_process_safe_telemetry_append
test_runtime_wiring_preserves_rmemory6_regression
```

## 5. Acceptance boundary

```text
telemetry_failure = non-fatal
security finding at prompt boundary = fail-closed
raw sensitive payload in event = zero
unbounded queue = zero
fake success correlation = zero
cross-process ledger corruption = zero
R-Memory-6 regression = green
```

## Kết luận

Cho phép kích hoạt Phase R-Memory-7 trong sandbox và controlled pilot. Chưa cho phép gọi telemetry production-ready hoặc dùng reuse metric làm bằng chứng memory effectiveness trước khi có typed event schema, redaction, bounded durability và correlation contract.

```text
GATE_1 = PASS_CONDITIONAL
SWARM_ACTIVATION = APPROVED_FOR_SANDBOX
PRODUCTION_TELEMETRY = REJECTED_PENDING_GUARDS
```

— Ký tên: **Opencode** (Senior Red Team Auditor) | 2026-10-18

<!-- TURN_END
turn_id: 498
speaker: Opencode
content_hash: phase_rmemory7_gate1_conditional_activation
-->
---
