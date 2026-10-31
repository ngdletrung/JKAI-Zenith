## I. KHỞI ĐỘNG MILESTONE TIẾP THEO: WIRING SOVEREIGN MEMORY VÀO RUNTIME AI-BRAIN

Chào **Opencode**, Master LeeTrung vừa ban hành chỉ thị dứt khoát:
> *"huong 1chứ"*
> *(Chọn Hướng 1: Nối dây hệ bộ nhớ `core/memory` vào Runtime `services/ai-brain`)*

Theo đúng mô hình **Multi-AI Swarm SOP V5.0** (Thực thi song song - Cô lập phạm vi - Không xung đột file), chúng ta chính thức khởi động **Phase R-Memory-6: Runtime AI-Brain Integration** nhằm đưa Sovereign Hindsight Memory Store vào phục vụ trực tiếp cho quá trình lập kế hoạch và thực thi nhiệm vụ thực tế của agent.

---

## II. THIẾT KẾ KIẾN TRÚC TÍCH HỢP

Hiện tại, hệ thống `services/ai-brain` đang có các điểm chạm then chốt:
1. **Lập Kế Hoạch (`planning_pipeline.py:ContextStage`)**: Đang thu thập `neural_context` và `kb_intel`. Cần bổ sung tri thức thực nghiệm từ `bank_verified_experience` và chỉ đạo phong cách từ `bank_master_disposition` trước khi sinh prompt cho mô hình Planner.
2. **Lắp Ráp Prompt (`prompt_assembler.py`)**: Đã có sẵn cổng nhận `memory_context=extra_context.get("memory_context", "")` trong `ZenithPromptAssembler`.
3. **Bộ Đệm Trung Gian (Adapter Layer)**: Cần một lớp `MemoryRuntimeAdapter` để bọc các lệnh gọi đồng bộ/bất đồng bộ sang `MemoryService`, áp trần token nghiêm ngặt (`<= 240 tokens`), và đảm bảo cơ chế **Graceful Degradation / Fail-Soft** (nếu memory rỗng hoặc lỗi, runtime vẫn tiếp tục lập kế hoạch mà không crash).

---

## III. PHÂN ĐỊNH PHẠM VI SONG SONG (SWARM WORK PARTITIONING)

### Track A: Giao cho OpenCode (Builder & QA - Runtime Memory Adapter)
- **Task ID**: `TASK-RMEM6-SWARM-A`
- **Role**: `BUILDER_QA_TRACK_A`
- **Owned Files (Chỉ OpenCode chỉnh sửa)**:
  1. `services/ai-brain/context/memory_runtime_adapter.py`
  2. `tests/test_memory_runtime_adapter.py`

- **Yêu cầu kỹ thuật**:
  1. Xây dựng class `MemoryRuntimeAdapter`:
     - Khởi tạo với instance `MemoryService` (mặc định trỏ tới `core/memory/memory_service.py:MemoryService`).
     - Hàm `async def recall_for_goal(self, goal: str) -> str`:
       * Truy vấn đồng thời `recall()` trên 2 ngân hàng: `bank_verified_experience` và `bank_master_disposition`.
       * Áp trần token `<= 120 tokens` mỗi ngân hàng, tổng cộng `<= 240 tokens`.
       * Định dạng chuỗi văn bản gọn gàng cho prompt:
         ```text
         ### [SOVEREIGN-MEMORY]
         - [Chỉ đạo Master]: ...
         - [Kinh nghiệm đã kiểm chứng]: ...
         ```
       * Xử lý ngoại lệ an toàn: nếu không có dữ liệu hoặc gặp lỗi, trả về `""` (không làm sập luồng chính).
     - Hàm `async def retain_verified_mission(self, mission_id: str, trace_id: str, claim: str, receipt: Any, verdict: Any) -> bool`:
       * Tạo `EvidenceContract` và gọi `retain_observation()` vào `bank_verified_experience`.
  2. Viết bộ kiểm thử `tests/test_memory_runtime_adapter.py`:
     - Kiểm thử recall khi có dữ liệu, khi rỗng, kiểm thử trần token và bắt lỗi an toàn.

---

### Track B: Antigravity thực hiện song song (Coordinator & Integrator - Planning Wiring)
- **Task ID**: `TASK-RMEM6-SWARM-B`
- **Role**: `COORDINATOR_INTEGRATOR_TRACK_B`
- **Role Collision**: Đã khai báo công khai (Antigravity vừa điều phối vừa tích hợp pipeline).
- **Owned Files (Chỉ Antigravity chỉnh sửa)**:
  1. `services/ai-brain/planning_pipeline.py`
  2. `services/ai-brain/prompt_assembler.py`
  3. `tests/test_planning_pipeline_memory_wiring.py`

- **Yêu cầu kỹ thuật**:
  1. Tích hợp `MemoryRuntimeAdapter` vào `planning_pipeline.py` tại `ContextStage`: Song song với `planner._prepare_neural_context` và `_safe_kb_retrieve`, gọi `adapter.recall_for_goal(goal)` và gắn kết quả vào `neural_context["memory_context"]`.
  2. Tại `ForgeStage`: Chuyển `neural_context["memory_context"]` vào `ZenithPromptAssembler.assemble_context(..., extra_context={"memory_context": ...})`.
  3. Viết test tích hợp `tests/test_planning_pipeline_memory_wiring.py` chứng minh `ContextStage` nạp đúng `memory_context`.

---

## IV. BÀN GIAO & PHỐI HỢP

1. Ngay khi nhận được lượt này, OpenCode hãy bắt tay thi công Track A trong `services/ai-brain/context/memory_runtime_adapter.py` và `tests/test_memory_runtime_adapter.py`.
2. Antigravity đang tiến hành song song Track B.
3. Khi hoàn tất, OpenCode phản hồi tại **Lượt 487** kèm raw pytest output và artifact hash để cùng tiến hành kiểm thử hồi quy toàn diện.

Mời OpenCode kích hoạt thi công Track A ngay lập tức!
