# JKAI — 5 cải tiến vận hành (ROI)

> **AI OS:** Các mục dưới được gom trong kernel `core/os/request_orchestrator.py`. Xem `docs/JKAI_AI_OS.md`.

## 1. Clone repo ngoài

- Module: `core/utils/repo_clone.py`
- Mặc định: URL GitHub/GitLab + phân tích → `git clone --depth 1` → `scratch/projects/{owner}-{repo}-ref`
- Tắt clone: `chỉ readme`, `web-only`, `không clone` trong goal
- Env: `JKAI_AUTO_CLONE_GITHUB=true`, `JKAI_CLONE_TTL_DAYS=7`

## 2. DEEP pipeline đầy đủ (T2→T6)

- `core/utils/deep_routing.py` → `should_use_deep_pipeline_full()`
- Tự bật khi: phân tích, lỗi, workspace, repo vừa clone
- Ép: `JKAI_DEEP_PIPELINE_FULL=true|false`

## 3. Mission context

- `core/utils/mission_context.py` → `scratch/mission_context/{mission_id}.json`
- API payload: `mission_id`, `parent_mission_id` (Mission Control → control-plane → receptionist)
- Follow-up: gửi `parent_mission_id` hoặc cùng `mission_id` để nối context

## 4. Skill references

- `core/utils/skill_references.py`
- Ingress deck + Planner load `references/*.md` (cap token)
- Chuẩn: `docs/skill_authoring_standard.md`

## 5. Fast-fix path

- `core/utils/fast_fix_routing.py`
- Sửa một file (`.py`, …) → FAST, directive `[JKAI FAST-FIX]`
- Env: `JKAI_FAST_FIX_PATH=true`

## Triển khai

```bash
docker restart ai-brain ai-control-plane
# mission-control nếu đổi backend MC
```

## Prompt mẫu

**Clone + phân tích sâu:**

```text
Phân tích https://github.com/revfactory/harness so với JKAI — không sửa code.
```

**Chỉ web (không clone):**

```text
Phân tích https://github.com/revfactory/harness — chỉ đọc web/README, không clone.
```

**Tiếp tục mission:**

```json
{ "goal": "chi tiết file teams/pipeline", "mission_id": "my_mission", "parent_mission_id": "my_mission" }
```
