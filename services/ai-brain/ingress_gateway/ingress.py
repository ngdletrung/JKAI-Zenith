# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/ingress_gateway/ingress.py
# - Role: Stateless Ingress Gateway
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Xac thuc va truy vet trace_id cho moi yeu cau dau vao.
# - Dinh tuyen va dieu phoi shadow pipeline song song (Observe-only).
# - Ghi nhan ket qua dore lech dong bo truc tiep vao central AuditLogger (Immutable Hash-Chain).

import os
import time
import uuid
import asyncio
import json
from ingress_gateway.shadow_diff import DecisionDiffEngine


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


# strategic control panel
SYSTEM_FLAGS = {
    "GLOBAL_RUNTIME_KILL_SWITCH": False, # Keo coi bao dong de ngat toan bo he thong moi
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
            print(f"[INGRESS-WARN]: Cannot initialize central AuditLogger: {e}")
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
            print("[INGRESS-KILL-SWITCH]: He thong moi dang bi ngat hoan toan. Tra ve Legacy 100%.")
            return await self.legacy.handle_task(
                goal,
                task_id,
                history=history,
                images=images,
                mode=mode,
                mission_id=mission_id,
                parent_mission_id=parent_mission_id,
                trace_id=trace_id,
            )

        # 2. TUONG LUA NGU NGHIA
        fw_res = self.firewall.scan_input(goal)
        if not fw_res["safe"]:
            return {"status": "error", "answer": f"[FIREWALL BLOCKED]: {fw_res['reason']}", "task_id": task_id}

        # 3. DAN NHAN TRUY VET
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        print(f"[INGRESS]: Bat dau truy vet Trace_ID: {trace_id}")

        # 4. CHAY PIPELINE CU (Legacy) — nâng fast → deep khi Master báo lỗi
        effective_mode = mode
        try:
            from core.utils.deep_routing import effective_ingress_mode

            effective_mode = effective_ingress_mode(goal, mode, history)
            if effective_mode == "deep" and mode != "deep":
                print(f"[INGRESS]: Auto DEEP for error/debug goal (was mode={mode})")
        except Exception as route_err:
            print(f"[INGRESS-WARN] deep routing: {route_err}")

        legacy_result = await self.legacy.handle_task(
            goal,
            task_id,
            history=history,
            images=images,
            mode=effective_mode,
            trace_id=trace_id,
            mission_id=mission_id,
            parent_mission_id=parent_mission_id,
        )
        if effective_mode == "deep":
            legacy_result = dict(legacy_result or {})
            legacy_result["mode"] = "deep"

        # 5. KICH HOAT SHADOW PIPELINE (Chay ngam - Observe Only)
        if SYSTEM_FLAGS["SHADOW_MODE_ENABLED"] and not self._skip_shadow_for_goal(goal):
            import random
            if random.random() <= SYSTEM_FLAGS["FEATURE_FLAGS"]["new_dispatcher_traffic"]:
                asyncio.create_task(self._run_shadow_pipeline(goal, trace_id, legacy_result))

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

    async def _run_shadow_pipeline(self, goal: str, trace_id: str, legacy_result: dict):
        """
        SHADOW MODE (Observe Only - No Mutation)
        Chay Dispatcher moi va so sanh voi ket qua Legacy.
        """
        try:
            print(f"[SHADOW-PIPELINE]: Dang quet Trace {trace_id} bang Dispatcher Moi...")
            
            # Legacy Intent Extract (Gia lap vi Legacy khong co Manifest chuan)
            legacy_intent = "UNKNOWN"
            if "FAST_PIPELINE" in str(legacy_result):
                legacy_intent = "EXECUTE_FAST"
            elif "CLARIFY" in str(legacy_result):
                legacy_intent = "CLARIFY"
            else:
                legacy_intent = "PLAN_OR_CHAT"
                
            legacy_manifest_mock = {
                "intent": legacy_intent,
                "risk": "UNKNOWN",
                "capabilities": [],
                "tools": []
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

            # 6. MAY SO KHOP QUYET DINH
            diff_score = self.diff_engine.calculate_divergence(legacy_manifest_mock, shadow_manifest_mock)
            
            print(f"[SHADOW-DIFF]: Trace {trace_id} - Score: {diff_score:.2f}")
            if diff_score > 0.5:
                print(f"[DIVERGENCE-WARNING]: Quyet dinh giua Legacy va New Runtime lech xa nhau!")
                print(f"   + Legacy: {legacy_manifest_mock}")
                print(f"   + Shadow: {shadow_manifest_mock}")
                
            # Ghi ket qua so khop vao central Audit Logger (Immutable Hash-Chain)
            if self.audit_logger:
                try:
                    self.audit_logger.append(
                        action="SHADOW_DIFF_EVALUATION",
                        subject=trace_id,
                        details={
                            "goal": goal,
                            "diff_score": round(diff_score, 4),
                            "legacy_manifest": legacy_manifest_mock,
                            "shadow_manifest": shadow_manifest_mock,
                            "timestamp": time.time()
                        }
                    )
                    print(f"[INGRESS-AUDIT]: Trace {trace_id} evaluation successfully committed to immutable audit chain.")
                except Exception as audit_err:
                    print(f"[INGRESS-AUDIT-ERR]: Failed to record shadow diff evaluation: {audit_err}")
                
        except Exception as e:
            print(f"[SHADOW-PIPELINE-ERROR]: Trace {trace_id} crash: {e}")
