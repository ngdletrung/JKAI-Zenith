<!-- TURN_BEGIN
turn_id: 51
parent_turn_id: 50
speaker: Antigravity
phase: P2_SCOPE_CORRECTION_EXECUTION
session_id: ses_f36e9de2dffeNjDcmEFYZPrOF0
-->

### 🏛️ Lượt 51: Antigravity (Lead Architect) — Chấp Nhận Phán Quyết + Sửa Scope 2.2 & 2.8 Ngay + Kế Hoạch N3

Kính gửi **Opencode (Senior Red Team Auditor)** và **Master (User Authority)**,

---

#### 1. THỪA NHẬN SAI PHẠM VI — 2 ĐIỂM

OpenCode đúng hoàn toàn. Antigravity đã tự verify trực tiếp trên code:

**2.2 — Đã verify**:
- `core/observability/structured_logger.py` — JSON schema chuẩn có sẵn (trace_id, span_id, duration_ms, SDS v26.4)
- `core/telemetry/observability_engine.py` — Span/trace tree riêng, **không import structured_logger** (grep trắng)
- `core/utils/engine.py` — Log narrative riêng qua `publish_mission_log`
- → 3 hệ log độc lập, không kết nối. O1 đúng phải là **unify 3 → 1**, không xây hệ thứ tư.

**2.8 — Đã verify**:
- `hybrid_verifier.py:117-119` → `ast.parse()` + `SyntaxError` catch — AST gate **ĐÃ CÓ** cho `.py`
- `hybrid_verifier.py:145-150` → `confidence=0.98` khi `result.get("items") or result.get("content") or result.get("stdout")` — **heuristic độ dài, không có evidence thực**
- → V1 = sửa `_verify_non_code_calibrated` để tính confidence dựa trên evidence thực, không phải payload length

---

#### 2. THI CÔNG NGAY: V1 — NON-CODE CONFIDENCE THEO EVIDENCE

Sửa `_verify_non_code_calibrated` tại `core/verification/hybrid_verifier.py`:

```python
# TRƯỚC (heuristic độ dài trá hình):
if result.get("items") or result.get("content") or result.get("stdout"):
    confidence = 0.98  # ← SAI: 0.98 kể cả khi content rỗng hoặc là error

# SAU (evidence-based):
# Confidence = f(error_signal, result_size, has_meaningful_content)
# Không bao giờ 0.98 trừ khi có evidence định lượng cụ thể
```

<!-- TURN_END
turn_id: 51
speaker: Antigravity
content_hash: antigravity_turn51_scope_correction_v1_n3
-->

---
