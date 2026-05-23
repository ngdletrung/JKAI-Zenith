import time
import uuid
import asyncio
import json
from ingress_gateway.shadow_diff import DecisionDiffEngine

# 🛑 BẢNG ĐIỀU KHIỂN CHIẾN LƯỢC (Strategic Control Panel)
SYSTEM_FLAGS = {
    "GLOBAL_RUNTIME_KILL_SWITCH": False, # Kéo còi báo động để ngắt toàn bộ hệ thống mới
    "SHADOW_MODE_ENABLED": True,         # Bật/Tắt chế độ chạy song song (Observe-only)
    "FEATURE_FLAGS": {
        "new_dispatcher_traffic": 0.10,  # 10% traffic vào Dispatcher mới
        "runtime_fabric": 0.00           # 0% traffic chạy thực sự trên Runtime mới
    }
}

class IngressGateway:
    """
    🚪 Lễ Tân Phi Trạng Thái (Stateless Ingress)
    Xác Thực -> Cắm Cờ Trace -> Gọi Legacy -> Bắn Shadow Pipeline (Async) -> Trả Kết Quả Legacy.
    """
    def __init__(self, receptionist_legacy, semantic_firewall, dispatcher_new):
        self.legacy = receptionist_legacy
        self.firewall = semantic_firewall
        self.dispatcher_new = dispatcher_new
        self.diff_engine = DecisionDiffEngine()

    async def receive_request(self, goal: str, task_id: str, history: list = None, images: list = None, mode: str = "fast"):
        """Đầu vào duy nhất của hệ thống."""
        # 1. 🛑 KIỂM TRA KILL SWITCH
        if SYSTEM_FLAGS["GLOBAL_RUNTIME_KILL_SWITCH"]:
            print("🛑 [KILL-SWITCH ACTIVATED]: Hệ thống mới đang bị ngắt hoàn toàn. Trả về Legacy 100%.")
            return await self.legacy.handle_task(goal, task_id, history=history, images=images, mode=mode)

        # 2. 🛡️ TƯỜNG LỬA NGỮ NGHĨA (Ngay tại cổng)
        fw_res = self.firewall.scan_input(goal)
        if not fw_res["safe"]:
            return {"status": "error", "answer": f"🛡️ [FIREWALL BLOCKED]: {fw_res['reason']}", "task_id": task_id}

        # 3. 🏷️ DÁN NHÃN TRUY VẾT (Trace ID)
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        print(f"🏷️ [INGRESS]: Bắt đầu truy vết Trace_ID: {trace_id}")

        # 4. CHẠY PIPELINE CŨ (Trụ cột hiện tại)
        # Hệ thống thực tế vẫn nhận kết quả từ Legacy để đảm bảo an toàn 100%
        legacy_result = await self.legacy.handle_task(goal, task_id, history=history, images=images, mode=mode)

        # 5. KÍCH HOẠT SHADOW PIPELINE (Chạy ngầm - Observe Only)
        if SYSTEM_FLAGS["SHADOW_MODE_ENABLED"]:
            # Chỉ bắt 10% traffic vào mẻ lưới Shadow
            import random
            if random.random() <= SYSTEM_FLAGS["FEATURE_FLAGS"]["new_dispatcher_traffic"]:
                asyncio.create_task(self._run_shadow_pipeline(goal, trace_id, legacy_result))

        return legacy_result

    async def _run_shadow_pipeline(self, goal: str, trace_id: str, legacy_result: dict):
        """
        🕵️ SHADOW MODE (Observe Only - No Mutation)
        Chạy Dispatcher mới và so sánh với kết quả Legacy.
        """
        try:
            print(f"🕵️ [SHADOW_MODE]: Đang quét Trace {trace_id} bằng Dispatcher Mới...")
            
            # Legacy Intent Extract (Rất giả lập vì Legacy không có Manifest chuẩn)
            # Chúng ta sẽ map tạm "requires_planner" hoặc "skill"
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

            # Chạy Dispatcher Mới để sinh Canonical Intent Representation (CIR)
            new_manifest = await self.dispatcher_new.dispatch(goal, trace_id)
            
            # Chuyển đổi sang chuẩn so khớp
            shadow_manifest_mock = {
                "intent": new_manifest.intent,
                "risk": new_manifest.risk.name,
                "capabilities": [p.name for p in new_manifest.capabilities_required],
                "tools": [new_manifest.skill] if new_manifest.skill else []
            }

            # 6. MÁY SO KHỚP QUYẾT ĐỊNH (Decision Diff Engine)
            diff_score = self.diff_engine.calculate_divergence(legacy_manifest_mock, shadow_manifest_mock)
            
            print(f"📊 [SHADOW-DIFF]: Trace {trace_id} - Score: {diff_score:.2f}")
            if diff_score > 0.5:
                print(f"⚠️ [DIVERGENCE WARNING]: Quyết định giữa Legacy và New Runtime lệch xa nhau!")
                print(f"   + Legacy: {legacy_manifest_mock}")
                print(f"   + Shadow: {shadow_manifest_mock}")
                
            # Todo: Gắn kết quả này vào Audit Logger để Data Analyst đánh giá
            
        except Exception as e:
            print(f"❌ [SHADOW-PIPELINE ERROR]: Trace {trace_id} crash: {e}")
            # Crash trong Shadow Mode KHÔNG ẢNH HƯỞNG đến User!
