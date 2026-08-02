# Harness → JKAI mapping (team + DEEP + skills)

Tham chiếu: [revfactory/harness](https://github.com/revfactory/harness) — **pattern team + skill references**, không dùng plugin Claude Code.

## Team patterns (L3 meta-factory)

| Harness pattern | JKAI `team_pattern` | Planner | Execution (T2–T6) | Mission Control |
|-----------------|---------------------|---------|-------------------|-----------------|
| Pipeline | `pipeline` | `Planner.generate_plan` tuần tự `depends_on` | T3 EXECUTOR theo DAG | Kế hoạch → Giải pháp |
| Fan-out / Fan-in | `fan_out_fan_in` | Bước recon/search `parallel=true` | T3 song song → bước merge | Kế hoạch (nhiều bước) |
| Expert pool | `expert_pool` | Skill deck + registry domain | Orchestrator chọn skill | Skill deck trong log |
| Producer → Reviewer | `producer_reviewer` | Báo cáo + tiêu chí review | **DEEP** + T5 **CRITIC** | Giải pháp + walkthrough |
| Supervisor | `supervisor` | Bước coordinator đầu | Meta-planner / planner agent | Kế hoạch |
| Hierarchical delegation | `hierarchical_delegation` | Phase cha → con | DAG nested milestones | Kế hoạch / Nhật ký |

**Suy luận pattern:** `core/utils/team_patterns.py` → `infer_team_pattern(goal)`  
**Prompt Planner:** `<TEAM_PATTERN_LAYER>` trong `services/ai-brain/planner.py`  
**Hậu xử lý:** `annotate_blueprint_dict`, `apply_pattern_to_steps`

## DEEP + review (phân tích)

| Loại yêu cầu | Routing | Ghi chú |
|--------------|---------|---------|
| Phân tích / so sánh / kiến trúc / harness / ROI | `goal_should_force_deep_for_analysis` | `JKAI_AUTO_DEEP_ON_ANALYSIS` (mặc định `true`) |
| URL GitHub chỉ đọc | `jkai_web_only_analysis` | Web scrape, không workspace agent |
| Lỗi / traceback | `goal_should_force_deep` | `JKAI_AUTO_DEEP_ON_ERROR` |
| scratch/projects | workspace enrich | Luôn DEEP |

File: `core/utils/deep_routing.py`, log receptionist: `receptionist_core.py`

## Skill references (progressive disclosure)

| Harness | JKAI |
|---------|------|
| `SKILL.md` ngắn | `intelligence/skills/<DECK>/<ID>/SKILL.md` |
| `references/*.md` | `references/` cùng thư mục skill |
| Load khi cần | `SkillDeckIndex.enrich_goal` + orchestrator retrieve |

Chuẩn: `docs/skill_authoring_standard.md`, mẫu: `intelligence/skills/_STANDARD/`

## Không áp dụng

- Claude Code plugin / MCP harness runtime
- Tự ghi registry skill khi phân tích (chỉ đề xuất trong walkthrough)

## Kiểm thử nhanh

```bash
cd /workspace && python -m pytest core/utils/test_team_patterns.py core/utils/test_deep_routing.py -q
```

Prompt mẫu (web-only):

```text
Phân tích https://github.com/revfactory/harness so với JKAI — chỉ README GitHub, không sửa code.
```

Kỳ vọng log: `DEEP — phân tích/so sánh/báo cáo`, `team_pattern: producer_reviewer`, không `WORKSPACE AGENT`.
