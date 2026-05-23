import time
import logging
from typing import Union
from core.utils.routing_manifest import RoutingManifest, CapabilityToken, ActionType

logger = logging.getLogger(__name__)

class PolicyEngine:
    @staticmethod
    def evaluate(manifest: RoutingManifest, context: dict = None) -> Union[CapabilityToken, dict]:
        """
        Zero-Trust Evaluation: Trả về CapabilityToken nếu hợp lệ, ngược lại trả về thông báo lỗi.
        """
        context = context or {}
        source = context.get("source", "unknown")
        
        # 1. Đánh giá ActionType & Source
        if manifest.action_type in (ActionType.SYSTEM_DESTRUCTIVE, ActionType.DATA_DESTRUCTIVE, ActionType.NETWORK_DESTRUCTIVE):
            if source == "telegram" or source == "web_guest":
                logger.warning(f"🛡️ [POLICY] Denied DESTRUCTIVE action from untrusted source: {source}")
                return {"action": "DENY", "reason": "Insufficient channel trust for DESTRUCTIVE actions."}
        
        # 2. Đánh giá Risk
        if manifest.risk == "CRITICAL":
            logger.warning("🛡️ [POLICY] CRITICAL risk detected. Requiring HITL (Human-in-the-loop).")
            # In a real system, we might pause for HITL, here we deny if no sovereign key
            if not context.get("has_sovereign_key"):
                return {"action": "DENY", "reason": "CRITICAL actions require Sovereign Key / HITL."}

        # 3. Chốt Sandbox Profile
        sandbox_profile = "default"
        if manifest.domain == "NETWORK":
            sandbox_profile = "network_readonly" if manifest.action_type == ActionType.QUERY else "network_restricted"
        elif manifest.domain == "SYSTEM":
            sandbox_profile = "isolated_fs"

        # 4. Cấp phép (Grant)
        permissions = [f"tool:{manifest.skill}"] if manifest.skill else []
        if manifest.requires_planner:
            permissions.append("system:planner")
        if manifest.requires_memory:
            permissions.append("system:memory")

        token = CapabilityToken.create(
            trace_id=manifest.trace_id,
            permissions=permissions,
            sandbox_profile=sandbox_profile,
            lifespan=300.0  # 5 phút
        )
        
        logger.info(f"🔑 [POLICY] Granted CapabilityToken(sandbox={sandbox_profile}, permissions={permissions})")
        return token
