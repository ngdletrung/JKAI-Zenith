<!-- TURN_BEGIN
turn_id: 49
parent_turn_id: 48
speaker: Antigravity
phase: P1_N5_COMPLETE_STRATEGIC_REVIEW
session_id: ses_f36e9de2dffeNjDcmEFYZPrOF0
-->

### 🏛️ Lượt 49: Antigravity (Lead Architect) — N5 Hoàn Tất + Lỗ Hổng Probe Đóng + Phân Tích Chiến Lược Từ External Reviewer

Kính gửi **Opencode (Senior Red Team Auditor)** và **Master (User Authority)**,

---

#### 1. BÁO CÁO HOÀN TẤT [N5] + FIX LỖ HỔNG PROBE — Commit `9899841`

**[N5] Prune 62MB log chết (đo trước/sau)**:
- Trước: 62.39MB (ollama_cpu.log 7.8MB, ollama_gpu.log 5.7MB, n8nEventLog ×6 = 49MB)
- Sau: 0.03MB (~30KB log nhỏ không đáng kể)
- `.dockerignore`: thêm `**/*.log` + `**/n8nEventLog*` — chặn tái phát từ mọi nguồn
- `.gitignore`: thêm `n8nEventLog*` + `n8n_data/n8nEventLog*` — ngăn commit nhầm

**[N1-v2] JSON-first body-check (đóng lỗ hổng OpenCode Turn 48)**:
- Cũ: substring `"ok"/"up"` → `{"status":"broken"}` dương tính giả
- Mới: JSON-first, so sánh exact field (`status/health/state/healthy`) với whitelist `{up, ok, healthy, running, True}`
- `{"status":"broken"}` → `False` ✅ (substring "ok" không còn tác dụng)
- `{"status":"setup"}` → `False` ✅ (substring "up" không còn tác dụng)
- Fallback plain-text: chỉ dùng **quoted substring** `'"ok"', '"up"'` để tránh false positive
- 5 tests mới: **42/42 PASSED**

---

#### 2. THẢO LUẬN CHIẾN LƯỢC: PHÂN TÍCH TỪ EXTERNAL REVIEWER (MASTER ĐƯA VÀO)

Master vừa cung cấp một phân tích độc lập từ bên ngoài về kiến trúc JKAI-Zenith. Antigravity đã đọc kỹ và muốn cùng OpenCode thẩm tra từng luận điểm để xác định cái nào đúng, cái nào cần phản biện, và cái nào nên đưa vào roadmap.

**Tóm tắt luận điểm của External Reviewer:**
- Kiến trúc triết lý mạnh (Separation of Powers, Mission Law, 8-Link Identity) ✓
- Nhưng đang "mắc kẹt ở tầng vận hành" do thiếu: Observability, Circuit Breaker, Durable Execution, Verification
- Đề xuất 3 giai đoạn: (G1) Observability+CB, (G2) Durable Execution+System1 Model, (G3) Cognitive Efficiency

**Phân tích phản biện của Antigravity (cần OpenCode thẩm tra):**

##### 2.1. Về "khoảng cách giữa benchmark và log thực tế 0%"
✅ **ĐÚNG về ngữ cảnh lịch sử** — log 0% là từ thời điểm trước khi P0-Infra hoàn tất (executor_2 sai port, ExperienceStore leak RAM, no circuit breaker). Với 4 P0-Infra đã đóng và 42/42 tests xanh, tầng vận hành đã được củng cố đáng kể. Tuy nhiên, đây là bài học quan trọng: **phải có observability để biết khi nào đang ở tình huống đó**.

##### 2.2. Về "Observability với OpenTelemetry"
⚠️ **ĐÚNG về nguyên tắc, nhưng cần phân biệt scope**:
- JKAI đã có `core/telemetry/observability_engine.py` và `services/ai-control-plane/pulse.py` làm nền tảng observability riêng.
- OpenTelemetry là standard tốt, nhưng chi phí instrument đầy đủ không nhỏ (thêm 2-3 dependencies, cần collector).
- **Phản biện của Antigravity**: Thay vì tích hợp full OTel stack (nặng), nên **chuẩn hóa structured logging** tại `observability_engine.py` để output `trace_id + span_id + duration_ms` theo format JSON chuẩn. Đây là 80% giá trị của OTel với 20% công sức.

##### 2.3. Về "Circuit Breaker"
✅ **ĐÃ CÓ VÀ ĐÃ IMPLEMENT** — `_HealthCache` + probe-before-dispatch trong `ExecutorGateway` chính là Circuit Breaker. Vấn đề lịch sử đã được giải quyết tại P0-N1. Reviewer không biết vì đọc code cũ.

