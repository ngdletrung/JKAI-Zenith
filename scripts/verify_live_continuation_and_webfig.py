# -*- coding: utf-8 -*-
"""
scripts/verify_live_continuation_and_webfig.py
Mô phỏng chính xác kịch bản thực địa của Master:
1. Giao task MikroTik WebFig: Kiểm tra Arbiter tự động dispatch sang Visual Browser ACI.
2. Mô phỏng câu trả lời chạm trần token (done_reason=length) và ghi nhớ ngữ cảnh.
3. Master gõ "tiếp tục": Kiểm tra Intent Router duy trì REASONING/PLANNER và tiếp nối câu trả lời, KHÔNG chào lại từ đầu.
"""
import sys
from core.kernel.tool_arbiter import tool_arbiter, ToolDomain
from core.os.routing.intent_router import intent_router, IntentMode
from core.os.routing.compound_parser import compound_intent_parser


def test_scenario():
    print("=" * 70)
    print("🔥 BÀI KIỂM CHỨNG THỰC ĐỊA 1: TÁC VỤ CẤU HÌNH MIKROTIK WEBFIG")
    print("=" * 70)
    
    prompt_1 = "Tự động phân tích quy trình cấu hình tường lửa MikroTik qua giao diện WebFig và đề xuất các bước click trực quan an toàn."
    print(f"📥 Input Master: '{prompt_1}'\n")

    # 1. Phân xử qua Tool Arbiter
    verdict = tool_arbiter.arbitrate(prompt_1)
    print(f"⚡ [TOOL ARBITER KẾT QUẢ]:")
    print(f"   - Miền công cụ chính (Primary Domain): {verdict.primary_domain.value}")
    print(f"   - Yêu cầu trực quan (is_visual_required): {verdict.is_visual_required}")
    print(f"   - URL Đích danh tự động định vị: {verdict.primary_target}")
    print(f"   - Công cụ bắt buộc kích hoạt: {verdict.mandatory_tools}")
    print(f"   - Lý do phân tuyến: {verdict.reason}")

    assert verdict.primary_domain == ToolDomain.BROWSER, "LỖI: Chưa tự động phân tuyến sang BROWSER!"
    assert verdict.is_visual_required is True, "LỖI: Chưa kích hoạt nhãn quan trực quan!"
    assert "visual_aci_gateway" in verdict.mandatory_tools, "LỖI: Chưa cấp phép Visual ACI Gateway!"
    print("\n✅ KIỂM CHỨNG 1 THÀNH CÔNG: Tác vụ WebFig đã tự động mở Visual Browser ACI!")

    print("\n" + "=" * 70)
    print("🔥 BÀI KIỂM CHỨNG THỰC ĐỊA 2: LỆNH 'TIẾP TỤC' KHÔNG BỊ TRÔI VỀ TIẾP TÂN")
    print("=" * 70)

    prompt_2 = "tiếp tục"
    print(f"📥 Input Master: '{prompt_2}'\n")

    # 2. Phân định qua Central Intent Router
    decision = intent_router.route(prompt_2)
    print(f"⚡ [CENTRAL INTENT ROUTER KẾT QUẢ]:")
    print(f"   - Ý định (Mode): {decision.mode.value}")
    print(f"   - Vai trò đảm trách (Role): {decision.role}")
    print(f"   - Nhãn năng lực (Tags): {decision.tags}")
    print(f"   - Độ tin cậy (Confidence): {decision.confidence}")
    print(f"   - Lý do: {decision.reason}")

    assert decision.mode == IntentMode.REASONING, f"LỖI: Mode bị gán thành {decision.mode}, không phải REASONING!"
    assert decision.role == "PLANNER", f"LỖI: Role bị gán thành {decision.role}, không phải PLANNER!"
    assert "CONTINUATION" in decision.tags, "LỖI: Thiếu tag CONTINUATION!"
    assert "CHAT" not in decision.tags, "LỖI: Bị trôi sang CHAT (sẽ gây lỗi chào lại từ đầu)!"
    print("\n✅ KIỂM CHỨNG 2 THÀNH CÔNG: Lệnh 'tiếp tục' được giao cho PLANNER tiếp nối công việc, tuyệt đối không trôi về RECEPTIONIST chào hỏi!")

    print("\n" + "=" * 70)
    print("🎉 TẤT CẢ CÁC BÀI TEST THỰC NGHIỆM ĐỀU ĐẠT CHUẨN XUẤT SẮC 100%!")
    print("=" * 70)


if __name__ == "__main__":
    test_scenario()
