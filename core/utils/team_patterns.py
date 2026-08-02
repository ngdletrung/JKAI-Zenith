"""
Harness-inspired team architecture patterns for JKAI Planner / DEEP routing.

Inspired by https://github.com/revfactory/harness (L3 meta-factory) — patterns only,
not Claude Code plugin runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Pattern IDs align with Harness naming for cross-doc clarity
PATTERN_PIPELINE = "pipeline"
PATTERN_FAN_OUT_IN = "fan_out_fan_in"
PATTERN_EXPERT_POOL = "expert_pool"
PATTERN_PRODUCER_REVIEWER = "producer_reviewer"
PATTERN_SUPERVISOR = "supervisor"
PATTERN_HIERARCHICAL = "hierarchical_delegation"

_ANALYSIS_RE = re.compile(
    r"\b(phân tích|phan tich|so sánh|so sanh|đánh giá|danh gia|đối chiếu|doi chieu|"
    r"review|analyze|compare|assess|architecture|kiến trúc|kien truc|"
    r"báo cáo|bao cao|kết luận|ket luan|harness|cải tiến cho jkai|cai tien cho jkai)\b",
    re.IGNORECASE,
)
_PARALLEL_RE = re.compile(
    r"\b(song song|parallel|đồng thời|dong thoi|nhiều góc|nhieu goc|"
    r"fan[- ]?out|đa nguồn|da nguon|tất cả các khía cạnh)\b",
    re.IGNORECASE,
)
_RESEARCH_RE = re.compile(
    r"\b(nghiên cứu|nghien cuu|research|tìm kiếm|tim kiem|map-reduce|"
    r"thu thập|thu thap|investigate)\b",
    re.IGNORECASE,
)
_HIERARCHICAL_RE = re.compile(
    r"\b(phân rã|phan ra|chia nhỏ|chia nho|hierarchical|delegat|"
    r"từng module|tung module|subtask)\b",
    re.IGNORECASE,
)
_SUPERVISOR_RE = re.compile(
    r"\b(supervisor|điều phối|dieu phoi|orchestrat|coordinator|điều hành mission)\b",
    re.IGNORECASE,
)
_EXPERT_POOL_RE = re.compile(
    r"\b(chuyên gia|chuyen gia|expert pool|theo domain|skill deck|#)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TeamPattern:
    id: str
    label_vi: str
    requires_deep_pipeline: bool
    requires_critic: bool
    planner_hints: str


_PATTERNS: Dict[str, TeamPattern] = {
    PATTERN_PIPELINE: TeamPattern(
        id=PATTERN_PIPELINE,
        label_vi="Pipeline (tuần tự)",
        requires_deep_pipeline=False,
        requires_critic=False,
        planner_hints="Các bước phụ thuộc depends_on; ít parallel trừ recon độc lập.",
    ),
    PATTERN_FAN_OUT_IN: TeamPattern(
        id=PATTERN_FAN_OUT_IN,
        label_vi="Fan-out / Fan-in",
        requires_deep_pipeline=True,
        requires_critic=False,
        planner_hints="Gom bước độc lập parallel=true (recon, search), sau đó 1 bước merge/synthesize.",
    ),
    PATTERN_EXPERT_POOL: TeamPattern(
        id=PATTERN_EXPERT_POOL,
        label_vi="Expert pool",
        requires_deep_pipeline=False,
        requires_critic=False,
        planner_hints="Chọn skill/agent theo domain; tránh một tool làm hết.",
    ),
    PATTERN_PRODUCER_REVIEWER: TeamPattern(
        id=PATTERN_PRODUCER_REVIEWER,
        label_vi="Producer → Reviewer",
        requires_deep_pipeline=True,
        requires_critic=True,
        planner_hints="Bước sinh báo cáo/plan trước; bước cuối verification hoặc agent_critic mindset; DEEP T5 CRITIC bắt buộc.",
    ),
    PATTERN_SUPERVISOR: TeamPattern(
        id=PATTERN_SUPERVISOR,
        label_vi="Supervisor",
        requires_deep_pipeline=True,
        requires_critic=False,
        planner_hints="Bước 1 coordinator/planner phân task; executor steps phụ thuộc supervisor.",
    ),
    PATTERN_HIERARCHICAL: TeamPattern(
        id=PATTERN_HIERARCHICAL,
        label_vi="Phân cấp",
        requires_deep_pipeline=True,
        requires_critic=False,
        planner_hints="Chia phase: parent milestone → child steps với depends_on rõ.",
    ),
}


def infer_team_pattern(goal: str) -> TeamPattern:
    g = (goal or "").strip()
    if not g:
        return _PATTERNS[PATTERN_PIPELINE]
    if _ANALYSIS_RE.search(g):
        return _PATTERNS[PATTERN_PRODUCER_REVIEWER]
    if _PARALLEL_RE.search(g):
        return _PATTERNS[PATTERN_FAN_OUT_IN]
    if _HIERARCHICAL_RE.search(g):
        return _PATTERNS[PATTERN_HIERARCHICAL]
    if _SUPERVISOR_RE.search(g):
        return _PATTERNS[PATTERN_SUPERVISOR]
    if _EXPERT_POOL_RE.search(g) or "#" in g:
        return _PATTERNS[PATTERN_EXPERT_POOL]
    if _RESEARCH_RE.search(g):
        return _PATTERNS[PATTERN_FAN_OUT_IN]
    return _PATTERNS[PATTERN_PIPELINE]


def pattern_prompt_block(pattern: Optional[TeamPattern] = None, goal: str = "") -> str:
    p = pattern or infer_team_pattern(goal)
    return f"""
