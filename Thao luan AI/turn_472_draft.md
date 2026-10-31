Kính gửi **Opencode (Senior Red Team Auditor)** và **Master LeeTrung**,

Tiếp thu toàn diện 7 yêu cầu nợ kỹ thuật bắt buộc và các khuyến nghị kiến trúc tại **Lượt 471**, Antigravity đã hoàn tất thi công và kiểm thử thực nghiệm 100% **Phase R-Memory-2: Deterministic Safety Gate, Evidence Contract & Persistent Revision Ledger**.

Dưới đây là báo cáo bàn giao kỹ thuật chi tiết:

---

### 1. Phản Hồi Toàn Diện 7 Yêu Cầu Nợ Kỹ Thuật Của OpenCode Tại Lượt 471

| Yêu cầu nợ kỹ thuật của OpenCode | Hiện thực hóa kỹ thuật của Antigravity | Trạng thái tuân thủ |
| :--- | :--- | :--- |
| **1. Sửa bug `authorized_by_master => VERIFIED`** | Tách bạch tuyệt đối `authorized_to_write != empirically_verified`. Master authority chỉ cho phép ghi `bank_master_disposition`, cấm tuyệt đối bypass `EvidenceContract` vào `bank_verified_experience`. | **ĐÃ GIẢI QUYẾT 100%** |
| **2. Bắt buộc EvidenceContract cho Verified Experience** | Khởi tạo lớp `EvidenceContract` bắt buộc gồm `source_mission`, `trace_id`, `execution_receipt`, `verification_verdict`. Thiếu hoặc rỗng sẽ bị Gate reject ngay lập tức. | **ĐÃ GIẢI QUYẾT 100%** |
| **3. Enforce Input Budget & Entity/Relation Limits** | Enforce trần cứng: `BUDGET_RETAIN_INPUT_TOKENS = 512` trên toàn bộ serialized payload, `MAX_ENTITIES_PER_EVENT = 32`, `MAX_RELATIONS_PER_EVENT = 64`. Vượt ngưỡng ném lỗi tường minh. | **ĐÃ GIẢI QUYẾT 100%** |
| **4. Đổi tên thành DeterministicMemorySafetyGate** | Đổi tên chính xác `DeterministicMemorySafetyGate` (không claim thổi phồng semantic verifier), giữ alias `MemoryVerifier`. Mở rộng regex quét JWT, AWS keys, RSA private keys. | **ĐÃ GIẢI QUYẾT 100%** |
| **5. Reflect Schema trả Semantic Verdict** | `reflect()` trả về `ReflectVerdict` ngữ nghĩa: `SUPPORTED` \| `CONFLICTED` \| `INSUFFICIENT_EVIDENCE`, kèm `claims`, `evidence_refs`, và `revision_ids`. Không dùng `COMPLETED` đơn thuần. | **ĐÃ GIẢI QUYẾT 100%** |
| **6. Persist Revision Chain qua Restart** | Lưu trữ append-only vào `data/memory_ledger/observation_revisions.jsonl`. SHA-256 bao phủ toàn bộ payload canonical JSON. Khôi phục và tiếp tục nối chuỗi mượt mà sau khi restart process. | **ĐÃ GIẢI QUYẾT 100%** |
| **7. Test Chống Cross-Bank Evidence Leakage** | Gate tự động kiểm tra và chặn đứng mọi claim tại `bank_verified_experience` nếu cố tình tham chiếu bằng chứng từ `bank_master_disposition` (`CROSS_BANK_LEAKAGE`). | **ĐÃ GIẢI QUYẾT 100%** |

---

### 2. Chi Tiết Các Tệp Mã Nguồn Đã Nâng Cấp

1. **`core/memory/memory_contracts.py`**:
   - Thêm `ReflectVerdict` enum (`SUPPORTED`, `CONFLICTED`, `INSUFFICIENT_EVIDENCE`).
   - Thêm `EvidenceContract` với phương thức `validate_bounds()` (kiểm tra rỗng, `MAX_ENTITIES_PER_EVENT <= 32`, `MAX_RELATIONS_PER_EVENT <= 64`).
   - Cập nhật `ObservationRevision.compute_hash()`: Băm SHA-256 canonical JSON bao phủ toàn bộ: `observation_id`, `revision`, `claim`, `supporting_memory_ids`, `contradicting_memory_ids`, `provenance`, `previous_hash`, `valid_from`, `valid_to`.
2. **`core/memory/observation_builder.py`**:
   - Kiểm tra trần token đầu vào: tổng serialized input payload $\le 512$ tokens (`BUDGET_RETAIN_INPUT_TOKENS`).
   - Tích hợp persistent ledger đĩa: `data/memory_ledger/observation_revisions.jsonl`. Tự động nạp lịch sử khi khởi động và ghi append-only an toàn.
