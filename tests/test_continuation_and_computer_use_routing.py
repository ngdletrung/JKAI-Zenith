# -*- coding: utf-8 -*-
"""
tests/test_continuation_and_computer_use_routing.py
Kiểm thử chuyên sâu cho:
1. Tiếp nối ngữ cảnh khi chạm trần token (Continuation Memory Handler & Routing).
2. Tự động nhận diện tác vụ Computer-Use / WebFig sang Visual Browser ACI.
3. Ánh xạ các bí danh Visual ACI Gateway trong Tool Router.
"""
from pathlib import Path
import pytest
from core.os.routing.intent_router import intent_router, IntentMode
from core.kernel.tool_arbiter import tool_arbiter, ToolDomain


class TestContinuationRouting:
    @pytest.mark.parametrize("cue", [
        "tiếp tục",
        "tiếp",
        "tiep tuc",
        "continue",
        "tiếp đi",
        "viết tiếp",
        "nói tiếp",
        "làm tiếp",
        "chạy tiếp",
        "trình bày tiếp",
        "tiếp tục nào",
        "tiếp tục đi",
    ])
    def test_continuation_cues_route_to_reasoning_not_chat(self, cue: str):
        """Khẩu lệnh 'tiếp tục' phải luôn định tuyến về REASONING / PLANNER, tuyệt đối không trôi sang CHAT."""
        decision = intent_router.route(cue)
        assert decision.mode == IntentMode.REASONING
        assert decision.role == "PLANNER"
        assert "CONTINUATION" in decision.tags
        assert "ANALYSIS" in decision.tags
        assert decision.confidence >= 0.95


class TestComputerUseWebGUIRouting:
    def test_mikrotik_webfig_task_routes_to_browser_aci(self):
        """Nhiệm vụ cấu hình MikroTik WebFig phải được Arbiter phân về BROWSER trực quan thực thi thật."""
        prompt = "Tự động phân tích quy trình cấu hình tường lửa MikroTik qua giao diện WebFig và đề xuất các bước click trực quan an toàn."
        verdict = tool_arbiter.arbitrate(prompt)

        assert verdict.primary_domain == ToolDomain.BROWSER
        assert verdict.is_visual_required is True
        assert "BROWSER_CONTROL" in verdict.mandatory_tools
        assert "visual_aci_gateway" in verdict.mandatory_tools
        assert verdict.primary_target is not None
        assert "127.0.0.1:8765" in verdict.primary_target or "8000" in verdict.primary_target

    def test_generic_web_click_routes_to_browser(self):
        """Nhiệm vụ yêu cầu thao tác click trên giao diện web phải chuyển sang Browser."""
        prompt = "Thao tác trên giao diện web click vào nút Đăng nhập và chụp ảnh màn hình"
        verdict = tool_arbiter.arbitrate(prompt)

        assert verdict.primary_domain == ToolDomain.BROWSER
        assert verdict.is_visual_required is True
        assert "visual_aci_gateway" in verdict.mandatory_tools


class TestToolRouterAliases:
    def test_tool_router_recognizes_visual_aci_aliases(self):
        """Tool router phải tự động ánh xạ các alias của Visual ACI Gateway sang BROWSER_VISION_OPS."""
        router_path = Path("services/ai-executor/tool_router.py")
        assert router_path.exists()
        content = router_path.read_text(encoding="utf-8")
        assert "VISUAL_ACI_GATEWAY" in content
        assert "VISUAL_COMPUTER_USE" in content
        assert "SOM_BROWSER_CLICK" in content
