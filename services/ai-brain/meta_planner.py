import json
import logging
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from core.utils.engine import engine

logger = logging.getLogger("JKAI.MetaPlanner")

class RoutingDecision(BaseModel):
    domain: str = Field(..., description="The matched domain (e.g., CODING, RESEARCH, CORE, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the routing decision")
    complexity: str = Field(..., description="Estimated complexity: SIMPLE, MEDIUM, COMPLEX, or EXTREME")
    execution_mode: str = Field(..., description="Execution mode: SEQUENTIAL, PARALLEL, or HYBRID")
    rationale: str = Field(..., description="Brief rationale for choosing this domain")
    agent_role: str = Field(..., description="The role of the domain agent to invoke (e.g., Software Architect, Research Specialist)")

class MetaPlanner:
    """
    🧠 META-PLANNER KERNEL (Level 3 AI OS)
    This is the lightweight router that understands the user goal
    and selects the appropriate domain agent.
    """
    def __init__(self):
        self.domain_registry_path = os.path.join(os.getcwd(), "intelligence", "domain_registry.json")
        self._load_registry()

    def _load_registry(self):
        try:
            with open(self.domain_registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.domains = data.get("domains", {})
        except Exception as e:
            logger.error(f"Failed to load domain registry: {e}")
            self.domains = {}

    async def route_task(self, goal: str, context: Optional[Dict] = None, task_id: str = "system") -> Dict[str, Any]:
        """Routes a high-level goal to a specific domain."""
        
        domain_list = []
        for key, info in self.domains.items():
            domain_list.append(f"- {key}: {info['name']} | {info['description']}")
        
        domains_str = "\n".join(domain_list)
        
        system_prompt = f"""
You are the JKAI Zenith Meta-Planner (Kernel).
Your ONLY job is to route the user's task to the correct Domain Agent.
Do NOT write code. Do NOT generate a full plan. 
Just analyze the goal and select the most appropriate domain.

<AVAILABLE_DOMAINS>
{domains_str}
</AVAILABLE_DOMAINS>

Output valid JSON matching the RoutingDecision schema.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {goal}"}
        ]

        logger.info(f"🧭 [META-PLANNER]: Routing task: '{goal[:50]}...'")
        
        # Use MINI_PLANNER role as this is a fast, structured classification task
        try:
            raw_decision = await engine.call_chat(
                messages=messages,
                role="MINI_PLANNER",
                schema=RoutingDecision.model_json_schema(),
                task_id=task_id
            )
            
            if isinstance(raw_decision, str):
                raw_decision = json.loads(raw_decision)
                
            decision = RoutingDecision.model_validate(raw_decision)
            
            # Fallback for unknown domains
            if decision.domain not in self.domains:
                logger.warning(f"[META-PLANNER]: Hallucinated domain '{decision.domain}'. Falling back to CORE.")
                decision.domain = "CORE"
                
            return decision.model_dump()
            
        except Exception as e:
            logger.error(f"[META-PLANNER] Routing failed: {e}")
            return {
                "domain": "CORE", 
                "confidence": 0.5, 
                "complexity": "MEDIUM",
                "execution_mode": "SEQUENTIAL",
                "rationale": f"Fallback due to error: {e}", 
                "agent_role": "Generalist"
            }
