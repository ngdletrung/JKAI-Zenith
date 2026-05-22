import os
import sys
import json
import asyncio

# Đảm bảo nạp được core engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from core.utils.engine import engine

# =================================================================
# 🎨 JKAI ZENITH: LOGIC KIẾN TRÚC SƯ GIAO DIỆN (PREMIUM UI ENGINE)
# Model được xác định bởi rule_hardware.md (Markdown-as-Authority)
# =================================================================

DESIGN_TOKENS = """
[ANTIGRAVITY DESIGN SYSTEM]
- Typography: "Inter", "Outfit", "SF Pro Display", sans-serif. Không bao giờ dùng font mặc định.
- Colors:
    + Background: #0B0E14 (Deep Void)
    + Surface: rgba(255, 255, 255, 0.03) (Glass)
    + Accent: #00F0FF (Neon Cyan), #7000FF (Deep Purple)
    + Text Primary: #E2E8F0 | Text Secondary: #94A3B8
    + Border: rgba(255, 255, 255, 0.1)
- Effects:
    + Liquid Glass: backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1);
    + Glow: box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
    + Micro-animations: transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
- Layout: Flexbox/Grid, padding rộng, border-radius: 12px - 24px.
"""

async def generate_ui(component_request: str, task_id: str = None):
    """
    Sinh mã nguồn HTML/CSS/JS thuần cho giao diện cao cấp.
    Model được lấy từ rule_hardware.md (Markdown-as-Authority).
    """
    print(f"[JKAI-UI] Designing component: {component_request}")

    prompt = f"""Bạn là Kiến trúc sư Giao diện (UI Architect) mang bản sắc "Antigravity".
Nhiệm vụ: Viết code HTML/CSS/JS thuần cho: "{component_request}"

DESIGN TOKENS BẮT BUỘC PHẢI TUÂN THỦ:
{DESIGN_TOKENS}

YÊU CẦU KỸ THUẬT:
- Trả về DUY NHẤT mã nguồn HTML hoàn chỉnh (chứa thẻ <style> và <script> bên trong).
- Tích hợp Google Fonts (Inter hoặc Outfit) qua thẻ <link>.
- Thiết kế phải trông cực kỳ đắt tiền, hiện đại, có chiều sâu (shadow/glass) và có sức sống (hover effects).
- KHÔNG dùng màu cơ bản chói. KHÔNG dùng placeholder text "Lorem ipsum".

Code của bạn (bắt đầu bằng <!DOCTYPE html>):"""

    try:
        # Gọi qua engine với role EXECUTOR (sinh mã nguồn thực thi)
        # Model được lấy từ rule_hardware.md — không hardcode
        code = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="EXECUTOR",
            task_id=task_id
        )

        if isinstance(code, dict) and "error" in code:
            return {"status": "error", "msg": f"Lỗi kết nối engine: {code['error']}"}

        # Lọc code ra khỏi markdown fences nếu có
        if "```html" in code:
            code = code.split("```html")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        # Lưu kết quả
        safe_name = component_request.replace(" ", "_")[:25]
        output_file = fos.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + "/intelligence/vault/UI_{safe_name}.html"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(code)

        return {
            "status": "success",
            "output_file": output_file,
            "code_preview": code[:500],
            "msg": f"Đã thiết kế xong giao diện Premium. File: {output_file}"
        }

    except Exception as e:
        return {"status": "error", "msg": f"Lỗi UI Engine: {str(e)}"}

if __name__ == "__main__":
    req = sys.argv[1] if len(sys.argv) > 1 else "Chiếc card server status với hiệu ứng glassmorphism"
    res = asyncio.run(generate_ui(req))
    print(json.dumps(res, indent=2, ensure_ascii=True))
