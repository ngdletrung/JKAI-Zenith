import asyncio
import os
import sys
from pydantic import ValidationError

# Thêm đường dẫn để import core và các module liên quan thưa Master
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))

from planner import Planner, Blueprint

async def test_pydantic_validation():
    print("🛡️ [TEST]: Khởi động Giao thức Kiểm tra Pydantic...")
    
    # Dữ liệu giả lập từ LLM thưa Master
    valid_data = {
        "thought": "Cần trinh sát web trước khi tổng hợp.",
        "steps": [
            {
                "id": "1",
                "tool": "web_search",
                "args": {"query": "python 2024"},
                "description": "Tìm kiếm thông tin",
                "assigned_agent": "agent_executor_beta.md",
                "hardware_target": "BETA",
                "expert_mindset": "Be fast",
                "verification": "Check results",
                "parallel": True
            }
        ],
        "rationale": "Tiết kiệm GPU cho bước sau",
        "failure_speculation": "Nếu mất mạng sẽ dùng cache"
    }
    
    try:
        model = Blueprint.model_validate(valid_data)
        print("✅ [SUCCESS]: Dữ liệu Blueprint hợp lệ thưa Master.")
        assert model.steps[0].hardware_target == "BETA"
    except ValidationError as e:
        print(f"❌ [FAILED]: Lỗi kiểm tra dữ liệu: {e}")

    invalid_data = valid_data.copy()
    invalid_data["steps"][0]["hardware_target"] = "INVALID" # Sai enum
    
    try:
        Blueprint.model_validate(invalid_data)
        print("❌ [FAILED]: Lẽ ra phải báo lỗi enum thưa Master.")
    except ValidationError:
        print("✅ [SUCCESS]: Đã phát hiện lỗi enum chính xác thưa Master.")

async def test_complexity_estimation():
    print("\n📊 [TEST]: Kiểm tra Giao thức Ước tính độ phức tạp...")
    planner = Planner()
    
    simple_goal = "Viết email chào mừng"
    complex_goal = "Phân tích và tích hợp hệ thống pipeline cho dữ liệu lớn"
    
    print(f"Goal: '{simple_goal}' -> Complexity: {planner._estimate_complexity(simple_goal)}")
    print(f"Goal: '{complex_goal}' -> Complexity: {planner._estimate_complexity(complex_goal)}")

if __name__ == "__main__":
    asyncio.run(test_pydantic_validation())
    asyncio.run(test_complexity_estimation())