<TEAM_PATTERN_LAYER harness_inspired="true">
Pattern được chọn: {p.id} ({p.label_vi})
Gợi ý lập kế hoạch: {p.planner_hints}
- pipeline: bước tuần tự, depends_on rõ.
- fan_out_fan_in: parallel recon/search → một bước tổng hợp.
- expert_pool: skill phù hợp từ registry/deck, không hallucinate tool.
- producer_reviewer: deliverable + tiêu chí review; phù hợp phân tích/so sánh/báo cáo.
- supervisor: bước điều phối đầu (coordinator/planner agent).
- hierarchical_delegation: milestone cha → con.
Trường Blueprint.team_pattern PHẢI = "{p.id}".
</TEAM_PATTERN_LAYER>
""".strip()


def annotate_blueprint_dict(blueprint: Dict[str, Any], pattern: Optional[TeamPattern] = None, goal: str = "") -> Dict[str, Any]:
    """Gắn team_pattern và gợi ý critic vào blueprint dict trước khi execute."""
    p = pattern or infer_team_pattern(goal)
    out = dict(blueprint or {})
    out["team_pattern"] = p.id
    if p.requires_critic:
        out["recommended_critic"] = True
        rationale = (out.get("rationale") or "").strip()
        if "CRITIC" not in rationale.upper() and "review" not in rationale.lower():
            out["rationale"] = (rationale + "\n[Harness] DEEP pipeline sẽ chạy T5 CRITIC (producer-reviewer).").strip()
    return out


def apply_pattern_to_steps(steps: List[Dict[str, Any]], pattern: TeamPattern) -> List[Dict[str, Any]]:
    """Hậu xử lý nhẹ: fan_out → đánh dấu parallel cho bước recon/search đầu (không đổi tool)."""
    if pattern.id != PATTERN_FAN_OUT_IN or not steps:
        return steps
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(steps):
        step = dict(s)
        tool = str(step.get("tool") or "").upper()
        if i < len(steps) - 1 and any(
            x in tool for x in ("SEARCH", "READ", "RECON", "LIST", "VIEW", "OMNI")
        ):
            step["parallel"] = True
        out.append(step)
    return out
