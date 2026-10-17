# Kế hoạch triển khai: Chế độ thảo luận Cloud cho JKAI (Discuss-Only Policy)

> **Nguyên tắc khóa (Master duyệt):** JKAI chỉ gọi model cloud khi người dùng ra lệnh thảo luận về một dự án cụ thể. Mọi task khác chạy local 100%. Không escalate tự động.

## 1. Mục tiêu

- Cho phép Master thảo luận dự án với model mạnh (DeepSeek reasoner / Gemini flash / OpenAI dự phòng) theo từng mission được chỉ định.
- Dữ liệu INTERNAL không bao giờ rời máy ở dạng thô: redact + canary + log hash-chain bắt buộc.
- Tri thức thu được chỉ vào memory qua hypothesis-gate (test local pass mới ghi).

## 2. Phạm vi (Scope)

**Làm:**
- Mode `discuss` mới trong pipeline (kế bên `fast/deep/agentic/auto`).
- Chọn model cloud theo chỉ định + fallback theo thứ tự DeepSeek → Gemini → OpenAI.
- Redact PII/secret + quét canary trước mọi egress.
- Egress log hash-chain + hạn mức call/mission.
- Thu hoạch ý hay qua hypothesis-gate.

**Không làm (cấm):**
- Escalate tự động ra cloud khi local fail (chưa duyệt).
- Gửi nguyên tài liệu INTERNAL, secret, key, đường dẫn nội bộ.
- Học trực tiếp response cloud vào memory/skills.
- Tắt killswitch toàn cục (`JKAI_LOCAL_ONLY` giữ mặc định 1).

## 3. Kiến trúc

```
Master lệnh discuss (dự án X, model Y)
  → Controller: gắn cờ allow_cloud=True cho đúng mission này
  → Redact: pii_scrubber + canary scan (fail → dừng + báo)
  → Egress log (hash-chain) TRƯỚC khi gửi
  → Gọi cloud API (timeout + retry giới hạn + hạn mức call)
  → Response về → gắn nhãn nguồn cloud, lưu local theo mission
  → Kết thúc: trích ý hay → hypothesis test local → pass mới vào memory
```

## 4. Module và file chạm

| # | Việc | File | Ghi chú |
|---|------|------|---------|
| 1 | Thêm mode `discuss` | `services/ai-control-plane/main.py` (`VALID_MODES`) | Từ chối mode lạ như hiện tại |
| 2 | Nhánh controller discuss | `core/os/cognition/adaptive_controller.py` | Strategy mới `CLOUD_DISCUSS`, chỉ khi cờ mission bật |
| 3 | Canary guard | `core/security/canary_guard.py` (mới) | Chèn + quét canary token tài liệu nội bộ |
| 4 | Egress log hash-chain | `core/security/egress_log.py` (mới) | Tái dùng pattern exam ledger: prev_hash → entry_hash |
| 5 | Móc redact vào đường cloud | `core/utils/engine.py` (đoạn cloud 1365-1383) | Redact + canary + log trước mọi call |
| 6 | Credit/hạn mức | `adaptive_controller.py` hoặc config | Tối đa N call/mission + N call/ngày, hết thì dừng xin ý kiến |
| 7 | Hypothesis-gate | Kế thừa A5 `verify_or_rollback_update` | Response cloud = giả thuyết, test local mới ghi memory |
| 8 | Cấu hình key | `rules_software.md` + env | Key trong env, không hardcode, không log |

## 5. Danh sách test khóa (TDD trước, code sau)

1. `test_discuss_requires_explicit_flag`: mission không cờ → cloud bị từ chối dù model là `gemini-*`.
2. `test_canary_blocks_leak`: prompt chứa canary → chặn 100%, không gửi.
3. `test_redact_strips_secrets`: prompt có API key/đường dẫn nội bộ → đã lột trước khi gửi (assert trên payload đã redact).
4. `test_egress_log_chain`: sửa 1 entry → chain gãy (verify fail).
5. `test_quota_stops`: hết hạn mức → dừng + báo, không gửi thêm.
6. `test_hypothesis_gate`: response cloud chưa qua test local → không vào memory.
7. `test_local_untouched`: bật discuss không ảnh hưởng pipeline local (full sprint xanh).

## 6. Tiêu chí nghiệm thu

- 7/7 test trên xanh + full sprint không regression.
- Demo 1 mission discuss thật (DeepSeek reasoner): log đủ redact + canary + hash-chain + hạn mức.
- Killswitch toàn cục vẫn ON sau khi xong (chỉ mission discuss được egress).
- Master duyệt log mẫu mới coi là xong.

## 7. Tiến độ dự kiến

| Đợt | Việc | Thời gian |
|-----|------|-----------|
| 1 | Canary guard + egress log + test 2,4 | 3 ngày |
| 2 | Mode discuss + nhánh controller + redact + test 1,3,5 | 1 tuần |
| 3 | Hypothesis-gate + demo live + test 6,7 | 3-4 ngày |

## 8. Rủi ro và cách chặn

| Rủi ro | Chặn bằng |
|--------|-----------|
| Lộ tài liệu qua prompt | Redact + canary + chỉ mission có cờ |
| Mosaic attack (nhiều câu vô hại ghép thành tranh nội bộ) | Hạn mức call + log để audit, cảnh báo Master khi discuss cùng dự án quá dày |
| Học sai từ cloud hallucinate | Hypothesis-gate, không ghi thẳng memory |
| Cháy tiền API | Hạn mức mission/ngày + ước tính chi phí trước call |
| Key lộ | Env-only, revoke key đã dán chat, cấp bộ mới cho chính thức |

---
*Lập bởi Opencode (Red Team) theo chỉ đạo Master. Antigravity thẩm định kỹ thuật và thi công TDD theo đúng 7 test khóa trên.*
