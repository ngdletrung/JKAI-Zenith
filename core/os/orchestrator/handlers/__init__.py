"""
JKAI AI OS — Orchestrator Handlers Registry
Khởi tạo và xuất xưởng danh sách tuần tự các handlers trong Ingress Pipeline.
"""

from typing import List

from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.handlers.math_reflex import MathReflexHandler
from core.os.orchestrator.handlers.slash_command import SlashCommandHandler
from core.os.orchestrator.handlers.reflex_memory import ReflexMemoryHandler
from core.os.orchestrator.handlers.fast_bypass import FastBypassHandler
from core.os.orchestrator.handlers.parallel_enrichment import ParallelEnrichmentHandler
from core.os.orchestrator.handlers.workspace_scope import WorkspaceScopeHandler
from core.os.orchestrator.handlers.intent_governor import IntentGovernorHandler
from core.os.orchestrator.handlers.execution_planner import ExecutionPlannerHandler
from core.os.orchestrator.handlers.cloud_discuss import CloudDiscussHandler

__all__ = [
    "BaseHandler",
    "MathReflexHandler",
    "SlashCommandHandler",
    "CloudDiscussHandler",
    "ReflexMemoryHandler",
    "FastBypassHandler",
    "ParallelEnrichmentHandler",
    "WorkspaceScopeHandler",
    "IntentGovernorHandler",
    "ExecutionPlannerHandler",
    "get_default_pipeline_handlers"
]


def get_default_pipeline_handlers() -> List[BaseHandler]:
    """Trả về danh sách các Handler theo thứ tự tối ưu hiệu năng."""
    return [
        MathReflexHandler("MathReflex"),              # 1. Toán học AST siêu tốc (<1ms)
        SlashCommandHandler("SlashCommand"),          # 2. Lệnh tắt (/research, /code, /status)
        CloudDiscussHandler("CloudDiscuss"),          # 3. Hội đồng Thảo luận Đa AI (JKAI Discuss Protocol v1.0)
        ReflexMemoryHandler("ReflexMemory"),          # 4. Tra cứu bộ nhớ phản xạ nơ-ron
        FastBypassHandler("FastBypass"),              # 5. Fast-path bypass cho câu đàm thoại xã giao
        ParallelEnrichmentHandler("ParallelEnrich"),  # 6. Speculative Fork-Join (SkillDeck, RepoClone, MissionCtx)
        WorkspaceScopeHandler("WorkspaceScope"),      # 7. Phạm vi Workspace & Cursor Agent
        IntentGovernorHandler("IntentGovernor"),      # 8. CentralIntentRouter v4.0 + Single-pass Governor
        ExecutionPlannerHandler("ExecutionPlanner"),  # 9. WorldState, MemoryState & Step Generation
    ]