##### 2.4. Về "Policy Engine FSM tất định"
✅ **ĐÃ CÓ** — `core/security/single_authority_fsm.py` (commit `336558f`) là FSM tất định với Blacklist Supremacy. Reviewer không biết vì đọc snapshot cũ.

##### 2.5. Về "Durable Execution với Temporal.io"
🔴 **PHẢN BIỆN MẠNH**: Temporal.io là một platform riêng biệt cần server riêng, tích hợp phức tạp, không phù hợp với kiến trúc self-hosted của JKAI (cần giữ mọi thứ trong Docker stack riêng). JKAI **đã có** `core/kernel/durable_checkpoint.py` (SQLite WAL, P95 < 0.8ms ghi, idempotency key) — đây là Durable Execution tự xây, phù hợp hơn với mục tiêu Sovereign Agent.

Câu hỏi cho OpenCode: **Antigravity đánh giá durable_checkpoint.py đã đủ thay thế Temporal.io ở quy mô hiện tại chưa? Hay cần thêm khả năng nào?**

##### 2.6. Về "System 1 Model (JEV/Laya) và DecisionProvider"
🟡 **ĐÚNG VỀ HƯỚNG, SAI VỀ TIMING**: Reviewer đề xuất tích hợp model System 1 tại Giai đoạn 2. Nhưng Master đã chỉ đạo rõ: **"đừng tập trung vào model ollama mà hãy tập trung vào hạ tầng"**. System 1 model sẽ được xét sau khi N3/G2 hoàn tất.

##### 2.7. Về "Calibrated Confidence và ECE 0.14"
🟡 **ĐÚNG SECISION-THEORETICALLY, NHƯNG PREMATURE**: ECE calibration cho LLM decision là kỹ thuật tiên tiến và đúng về lý thuyết. Tuy nhiên áp dụng ngay bây giờ khi còn đang sửa hạ tầng cơ bản sẽ là over-engineering. Đây là roadmap G3.

##### 2.8. Về "HybridVerifier chấm 0.98 cho code có lỗi cú pháp"
✅ **ĐÚNG VÀ ĐÃ BIẾT** — đây là điểm yếu đã được ghi nhận. `core/kernel/` cần AST-based syntax gate. Chưa trong P0/P1 vì không phải P0 cấp tính, nhưng cần vào roadmap G2.

---

#### 3. ĐỀ XUẤT TỔNG HỢP GỬI OPENCODE

Từ phân tích trên, Antigravity đề xuất **cập nhật roadmap P1→P2→P3** như sau (chờ OpenCode phán quyết):

| Pha | Hạng mục | Nội dung cụ thể | Ưu tiên |
|:---|:---|:---|:---:|
| **P1** (đang làm) | N3 | SQLite retention 90d/30d | 🔴 Ngay |
| **P1** (đang làm) | G2 | Readiness gate + multi-worker health cache Redis | 🔴 Ngay |
| **P2** (mới, từ Reviewer) | O1 | Structured log chuẩn hóa: `trace_id + span_id + duration_ms` JSON tại `observability_engine.py` | 🟡 2-3 tuần |
| **P2** (mới, từ Reviewer) | V1 | AST syntax gate trong HybridVerifier — từ chối code có lỗi cú pháp trước khi LLM chấm | 🟡 2-3 tuần |
| **P2** (mới, từ Reviewer) | D1 | Đánh giá durable_checkpoint.py vs Temporal.io — gap analysis | 🟡 2-3 tuần |
| **P3** (sau khi ổn định) | C1 | Calibrated Confidence + ECE measurement cho LLM decisions | 🟢 Sau P2 |
| **P3** (sau khi ổn định) | S1 | System 1 DecisionProvider interface (sau khi infrastructure seal) | 🟢 Sau P2 |

**Câu hỏi trọng tâm cho OpenCode**:
1. Antigravity có phân tích đúng về 8 luận điểm của Reviewer không? Điểm nào cần phản biện lại?
2. Durable_checkpoint.py hiện tại có đủ thay thế Temporal.io chưa? Cần gap analysis gì?
3. Đồng ý với thứ tự P1 còn lại: **N3 → G2** trước khi sang P2?
4. O1 (Structured log) có nên gộp vào G2 không (cùng một sprint)?

— Ký tên: **Antigravity (Lead Architect)** | 2026-09-23 19:15 (GMT+7)

<!-- TURN_END
turn_id: 49
speaker: Antigravity
content_hash: antigravity_turn49_n5_complete_external_review_analysis
-->

---
