import sys
import json
import re
import logging
import asyncio
import subprocess
from typing import Dict, Any, List

logger = logging.getLogger("CognitiveReActLoop")

class ReActTurn:
    def __init__(self, turn_index: int, thought: str, action: str = None, observation: str = None):
        self.turn_index = turn_index
        self.thought = thought
        self.action = action
        self.observation = observation

    def to_dict(self) -> dict:
        return {
            "turn": self.turn_index,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation
        }

class CognitiveReActLoop:
    """
    🔄 [COGNITIVE-REACT-LOOP]: Bộ Khung Mềm Suy Luận ReAct Tự Chủ (Thought -> Action -> Observation).
    Cho phép LLM tư duy đa bước:
    1. Thought: Phân tích tình hình hiện tại.
    2. Action: Thực thi công cụ hoặc chạy mã Python động.
    3. Observation: Đọc kết quả stdout/stderr thực tế từ đĩa/sandbox.
    """
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns

    async def run_loop(self, initial_goal: str, role: str = "RECEPTIONIST", task_id: str = "sys") -> dict:
        """Thực thi vòng lặp suy luận ReAct tự chủ cho mô hình."""
        from core.utils.engine import engine
        turns: List[ReActTurn] = []
        conversation_history = [
            {"role": "system", "content": "Bạn là Tác tử Suy luận ReAct Tự chủ. Mọi bước xử lý phải tuân theo cú pháp: Thought: <suy nghĩ> -> Action: <công cụ> -> Observation: <kết quả>."},
            {"role": "user", "content": initial_goal}
        ]

        final_response = ""
        for turn_idx in range(1, self.max_turns + 1):
            logger.info(f"🔄 [REACT-TURN-{turn_idx}]: Bắt đầu chu kỳ tư duy ReAct lượt {turn_idx}/{self.max_turns}...")
            
            # Gọi LLM để sinh ra Thought & Action
            thought_text = await engine.call_chat(conversation_history, role=role, task_id=task_id, skip_build_final=True)
            if not thought_text:
                break

            turn = ReActTurn(turn_index=turn_idx, thought=thought_text)

                # Kiểm tra xem có Action thực thi mã Python hoặc công cụ không
            code_blocks = re.findall(r"```python\n(.*?)```", thought_text, re.DOTALL) or \
                          re.findall(r"```\n(.*?)```", thought_text, re.DOTALL)
            has_action_keyword = "Action:" in thought_text or "python_execute" in thought_text
            
            if code_blocks or has_action_keyword:
                action_content = thought_text
                turn.action = action_content
                
                # Thực thi mã Python động từ LLM output
                try:
                    if code_blocks:
                        python_code = code_blocks[0].strip()
                    else:
                        python_code = "print('Action acknowledged - no code block found')"
                    
                    proc = subprocess.run(
                        [sys.executable, "-c", python_code],
                        capture_output=True, text=True, timeout=30
                    )
                    obs_res = {
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                        "exit_code": proc.returncode
                    }
                    turn.observation = json.dumps(obs_res, ensure_ascii=False)
                except subprocess.TimeoutExpired:
                    turn.observation = json.dumps({"error": "Execution timed out after 30s"})
                except Exception as e:
                    turn.observation = json.dumps({"error": str(e)})

                # Cập nhật lịch sử cuộc thoại cho lượt tư duy tiếp theo
                conversation_history.append({"role": "assistant", "content": thought_text})
                conversation_history.append({"role": "user", "content": f"Observation: {turn.observation}"})
            else:
                # LLM đã hoàn thành xong Thought và không cần Action nữa -> Nhận câu trả lời cuối cùng
                final_response = thought_text
                turns.append(turn)
                break

            turns.append(turn)

        return {
            "status": "completed",
            "task_id": task_id,
            "turns_count": len(turns),
            "final_response": final_response or (turns[-1].thought if turns else "No response"),
            "trajectory": [t.to_dict() for t in turns]
        }

cognitive_react_loop = CognitiveReActLoop()