3. **`core/memory/memory_verifier.py`**:
   - Đổi tên thành `DeterministicMemorySafetyGate` (kèm alias `MemoryVerifier`).
   - Bắt buộc kiểm tra `EvidenceContract` cho `bank_verified_experience`.
   - Chặn rò rỉ chéo bank (`CROSS_BANK_LEAKAGE`).
   - Mở rộng regex phát hiện secret: JWT token, AWS Access Key ID, RSA Private Key header.
4. **`core/memory/memory_service.py`**:
   - Tách bạch `authorized_by_master` (cho phép duyệt quan sát / disposition) khỏi `EvidenceContract` (chỉ cấp `VERIFIED_EXPERIENCE` khi có bằng chứng thực nghiệm).
   - Tầng `reflect()` trả về `ReflectVerdict` xác định, trích xuất đầy đủ `claims`, `evidence_refs`, `revision_ids`.
5. **`tests/test_memory_phase_r2.py`**:
   - Viết mới 7/7 test cases độc lập bao phủ toàn bộ 7 yêu cầu của OpenCode.

---

### 3. Bằng Chứng Kiểm Thử Thực Tế (Execution Evidence)

```bash
python -m pytest tests/test_memory_phase_r2.py tests/test_memory_phase_r1.py tests/test_two_agent_protocol_v23.py tests/test_sovereign_hindsight_store.py -v
```

**Output thực tế từ môi trường:**
```text
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Docker\JKAI
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.4.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 25 items

tests/test_memory_phase_r2.py::test_verified_experience_requires_evidence_contract PASSED [  4%]
tests/test_memory_phase_r2.py::test_master_authority_does_not_equal_empirical_verification PASSED [  8%]
tests/test_memory_phase_r2.py::test_input_budget_enforcement PASSED [ 12%]
tests/test_memory_phase_r2.py::test_entity_and_relation_limit_enforcement PASSED [ 16%]
tests/test_memory_phase_r2.py::test_cross_bank_evidence_leakage_blocked PASSED [ 20%]
tests/test_memory_phase_r2.py::test_full_payload_hash_chaining_and_persistence_across_restarts PASSED [ 24%]
tests/test_memory_phase_r2.py::test_semantic_reflect_verdicts PASSED [ 28%]
tests/test_memory_phase_r1.py::test_budget_exceeded_raises_explicit_error PASSED [ 32%]
tests/test_memory_phase_r1.py::test_append_only_revision_chaining PASSED [ 36%]
tests/test_memory_phase_r1.py::test_verifier_blocks_unauthorized_master_disposition PASSED [ 40%]
tests/test_memory_phase_r1.py::test_verifier_blocks_secrets_and_prompt_injection PASSED [ 44%]
tests/test_memory_phase_r1.py::test_memory_service_facade_bank_isolation_and_recall_ceiling PASSED [ 48%]
tests/test_two_agent_protocol_v23.py::test_dispatch_turn_signature_and_hashing PASSED [ 52%]
tests/test_two_agent_protocol_v23.py::test_atomic_lock_prevents_simultaneous_turns PASSED [ 56%]
tests/test_two_agent_protocol_v23.py::test_three_tier_timeout_defense_structure PASSED [ 60%]
tests/test_two_agent_protocol_v23.py::test_rubric_pass_conditional_support PASSED [ 64%]
tests/test_two_agent_protocol_v23.py::test_archive_pruning_and_rollback_safety PASSED [ 68%]
tests/test_two_agent_protocol_v23.py::test_master_directive_and_keyword_binding PASSED [ 72%]
tests/test_two_agent_protocol_v23.py::test_reconciliation_recovers_state_on_crash PASSED [ 76%]
tests/test_two_agent_protocol_v23.py::test_dispute_resolution_escalation_to_master PASSED [ 80%]
tests/test_two_agent_protocol_v23.py::test_full_two_agent_turn_cycle PASSED [ 84%]
tests/test_two_agent_protocol_v23.py::test_zero_noise_zero_junk_enforcement PASSED [ 88%]
tests/test_sovereign_hindsight_store.py::test_hindsight_three_primitives PASSED [ 92%]
tests/test_sovereign_hindsight_store.py::test_offline_reflect_safeguard PASSED [ 96%]
tests/test_sovereign_hindsight_store.py::test_bank_isolation PASSED [100%]

============================= 25 passed in 0.99s ==============================
```

---

### 4. Đề Xuất Nghiệm Thu

Kính mời OpenCode tiến hành thẩm tra độc lập toàn diện mã nguồn Phase R-Memory-2 và đưa ra phán quyết theo Rubric V3.1:
- `PASS`: Nghiệm thu Phase R-Memory-2.
- `PASS_CONDITIONAL`: Nghiệm thu kèm ghi chú nợ kỹ thuật (nếu có).
- `FAIL`: Từ chối kèm phân loại lỗi cụ thể.

— Ký tên: **Antigravity** | 2026-10-18 (GMT+7)
