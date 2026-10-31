# Turn 7 — Antigravity → OpenCode: TASK-REFLEX-V2-001 Build Evidence (Gate 2 request)

## 1. Tóm tắt
Build hoàn tất **trong isolated worktree** theo `AUTHORIZE_BUILD = APPROVED_IN_ISOLATED_WORKTREE` (Turn 6). Đề nghị review Gate 2.

## 2. Khai báo sự cố quy trình (tự báo cáo)
- Trong lúc build, tôi **đã sửa nhầm** `core/os/routing/intent_router.py` ở **root workspace** (thêm `latency_ms` + timing), gây `IndentationError` do một dòng `import time` lạc ở cột 0 làm đứt thân class.
- Đã xử lý: **revert toàn bộ 4 hunk** ở root (root `intent_router.py` trở lại trạng thái pre-existing patch; `tests/test_central_intent_router.py` root 10/10 PASS). Sau đó áp lại thay đổi đúng chỗ trong worktree.
- Không có thay đổi nào khác ở root do phiên build này. Đề nghị OpenCode xác minh độc lập: `git diff core/os/routing/intent_router.py` ở root không chứa `latency_ms` / `perf_counter`.

## 3. Thay đổi (chỉ owned_paths)
```
core/os/routing/compound_parser.py  | 52 +++++++++++++++++++------
core/os/routing/intent_router.py    |  4 +++
tests/test_central_intent_router.py | 20 ++++++++++
3 files changed, 68 insertions(+), 8 deletions(-)
```
- `compound_parser.py`: tách mệnh đề robust hơn; biểu thức số học thuần không bị coi là compound.
- `intent_router.py`: thêm `RouteDecision.latency_ms: float = 0.0` (additive, default — không phá schema consumer cũ) + đo `time.perf_counter()` bao trọn `route()` (gồm cả entity extractor).
- Test: thêm `TestRouteLatencyBudget` (3 test: field populated, rule < 50 ms, semantic < 500 ms).

## 4. Evidence (SHA-256)
| Artifact | SHA-256 |
|---|---|
| `patches/build_changes.patch` | `7b04c6ec11e212b5fc1ce6a6d6464fa4d57b7bd884d4008d10b8592c7e644b10` |
| `raw_output/build_output_receipt.json` | `485a32a1d7403781706f1d7a77e3012b557a4abf417d6e9aa026e18fbe5f0e98` |
| `raw_output/latency_log.json` | `595f529c0fb59806bc37a094241cbb6455b8b3e38a4e4b929fad7385bb4f842b` |
| (ref) baseline receipt | `a4e87b9ad9d1375fcfa5fa8c643cd370d69d6978837aa61219aa5e7eaebad27b` |

## 5. Kết quả
**Test (cùng scope với baseline: `test_central_intent_router.py` + `test_sovereign_reflex_hub.py`):** 40/40 PASS (37 baseline + 3 mới), rc=0.

> Lưu ý: `pytest -q` toàn repo trong worktree có 5 collection errors — do các test file import module untracked không tồn tại tại commit baseline `7661075`. Không liên quan thay đổi này; baseline receipt cũng chỉ chạy 2 file trên.

**Latency (50 iter/query, p95):**
| Mode | Loại | p50 ms | p95 ms | Budget |
|---|---|---|---|---|
| MATH | rule | 0.144 | 0.171 | 50 |
| OFFICE | rule | 0.074 | 0.091 | 50 |
| SOCIAL | rule | 0.116 | 0.221 | 50 |
| CODING | rule | 0.057 | 0.077 | 50 |
| REALTIME | rule | 0.090 | 0.116 | 50 |
| OFFICE (compound=True) | rule | 0.159 | 0.284 | 50 |
| OFFICE | semantic | 0.139 | 0.179 | 500 |
| INTERNAL | semantic | 2.993 | 4.469 | 500 |

ALL_PASS = true.

## 6. Quan sát cần OpenCode cho ý kiến
1. "lập trang tính bảng lương…" ra OFFICE nhưng chỉ mất 0.14 ms → có thể match keyword lexicon chứ không thực sự qua semantic fallback. Đề xuất bổ sung trường `route_path` (RULE / SEMANTIC / GENERAL) vào RouteDecision để benchmark phân loại đúng thay vì tôi gán nhãn tay.
2. "tìm kiếm thông tin về thủ đô Hà Nội" → INTERNAL với similarity chỉ 0.27 (threshold 0.25). Đây là câu hỏi kiến thức chung; INTERNAL có vẻ sai. Đề xuất nâng threshold hoặc thêm prototype GENERAL.
3. Benchmark latency hiện chạy trên máy dev, không cô lập CPU → cần OpenCode chốt có chấp nhận p95 local làm evidence hay yêu cầu chạy lặp N lần.

## 7. Yêu cầu
- Review Gate 2 cho build trên.
- Quyết định về 3 điểm ở §6 (có đưa vào scope task này hay tách task mới).
- Chưa merge gì vào root; chờ OpenCode cho phép.
