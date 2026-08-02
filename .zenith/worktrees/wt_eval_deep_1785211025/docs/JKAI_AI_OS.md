# JKAI — AI Operating System

JKAI không phải “một chatbot + vài if”. Đây là **AI OS**: mọi yêu cầu của Master đi qua **một kernel điều phối**, rồi mới tới pipeline thực thi.

## Kiến trúc tầng

```text
Master (MC / API / Telegram)
        ↓
   Ingress Gateway (firewall, trace_id, mode)
        ↓
   AI OS Kernel — orchestrate_request()     ← core/os/request_orchestrator.py
        ↓
   ┌─────┴─────┬─────────────┬──────────────┐
   Reflex    Skill Deck    Mission Ctx    Clone/Workspace
        ↓
   Intent (OS + IntentCortex) → Pipeline
        ↓
   Receptionist / TaskManager / Executor
        ↓
   Mission Control (log, artifact, context pack)
```

## Pipeline (không giới hạn một loại việc)

| Pipeline | Khi nào |
|----------|---------|
| `reflex` | Câu hỏi đã có trong bộ nhớ chung |
| `inspect` | Rà soát skill deck (#NNNN) |
| `fast_chat` | Hội thoại đơn giản |
| `fast_fix` | Sửa một file, thay đổi tối thiểu |
| `fast` | Phản xạ + tool, không CRITIC đầy đủ |
| `deep` | Plan + ReAct + CRITIC plan |
| `deep_full` | T2→T6 (recon, context, forge, execute, critic, summarize) |
| `cursor_agent` | Workspace local: list/read/run/fix trong scope |

## OS Intent (phân loại tổng quát)

`core/os/intent_taxonomy.py`: `SOCIAL`, `RESEARCH`, `ANALYZE`, `DEBUG`, `BUILD`, `FIX`, `AUDIT`, `OPERATE`, `MULTIMODAL`, `GENERAL`.

Capability tags: `remote_repo`, `local_workspace`, `web_only`, `single_file_fix`, `skill_deck`, `ops`, …

## Nguyên tắc “mọi vấn đề”

1. **Không hardcode một repo** — GitHub clone / web-only / local workspace do policy, không tên harness cố định.
2. **Enrich trước, execute sau** — skill deck, references, mission context, clone đều trong kernel.
3. **Mode tự chọn** — `auto` + IntentCortex + deep_routing; Master vẫn ép `/deep`, `/fast`.
4. **Nhớ mission** — `scratch/mission_context/` + `parent_mission_id`.
5. **Mở rộng** — thêm intent/pipeline mới trong `intent_taxonomy` + `request_orchestrator`, không rải if trong receptionist.

## Module liên quan

| Module | Vai trò |
|--------|---------|
| `core/os/request_orchestrator.py` | Kernel duy nhất |
| `core/utils/deep_routing.py` | DEEP khi lỗi / phân tích |
| `core/utils/team_patterns.py` | Harness team trên plan |
| `core/utils/execution_policy.py` | Policy từng bước executor |
| `core/utils/intent_cortex.py` | Lexicon + complexity |
| `services/ai-control-plane/task_manager.py` | Mission DAG / budget |
| `docs/jkai_five_improvements.md` | 5 cải tiến ROI gần đây |

## Ví dụ (cùng kernel, khác pipeline)

- *"Xin chào"* → `fast_chat`
- *"Phân tích https://github.com/.../repo"* → clone + `deep_full`
- *"Chỉ đọc web/README …"* → `web_only` + `deep`
- *"Sửa typo file X.py"* → `fast_fix`
- *"Kiểm tra scratch/projects/app"* → `cursor_agent` hoặc `deep`
- *"Docker restart ai-brain lỗi"* → `DEBUG` + `deep_full`

## Triển khai

Sau đổi kernel: `docker restart ai-brain`

Log Mission Control: dòng `AI OS: intent=... pipeline=...`

## MCP (Cursor / VS Code)

MCP server: `tools/jkai-mcp/` — xem `tools/jkai-mcp/README.md` và `mcp-config.example.json`.
