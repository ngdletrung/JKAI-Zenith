# 🧬 JKAI Zenith: COGNITIVE AUTONOMOUS LOOP (The "Skeleton")
# Inspired by OpenHands & ReAct Architecture | Sovereign Implementation

import asyncio
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from core.utils.engine import engine
from core.kernel.cognitive_event_bus import cognitive_event_bus, ObservationEvent, CognitiveEvent
from core.kernel.compaction import compaction_engine

logger = logging.getLogger("CognitiveLoop")

class CognitiveLoop:
    """
    🏗️ COGNITIVE LOOP (Khung xương Trí tuệ)
    Điều phối chu trình: SUY NGHĨ -> HÀNH ĐỘNG -> QUAN SÁT -> PHẢN BIỆN.
    Giúp các model nhỏ (0.6B) hoạt động thông minh bằng cách chia nhỏ vấn đề.
    """

    def __init__(self, task_id: str, goal: str):
        self.task_id = task_id
        self.goal = goal
        self.history: List[Dict[str, Any]] = []
        self.max_steps = 10
        self.step_count = 0
        self.is_finished = False

    def _log(self, tag: str, msg: str, stealth: bool = False):
        engine.publish_mission_log(tag, f"[LOOP]: {msg}", self.task_id, stealth=stealth)

    async def run(self):
        """Kích hoạt chu trình tự trị nhận thức 7 bước thưa Master."""
        self._log("ZENITH", f"🚀 Khởi động Chu trình Tự trị cho mục tiêu: {self.goal}")

        # Nạp World State & Active Core Memory
        from core.os.world_state import get_mission_world_state, update_mission_world_state, record_causality_link
        from core.utils.active_core_memory import get_all_blocks_prompt
        from core.utils.otlp_tracer import generate_trace_parent
        from core.utils.human_approval_gate import eval_tool_risk, create_approval_interrupt

        world_st = update_mission_world_state(self.task_id, "state_data", {"goal": self.goal, "step_count": 0})
        core_mem_p = get_all_blocks_prompt()

        # 1. Khởi tạo ngữ cảnh hệ thống
        system_prompt = (
            "# 🌌 JKAI ZENITH: GIAO THỨC CHỦ QUYỀN TỐI THƯỢNG\n"
            "Bạn đang hoạt động trong một CHU TRÌNH TỰ TRỊ (Autonomous Cognitive Loop).\n"
            "Mục tiêu tối thượng: " + self.goal + "\n\n"
            "## 🏛️ QUY TẮC THỰC THI:\n"
            "1. **Một hành động mỗi lần**: Chỉ thực hiện DUY NHẤT một hành động (gọi công cụ) trong mỗi bước.\n"
            "2. **Quan sát & Phản xạ**: Sau mỗi hành động, bạn sẽ nhận được kết quả (Observation). Hãy dùng nó để quyết định bước tiếp theo.\n"
            "3. **Tự sửa lỗi**: Nếu công cụ thất bại, hãy tìm cách khác. Đừng bỏ cuộc.\n"
            "4. **Kết thúc**: Khi đã đạt được mục tiêu, hãy trả lời với tiền tố 'FINAL_ANSWER:'.\n\n"
            f"{core_mem_p}"
        )
        self.history.append({"role": "system", "content": system_prompt})

        while not self.is_finished and self.step_count < self.max_steps:
            self.step_count += 1
            update_mission_world_state(self.task_id, "state_data", {"step_count": self.step_count})
            self._log("ZENITH", f"🔄 [BƯỚC {self.step_count}] Đang suy luận bước tiếp theo...", stealth=True)

            # 2. Compaction: Nén ngữ cảnh nếu cần
            self.history = await compaction_engine.condense(self.history, self.task_id)

            # 3. SUY NGHĨ & HÀNH ĐỘNG (THINK & ACT)
            try:
                traceparent_hdr = generate_trace_parent(self.task_id)
                response = await engine.call_chat(
                    messages=self.history,
                    role="RECEPTIONIST",
                    task_id=self.task_id,
                    json_mode=True
                )

                if not response:
                    self._log("ERROR", "⚠️ Model trả về phản hồi rỗng. Đang thử kích hoạt phản xạ khẩn cấp...")
                    response = await engine.call_chat(
                        messages=self.history + [{"role": "user", "content": "Hãy trả lời bằng định dạng JSON: {\"action\": \"...\", \"thought\": \"...\"}"}],
                        role="RECEPTIONIST",
                        task_id=self.task_id,
                        json_mode=True
                    )

                # 4. Phân tích hành động
                action_data = self._parse_action(response)
                self.history.append({"role": "assistant", "content": json.dumps(action_data, ensure_ascii=False)})

                if "FINAL_ANSWER" in str(action_data.get("thought", "")) or "FINAL_ANSWER" in str(action_data.get("answer", "")):
                    self.is_finished = True
                    update_mission_world_state(self.task_id, "state_data", {"status": "COMPLETED"})
                    return action_data.get("answer") or action_data.get("thought")

                # 5. THỰC THI & CHỐNG RỦI RO (EXECUTE & RISK GATE)
                tool_name = action_data.get("tool")
                tool_params = action_data.get("params") or {}

                if tool_name:
                    # 🛡️ Human Approval Risk Gate
                    requires_approval, risk_reason = eval_tool_risk(tool_name, tool_params if isinstance(tool_params, dict) else {"param": tool_params})
                    if requires_approval:
                        create_approval_interrupt(self.task_id, tool_name, tool_params, risk_reason)
                        self._log("WARN", f"🛑 [HUMAN-APPROVAL INTERCEPTED]: {tool_name} bị đánh chặn — {risk_reason}")
                        return f"⚠️ [APPROVAL-REQUIRED]: Thao tác {tool_name} bị đánh chặn bởi Human Approval Gate vì rủi ro: {risk_reason}. Cần Master phê duyệt."

                    self._log("ZENITH", f"⚙️ Thực thi công cụ `{tool_name}`...")
                    observation = await self._execute_tool(tool_name, tool_params)
                    
                    # 6. QUAN SÁT & CẬP NHẬT WORLD STATE (OBSERVE & UPDATE WORLD)
                    obs_text = f"[OBSERVATION]:\n{observation}"
                    self.history.append({"role": "user", "content": obs_text})
                    
                    record_causality_link(self.task_id, cause=f"{tool_name}({tool_params})", effect=str(observation)[:200], status="SUCCESS")

                    await cognitive_event_bus.publish(ObservationEvent(
                        task_id=self.task_id,
                        agent_id="receptionist",
                        tool_name=tool_name,
                        output=observation
                    ))
                else:
                    self._log("ZENITH", "🤔 Model chưa quyết định được hành động. Đang yêu cầu suy nghĩ lại.")
                    self.history.append({"role": "user", "content": "Bạn chưa chọn công cụ. Hãy chọn một công cụ từ danh sách SKILLS hoặc trả về FINAL_ANSWER."})

            except Exception as e:
                self._log("ERROR", f"Lỗi trong chu trình: {e}")
                record_causality_link(self.task_id, cause=f"step_{self.step_count}", effect=str(e), status="ERROR")
                self.step_count += 1
                await asyncio.sleep(1)

        return "Chu trình đã đạt giới hạn bước hoặc xảy ra lỗi nghiêm trọng thưa Master."

    def _parse_action(self, response: Any) -> Dict[str, Any]:
        """Bóc tách hành động từ phản hồi của model."""
        if isinstance(response, dict):
            return response
        try:
            # Tìm JSON trong text
            import re
            match = re.search(r"\{.*\}", str(response), re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {"thought": str(response), "tool": None}

    async def _execute_tool(self, tool_name: str, params: Any) -> str:
        """Thực thi công cụ thông qua Executor Gateway."""
        try:
            # Giả lập thực thi (Cần kết nối với executor_gateway thực tế trong Zenith)
            # Ở đây ta sẽ dùng engine.call_skill làm proxy hoặc gọi trực tiếp nếu có token
            from receptionist.executor_gateway import ExecutionRequest
            # Lưu ý: Cần CapabilityToken, trong Loop này ta giả định đã có quyền hạn tối cao
            # hoặc sẽ được Receptionist cấp phát.
            
            # TODO: Tích hợp sâu với ExecutorGateway của Zenith
            result = engine.call_skill(tool_name, params, self.task_id)
            return str(result.get("output", "Không có đầu ra."))
        except Exception as e:
            return f"Lỗi thực thi: {e}"

# 🌌 Sovereign Property of Master LeeTrung.
