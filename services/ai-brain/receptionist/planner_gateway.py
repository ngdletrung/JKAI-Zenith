from core.utils.engine import engine

class PlannerGateway:
    """
    📐 TẬP ĐOÀN JKAI ZENITH - PLANNER GATEWAY (STATELESS)
    Giao tiếp với ai-control-plane chuyên trách lập Blueprint.
    """
    def __init__(self, http_client):
        self.http_client = http_client

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

    async def request_plan(self, goal: str, images: list, history: list, task_id: str, cap_token: dict) -> dict:
        """Yêu cầu Planner lập kế hoạch với Capability Token."""
        self._log("ZENITH", "🧠 [ROUTING]: Kích hoạt Planner với Capability Token...", task_id)
        try:
            resp = await self.http_client.post(f"http://ai-control-plane:8000/plan", json={
                "goal": goal,
                "context": {"images": images},
                "history": history,
                "task_id": task_id,
                "token": cap_token
            })
            plan_res = resp.json()
            
            if plan_res.get("steps") and not any(s.get("id") == "error" for s in plan_res["steps"]):
                return {"status": "success", "msg": "📐 [BLUEPRINT]: Ban Chiến lược đã lập xong lộ trình thực thi thưa Master. Mời Ngài kiểm tra trong tab Kế hoạch."}
            elif plan_res.get("error"):
                return {"status": "error", "msg": f"❌ [PLANNER ERROR]: {plan_res.get('error')}"}
            elif plan_res.get("ambiguous"):
                return {"status": "clarify", "msg": f"❓ [CLARIFY]: {plan_res.get('question')}"}
            else:
                return {"status": "error", "msg": "⚠️ [PLANNER WARNING]: Lỗi Planner không xác định."}
        except Exception as e:
            self._log("SYSTEM", f"⚠️ [ROUTING-ERR]: Lỗi kết nối Ban Chiến lược: {e}", task_id)
            return {"status": "error", "msg": f"Lỗi kết nối Ban Chiến lược: {e}"}
