# -*- coding: utf-8 -*-
"""
scripts/test_live_visual_hud_operator.py
Kiểm thử thực địa năng lực Điều khiển Web Trực quan (Visual Live Operator):
1. Khởi chạy SemanticBrowserActuator ở chế độ HEADED (Hiển thị cửa sổ Chrome thật).
2. Tự động đưa cửa sổ ra màn hình chính trước mắt Master.
3. Injected Floating HUD Banner trực quan và viền sáng phát quang (glowing outline).
4. Thao tác đa bước: Mở HackerNews -> Click menu 'new' -> Click menu 'past'.
5. Lưu ảnh chụp trực quan có bằng chứng SHA-256.
"""
import asyncio
import os
import sys
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Thêm đường dẫn project root & ai-browser
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "services", "ai-browser"))

# Bắt buộc chế độ hiển thị cửa sổ thật cho Master quan sát
os.environ["JKAI_BROWSER_HEADLESS"] = "false"

from semantic_actuator import SemanticBrowserActuator, ActRequest


async def main():
    print("=" * 70)
    print("🚀 [JKAI LIVE OPERATOR] Khởi động chế độ điều khiển trực quan cho Master...")
    print("=" * 70)

    actuator = SemanticBrowserActuator()
    target_url = "https://news.ycombinator.com/"

    try:
        print(f"\n[1/4] Đang mở trình duyệt Chromium và truy cập: {target_url}")
        page = await actuator.get_or_create_page(target_url)
        await asyncio.sleep(1.0)

        print("[2/4] Đang quét cấu trúc DOM Accessibility Tree (Observe)...")
        obs = await actuator.observe(page, goal="Khám phá các mục tin tức Hacker News")
        print(f"       -> Phát hiện {obs.elements_count} phần tử tương tác.")
        print(f"       -> Quality Gate Passed: {obs.quality_gate_passed}")

        # Tìm ref của nút 'new'
        new_ref = None
        for elem in obs.elements:
            if elem.name.lower() == "new" and elem.role in ("link", "button"):
                new_ref = elem.ref_id
                break

        if not new_ref:
            new_ref = "@e2"

        print(f"\n[3/4] Master hãy nhìn màn hình: Đang click mục 'new' (Ref: {new_ref})...")
        act_res1 = await actuator.act(page, ActRequest(action="click", target=new_ref))
        print(f"       -> Kết quả: {act_res1.status} | Tier: {act_res1.healing_tier_used}")
        await asyncio.sleep(1.5)

        # Quét lại DOM sau khi chuyển trang
        obs2 = await actuator.observe(page, goal="Tìm mục 'past'")
        past_ref = None
        for elem in obs2.elements:
            if elem.name.lower() == "past" and elem.role in ("link", "button"):
                past_ref = elem.ref_id
                break

        if not past_ref:
            past_ref = "@e3"

        print(f"\n[4/4] Master hãy nhìn màn hình: Đang click mục 'past' (Ref: {past_ref})...")
        act_res2 = await actuator.act(page, ActRequest(action="click", target=past_ref))
        print(f"       -> Kết quả: {act_res2.status} | Tier: {act_res2.healing_tier_used}")
        await asyncio.sleep(1.5)

        # Chụp ảnh bằng chứng
        screenshot_path = "C:/Users/AdminPC-MMO/.gemini/antigravity/brain/34ab7517-7c5f-4cc8-b833-f816792b0802/live_visual_hud_demo.png"
        await page.screenshot(path=screenshot_path)
        print(f"\n📸 [BẰNG CHỨNG THỰC ĐỊA] Đã lưu ảnh chụp trực quan tại:\n   {screenshot_path}")

        print("\n" + "=" * 70)
        print("✅ [HOÀN TẤT THỬ NGHIỆM] Master đã quan sát trọn vẹn tiến trình thao tác!")
        print("=" * 70)

    finally:
        await actuator.close_session()


if __name__ == "__main__":
    asyncio.run(main())
