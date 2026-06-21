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
        engine.publish_mission_log(tag, f"💎🫡 [LOOP]: {msg}", self.task_id, stealth=stealth)

    async def run(self):
        """Kích hoạt chu trình tự trị thưa Master."""
        self._log("ZENITH", f"🚀 Khởi động Chu trình Tự trị cho mục tiêu: {self.goal}")
        
        # 1. Khởi tạo ngữ cảnh hệ thống
        system_prompt = (
            "# 🌌 JKAI ZENITH: GIAO THỨC CHỦ QUYỀN TỐI THƯỢNG\n"
            "Bạn đang hoạt động trong một CHU TRÌNH TỰ TRỊ (Autonomous Loop).\n"
            "Mục tiêu tối thượng: " + self.goal + "\n\n"
            "## 🏛️ QUY TẮC THỰC THI:\n"
            "1. **Một hành động mỗi lần**: Chỉ thực hiện DUY NHẤT một hành động (gọi công cụ) trong mỗi bước.\n"
            "2. **Quan sát & Phản xạ**: Sau mỗi hành động, bạn sẽ nhận được kết quả (Observation). Hãy dùng nó để quyết định bước tiếp theo.\n"
            "3. **Tự sửa lỗi**: Nếu công cụ thất bại, hãy tìm cách khác. Đừng bỏ cuộc.\n"
            "4. **Kết thúc**: Khi đã đạt được mục tiêu, hãy trả lời với tiền tố 'FINAL_ANSWER:'."
        )
        self.history.append({"role": "system", "content": system_prompt})

        while not self.is_finished and self.step_count < self.max_steps:
            self.step_count += 1
            self._log("ZENITH", f"🔄 [BƯỚC {self.step_count}] Đang suy luận bước tiếp theo...", stealth=True)

            # 2. Compaction: Nén ngữ cảnh nếu cần
            self.history = await compaction_engine.condense(self.history, self.task_id)

            # 3. SUY NGHĨ & HÀNH ĐỘNG (THINK & ACT)
            try:
                response = await engine.call_chat(
                    messages=self.history,
                    role="RECEPTIONIST", # Model 0.6B
                    task_id=self.task_id,
                    json_mode=True # Ép model xuất JSON để dễ bóc tách hành động
                )

                if not response:
                    self._log("ERROR", "⚠️ Model trả về phản hồi rỗng. Đang thử kích hoạt phản xạ khẩn cấp...")
                    # Fallback prompt for 0.6B model
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
                    return action_data.get("answer") or action_data.get("thought")

                # 5. THỰC THI (EXECUTE)
                tool_name = action_data.get("tool")
                tool_params = action_data.get("params")

                if tool_name:
                    self._log("ZENITH", f"⚙️ Thực thi công cụ `{tool_name}`...")
                    observation = await self._execute_tool(tool_name, tool_params)
                    
                    # 6. QUAN SÁT (OBSERVE)
                    obs_text = f"[OBSERVATION]:\n{observation}"
                    self.history.append({"role": "user", "content": obs_text})
                    
                    # Phát sóng sự kiện Quan sát
                    await cognitive_event_bus.publish(ObservationEvent(
                        task_id=self.task_id,
                        agent_id="receptionist_0.6b",
                        tool_name=tool_name,
                        output=observation
                    ))
                else:
                    self._log("ZENITH", "🤔 Model chưa quyết định được hành động. Đang yêu cầu suy nghĩ lại.")
                    self.history.append({"role": "user", "content": "Bạn chưa chọn công cụ. Hãy chọn một công cụ từ danh sách SKILLS hoặc trả về FINAL_ANSWER."})

            except Exception as e:
                self._log("ERROR", f"Lỗi trong chu trình: {e}")
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
