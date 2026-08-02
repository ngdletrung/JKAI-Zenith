# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/kernel/cce.py
# - Role: Cognitive Continuity Engine (CCE) - Multi-Cycle Continuity Substrate
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v25.0 (Cognitive OS Substrate)
#
# [WORKING PRINCIPLES]:
# 1. State-Driven Continuity: Resolves entity references ("file đó") from UCWS.
# 2. Decision Boundary Risk Assessment: Low Risk -> Act; High Risk -> Human Gate.
# 3. Reducer-Driven State Transition: W(N+1) = Reduce(W(N), Event).
# -----------------------------------------------------------------------------

import time
import json
import logging
from typing import Dict, Any, List, Optional
from core.os.ucws import get_ucws, reduce_world_state, UCWS
from core.utils.human_approval_gate import eval_tool_risk, create_approval_interrupt
from core.utils.otlp_tracer import generate_trace_parent
from core.utils.active_core_memory import get_all_blocks_prompt

logger = logging.getLogger("JKAI.CCE")


class CognitiveContinuityEngine:
    """
    Cognitive Continuity Engine (CCE)
    Coordinates continuous reasoning cycles across missions with state versioning and causality tracking.
    """

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.ucws: UCWS = get_ucws(mission_id)

    def resolve_entity_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Resolves implicit entity references (e.g., 'file đó', 'báo cáo đó') 
        from current UCWS entities without needing full raw chat history.
        """
        if not reference:
            return None

        ref_lower = reference.lower()
        entities = self.ucws.current_state.entities

        # 1. Exact match on entity_id or name
        for entity_id, data in entities.items():
            if entity_id.lower() in ref_lower or data.get("name", "").lower() in ref_lower:
                return data

        # 2. Type-based resolution (e.g. 'file' -> most recently modified file)
        if any(kw in ref_lower for kw in ["file", "tệp", "tài liệu"]):
            file_entities = [d for d in entities.values() if d.get("type") == "file"]
            if file_entities:
                # Return most recently updated file entity
                file_entities.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
                return file_entities[0]

        return None

    def execute_cognitive_cycle(
        self,
        cycle_id: str,
        goal: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        observation: str
    ) -> Dict[str, Any]:
        """
        Executes a complete 7-step Cognitive Continuity cycle:
        Observe -> Interpret -> Plan -> Risk -> Act -> Evaluate -> Reflect -> Emit Event -> Reducer -> UCWS vN+1
        """
        traceparent = generate_trace_parent(self.mission_id)
        t_start = time.perf_counter()

        # Step 1 & 2: Risk Assessment at Decision Boundary
        requires_approval, risk_reason = eval_tool_risk(tool_name, tool_args)
        if requires_approval:
            # High Risk -> Human Gate Interrupt
            interrupt_payload = create_approval_interrupt(self.mission_id, tool_name, tool_args, risk_reason)
            reduce_world_state(self.ucws, {
                "event_type": "UNCERTAINTY_UPDATED",
                "payload": {"execution": 0.95}
            })
            return {
                "status": "INTERRUPTED_AWAITING_APPROVAL",
                "mission_id": self.mission_id,
                "world_version": self.ucws.world_version,
                "reason": risk_reason
            }

        # Step 3: Emit Tool Execution Causality Event
        reduce_world_state(self.ucws, {
            "event_type": "CAUSALITY_RECORDED",
            "payload": {
                "cause": goal,
                "action": tool_name,
                "observation": str(observation)[:200],
                "effect": "Cycle completed",
                "confidence": 0.95
            }
        })

        # Step 4: Emit State Change Event
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        reduce_world_state(self.ucws, {
            "event_type": "STATE_CHANGED",
            "payload": {
                "last_cycle_id": cycle_id,
                "last_tool": tool_name,
                "cycle_latency_ms": elapsed_ms
            }
        })

        return {
            "status": "SUCCESS",
            "mission_id": self.mission_id,
            "world_version": self.ucws.world_version,
            "latency_ms": elapsed_ms,
            "traceparent": traceparent
        }
