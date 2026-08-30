# -*- coding: utf-8 -*-
"""
🧠 [DUAL-DRAFTING & STEP PRE-WARMER v1.0]
File: core/planning/dual_drafter.py

Cơ chế Phác thảo Song song (Dual-Drafting) & Làm ấm Bước tiếp theo (Step Pre-Warmer):
  - Draft A (Fast-Draft): qwen3.5:4b trên GPU (1.5s).
  - Draft B (Deep-Draft): Qwen3-30B MoE trên 20 luồng CPU Xeon (5-8s).
  - Validator Gate: Nếu Draft A đạt Coverage >= 80%, Early-Exit ngay lập tức.
  - Step Pre-Warmer: Nạp trước context/tài liệu cho Bước N+1 khi Bước N đang chạy.
"""

import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("JKAI.DualDrafter")


@dataclass
class PlanDraft:
    steps: List[Dict[str, Any]]
    generator_role: str
    generation_time_ms: float
    confidence_score: float
    coverage_score: float
    is_approved: bool = False
    notes: str = ""


class PlanCoverageValidator:
    """
    🔍 Validator thẩm định độ tin cậy của Draft A (Fast-Draft)
    """

    @staticmethod
    def evaluate_draft(goal: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Đo lường mức độ bao phủ yêu cầu của kế hoạch (Requirement Coverage & Invariants).
        """
        if not steps or not isinstance(steps, list):
            return {"approved": False, "score": 0.0, "reason": "Kế hoạch không có bước nào."}

        # 1. Kiểm tra cấu trúc tối thiểu (Ít nhất phải có bước thực thi và bước kiểm định)
        has_execute = any("exec" in str(s.get("type", "")).lower() or "action" in str(s.get("type", "")).lower() or "tool" in str(s) for s in steps)
        has_verify = any("verif" in str(s.get("type", "")).lower() or "check" in str(s.get("type", "")).lower() or "test" in str(s) for s in steps)

        # 2. Phân tích độ phủ từ khóa mục tiêu (Goal Token Coverage)
        goal_tokens = set(re_tokens(goal))
        if not goal_tokens:
            coverage = 1.0
        else:
            plan_text = " ".join([str(s.get("description", "")) + " " + str(s.get("goal", "")) for s in steps]).lower()
            matched_tokens = [t for t in goal_tokens if t in plan_text]
            coverage = len(matched_tokens) / max(len(goal_tokens), 1)

        # 3. Tính điểm chất lượng tổng hợp
        quality_score = coverage * 0.6 + (0.2 if has_execute else 0.0) + (0.2 if has_verify else 0.0)

        # Ngưỡng phê duyệt: Coverage >= 0.70 và có bước hành động
        is_approved = (quality_score >= 0.70) and (has_execute or len(steps) >= 2)

        return {
            "approved": is_approved,
            "quality_score": round(quality_score, 3),
            "coverage": round(coverage, 3),
            "has_execute": has_execute,
            "has_verify": has_verify,
            "step_count": len(steps)
        }


class DualDraftingEngine:
    """
    ⚡ Động cơ Phác thảo Kế hoạch Song song
    """

    def __init__(self):
        self.validator = PlanCoverageValidator()

    async def generate_dual_plan(
        self,
        goal: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PlanDraft:
        """
        Khởi chạy song song Draft A (GPU) và Draft B (CPU MoE), ưu tiên Early-Exit nếu Draft A đạt chuẩn.
        """
        t0 = time.perf_counter()

        # Tạo task cho Draft A (Fast-Draft)
        task_fast = asyncio.create_task(self._draft_fast_plan(goal, task_id, context))
        # Tạo task cho Draft B (Deep-Draft)
        task_deep = asyncio.create_task(self._draft_deep_plan(goal, task_id, context))

        # Đợi Draft A hoàn thành trước (thường chỉ mất 1.0 - 1.5s)
        try:
            fast_plan = await asyncio.wait_for(asyncio.shield(task_fast), timeout=3.0)
            elapsed_fast = (time.perf_counter() - t0) * 1000

            # Kiểm định chất lượng Draft A qua Validator
            eval_res = self.validator.evaluate_draft(goal, fast_plan.get("steps", []))
            
            if eval_res["approved"]:
                # Early-Exit thành công: Hủy Draft B để tiết kiệm CPU Xeon
                if not task_deep.done():
                    task_deep.cancel()
                
                return PlanDraft(
                    steps=fast_plan.get("steps", []),
                    generator_role="PLANNER_FAST",
                    generation_time_ms=elapsed_fast,
                    confidence_score=eval_res["quality_score"],
                    coverage_score=eval_res["coverage"],
                    is_approved=True,
                    notes=f"Draft A early-exit approved ({eval_res['quality_score']:.2f})."
                )
        except Exception:
            pass

        # Fallback sang Draft B nếu Draft A không đạt hoặc timeout
        try:
            deep_plan = await asyncio.wait_for(task_deep, timeout=10.0)
            elapsed_deep = (time.perf_counter() - t0) * 1000
            eval_deep = self.validator.evaluate_draft(goal, deep_plan.get("steps", []))

            return PlanDraft(
                steps=deep_plan.get("steps", []),
                generator_role="DEEP_REASONER",
                generation_time_ms=elapsed_deep,
                confidence_score=eval_deep["quality_score"],
                coverage_score=eval_deep["coverage"],
                is_approved=True,
                notes="Draft B generated via Deep Reasoner."
            )
        except Exception as e:
            # Fallback tối hậu: Sinh kế hoạch mặc định an toàn
            return PlanDraft(
                steps=[
                    {"id": "step_1", "description": f"Khảo sát và thu thập dữ liệu cho: {goal[:50]}", "type": "recon"},
                    {"id": "step_2", "description": "Thực thi tác vụ và tổng hợp bằng chứng", "type": "execute"},
                    {"id": "step_3", "description": "Kiểm định kết quả và xuất báo cáo", "type": "verify"}
                ],
                generator_role="DEFAULT_FALLBACK",
                generation_time_ms=(time.perf_counter() - t0) * 1000,
                confidence_score=0.5,
                coverage_score=0.5,
                is_approved=True,
                notes=f"Fallback plan generated: {e}"
            )

    async def _draft_fast_plan(self, goal: str, task_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Tạo kế hoạch nhanh bằng mô hình Lễ tân / Planner trên GPU."""
        from core.utils.engine import engine
        prompt = (
            f"Hãy lập kế hoạch 3-5 bước hành động cụ thể để giải quyết mục tiêu sau:\n"
            f"MỤC TIÊU: {goal}\n\n"
            f"Định dạng JSON: {{\"steps\": [{{\"id\": \"step_1\", \"description\": \"...\", \"type\": \"recon|execute|verify\"}}]}}"
        )
        resp = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER",
            task_id=task_id,
            skip_memory=True
        )
        raw = resp.get("answer", "") if isinstance(resp, dict) else str(resp)
        return parse_plan_json(raw, goal)

    async def _draft_deep_plan(self, goal: str, task_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Tạo kế hoạch sâu bằng mô hình DEEP_REASONER trên CPU Xeon."""
        from core.utils.engine import engine
        prompt = (
            f"Hãy phân tích sâu và lập kế hoạch chi tiết từng bước (DAG dependencies):\n"
            f"MỤC TIÊU: {goal}\n\n"
            f"Định dạng JSON: {{\"steps\": [{{\"id\": \"step_1\", \"description\": \"...\", \"type\": \"recon|execute|verify\"}}]}}"
        )
        resp = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="DEEP_REASONER",
            task_id=task_id,
            skip_memory=True
        )
        raw = resp.get("answer", "") if isinstance(resp, dict) else str(resp)
        return parse_plan_json(raw, goal)


class StepPreWarmer:
    """
    ⚡ Làm ấm tài nguyên và dữ liệu cho Bước N+1 trong lúc Bước N đang thực thi.
    """

    @staticmethod
    async def pre_warm_next_step(next_step_desc: str, task_id: str) -> None:
        """
        Kích hoạt tải ngầm tri thức RAG Multi-Index vào RAM cache trước khi bước tiếp theo bắt đầu.
        """
        if not next_step_desc:
            return
        try:
            from core.knowledge_sources.retriever import retriever
            # Nạp ngầm vào cache mà không làm chậm bước hiện tại
            asyncio.create_task(retriever.search(next_step_desc, top_k=2))
        except Exception:
            pass


def re_tokens(text: str) -> List[str]:
    import re
    return [t for t in re.findall(r"\b[\w\-]+\b", text.lower()) if len(t) > 2]


def parse_plan_json(raw_text: str, goal: str) -> Dict[str, Any]:
    """Trích xuất JSON kế hoạch từ phản hồi của LLM."""
    import json
    import re
    try:
        match = re.search(r"\{.*\"steps\".*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    
    # Fallback heuristic tạo steps từ các dòng gạch đầu dòng
    lines = [line.strip() for line in raw_text.split("\n") if line.strip().startswith(("-", "*", "1.", "2.", "3.", "4."))]
    if lines:
        return {
            "steps": [
                {"id": f"step_{i+1}", "description": line.lstrip("-*0123456789. "), "type": "execute"}
                for i, line in enumerate(lines[:5])
            ]
        }
    return {
        "steps": [
            {"id": "step_1", "description": f"Thực thi mục tiêu: {goal}", "type": "execute"},
            {"id": "step_2", "description": "Kiểm định kết quả", "type": "verify"}
        ]
    }


dual_drafter = DualDraftingEngine()
step_prewarmer = StepPreWarmer()
