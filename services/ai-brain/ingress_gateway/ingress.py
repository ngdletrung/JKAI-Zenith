# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/ingress_gateway/ingress.py
# - Role: Stateless Ingress Gateway
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v19.0 (Structured Logging + Intent Fix)
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem No-Emoji va Zero-Noise.
# - Xac thuc va truy vet trace_id cho moi yeu cau dau vao.
# - Dinh tuyen va dieu phoi shadow pipeline song song (Observe-only).
# - Ghi nhan ket qua do lech dong bo truc tiep vao central AuditLogger (Immutable Hash-Chain).

import os
import time
import uuid
import asyncio
import json
import logging
from ingress_gateway.shadow_diff import DecisionDiffEngine

logger = logging.getLogger("jkai.ingress")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


# strategic control panel
SYSTEM_FLAGS = {
    "GLOBAL_RUNTIME_KILL_SWITCH": False,
    "SHADOW_MODE_ENABLED": _env_bool("JKAI_SHADOW_MODE_ENABLED", default=False),
    "FEATURE_FLAGS": {
        "new_dispatcher_traffic": 1.00,  # 100% traffic vao Dispatcher moi de test log
        "runtime_fabric": 0.00           # 0% traffic chay thuc su tren Runtime moi
    }
}

class IngressGateway:
    """
    Le Tan Phi Trang Thai (Stateless Ingress)
    Xac Thuc -> Cam Co Trace -> Goi Legacy -> Ban Shadow Pipeline (Async) -> Tra Ket Qua Legacy.
    """
    def __init__(self, receptionist_legacy, semantic_firewall, dispatcher_new):
        self.legacy = receptionist_legacy
        self.firewall = semantic_firewall
        self.dispatcher_new = dispatcher_new
        self.diff_engine = DecisionDiffEngine()

        # Khoi tao AuditLogger thong qua Redis connection thuc te
        try:
            from redis_client import get_redis
            from telemetry.audit_logger import AuditLogger
            self.audit_logger = AuditLogger(get_redis())
        except Exception as e:
            logger.warning("[INGRESS]: Cannot initialize central AuditLogger: %s", e)
            self.audit_logger = None

    async def receive_request(
        self,
        goal: str,
        task_id: str,
        history: list = None,
        images: list = None,
        mode: str = "fast",
        mission_id: str = None,
        parent_mission_id: str = None,
        trace_id: str = None,
    ):
        """Dau vao duy nhat cua he thong."""
        # 1. KIEM TRA KILL SWITCH
        if SYSTEM_FLAGS["GLOBAL_RUNTIME_KILL_SWITCH"]:
            logger.critical("[INGRESS-KILL-SWITCH]: He thong moi dang bi ngat hoan toan. Tra ve Legacy 100%.")
            return await self.legacy.handle_task(
                goal, task_id,
                history=history, images=images, mode=mode,
                mission_id=mission_id, parent_mission_id=parent_mission_id, trace_id=trace_id,
            )

        # 2. TUONG LUA NGU NGHIA (skip SSM-enriched goals — system content, not user input)
        fw_res = {"safe": True}
        if "<ZENITH_SKILL_ACTIVATED>" in goal:
            logger.debug("[INGRESS-FIREWALL]: SSM-enriched goal, skipping firewall.")
        else:
            fw_res = self.firewall.scan_input(goal)
        if not fw_res["safe"]:
            logger.warning(
                "[INGRESS-BLOCKED]: task_id=%s | category=%s | reason=%s",
                task_id, fw_res.get("category"), fw_res.get("reason")
            )
            return {"status": "error", "answer": f"[FIREWALL BLOCKED]: {fw_res['reason']}", "task_id": task_id}

        # 3. DAN NHAN TRUY VET
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        logger.info("[INGRESS]: task_id=%s | trace_id=%s | mode=%s | goal_len=%d",
                    task_id, trace_id, mode, len(goal))

        # 4. CHAY PIPELINE CU (Legacy) — nang fast -> deep khi Master bao loi
        effective_mode = mode
        try:
            from core.utils.deep_routing import effective_ingress_mode
            effective_mode = effective_ingress_mode(goal, mode, history)
            if effective_mode == "deep" and mode != "deep":
                logger.info("[INGRESS]: Auto-upgrade to DEEP mode for error/debug goal. task_id=%s", task_id)
        except Exception as route_err:
            logger.warning("[INGRESS-WARN]: deep routing error: %s | task_id=%s", route_err, task_id)

        legacy_result = await self.legacy.handle_task(
            goal, task_id,
            history=history, images=images, mode=effective_mode,
            trace_id=trace_id, mission_id=mission_id, parent_mission_id=parent_mission_id,
        )
        if effective_mode == "deep":
            legacy_result = dict(legacy_result or {})
            legacy_result["mode"] = "deep"

        # 5. KICH HOAT SHADOW PIPELINE (Chay ngam - Observe Only)
        if SYSTEM_FLAGS["SHADOW_MODE_ENABLED"] and not self._skip_shadow_for_goal(goal):
            import random
            if random.random() <= SYSTEM_FLAGS["FEATURE_FLAGS"]["new_dispatcher_traffic"]:
                asyncio.create_task(self._run_shadow_pipeline(goal, trace_id, legacy_result, task_id))

        return legacy_result

    @staticmethod
    def _skip_shadow_for_goal(goal: str) -> bool:
        """Inspect / deck-only queries already answered by receptionist — skip noisy shadow LLM."""
        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            deck = SkillDeckIndex.get()
            if not deck.parse_refs(goal):
                return False
            return deck.is_inspect_intent(goal)
        except Exception:
            return False

    async def _run_shadow_pipeline(self, goal: str, trace_id: str, legacy_result: dict, task_id: str = None):
        """
        SHADOW MODE (Observe Only - No Mutation)
        Chay Dispatcher moi va so sanh voi ket qua Legacy.
        """
        try:
            logger.debug("[SHADOW-PIPELINE]: Dang quet Trace %s bang Dispatcher Moi...", trace_id)

            # [FIX]: Dung ket qua thuc te tu legacy_result thay vi string matching thu
            # Uu tien doc tu cac field co cau truc: mode, pipeline, intent
            legacy_intent = (
                legacy_result.get("intent")
                or legacy_result.get("pipeline")
                or legacy_result.get("mode", "").upper()
                or "UNKNOWN"
            )
            # Chuan hoa gia tri
            _intent_map = {
                "fast": "EXECUTE_FAST",
                "FAST": "EXECUTE_FAST",
                "deep": "PLAN_OR_CHAT",
                "DEEP": "PLAN_OR_CHAT",
                "clarify": "CLARIFY",
                "CLARIFY": "CLARIFY",
            }
            legacy_intent = _intent_map.get(legacy_intent, legacy_intent or "PLAN_OR_CHAT")

            legacy_manifest_mock = {
                "intent": legacy_intent,
                "risk": legacy_result.get("risk", "UNKNOWN"),
                "capabilities": legacy_result.get("capabilities", []),
                "tools": legacy_result.get("tools_used", [])
            }

            # Chay Dispatcher Moi de sinh Canonical Intent Representation (CIR)
            new_manifest = await self.dispatcher_new.dispatch(goal, trace_id)

            # Chuyen doi sang chuan so khop
            shadow_capabilities = []
            if getattr(new_manifest, "requires_planner", False):
                shadow_capabilities.append("PLANNER")
            if getattr(new_manifest, "requires_memory", False):
                shadow_capabilities.append("MEMORY")
            if getattr(new_manifest, "requires_llm", False):
                shadow_capabilities.append("LLM")

            for cap in getattr(new_manifest, 'capabilities_required', getattr(new_manifest, 'constraints', [])):
                cap_name = cap.name if hasattr(cap, 'name') else str(cap)
                if cap_name not in shadow_capabilities:
                    shadow_capabilities.append(cap_name)

            shadow_manifest_mock = {
                "intent": new_manifest.intent,
                "risk": new_manifest.risk.name if hasattr(new_manifest.risk, 'name') else str(new_manifest.risk),
                "capabilities": shadow_capabilities,
                "tools": [new_manifest.skill] if new_manifest.skill else []
            }

            # MAY SO KHOP QUYET DINH
            diff_score = self.diff_engine.calculate_divergence(legacy_manifest_mock, shadow_manifest_mock)
            logger.info("[SHADOW-DIFF]: trace=%s | score=%.2f", trace_id, diff_score)

            if diff_score > 0.5:
                logger.warning(
                    "[DIVERGENCE-WARNING]: trace=%s | score=%.2f | legacy=%s | shadow=%s",
                    trace_id, diff_score, legacy_manifest_mock, shadow_manifest_mock
                )

            # Ghi ket qua so khop vao central Audit Logger (Immutable Hash-Chain)
            if self.audit_logger:
                try:
                    self.audit_logger.append(
                        action="SHADOW_DIFF_EVALUATION",
                        subject=trace_id,
                        details={
                            "goal": goal,
                            "task_id": task_id,
                            "diff_score": round(diff_score, 4),
                            "legacy_manifest": legacy_manifest_mock,
                            "shadow_manifest": shadow_manifest_mock,
                            "timestamp": time.time()
                        }
                    )
                    logger.debug("[INGRESS-AUDIT]: Trace %s committed to immutable audit chain.", trace_id)
                except Exception as audit_err:
                    logger.error("[INGRESS-AUDIT-ERR]: Failed to record shadow diff: %s", audit_err)

        except Exception as e:
            logger.error("[SHADOW-PIPELINE-ERROR]: trace=%s | error=%s", trace_id, e)
