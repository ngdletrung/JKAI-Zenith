# -*- coding: utf-8 -*-
"""
scripts/run_visible_browser_on_desktop.py
BẬT TRÌNH DUYỆT CỬA SỔ THẬT TRÊN MÀN HÌNH WINDOWS (HEADLESS = FALSE)
Để Master tận mắt nhìn thấy trình duyệt mở lên, tự động di chuột và click các nút trực quan!
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import os
from pathlib import Path

TARGET_URL = "https://news.ycombinator.com/"


async def run_visible_demo():
    from playwright.async_api import async_playwright
    print("🖥️ [VISIBLE DESKTOP MODE] Khởi chạy cửa sổ trình duyệt Chromium thật trên màn hình của Master...")

    async with async_playwright() as p:
        # BẬT CỬA SỔ HIỂN THỊ TRÊN MÀN HÌNH (headless=False)
        # slow_mo=1000: Mỗi thao tác dừng 1 giây để Master quan sát rõ ràng
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1200,
            args=["--start-maximized", "--window-position=100,100", "--window-size=1280,800"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # 1. Mở trang chủ
        print(f"🌐 [1/4] Đang mở trang web: {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="networkidle")
        print("👀 Master hãy nhìn lên màn hình: Trình duyệt Chromium đã xuất hiện!")
        await page.wait_for_timeout(3000)

        # 2. Tự động click vào mục 'new'
        print("🖱️ [2/4] Chuột chuẩn bị tự động click vào mục 'new' (Bài viết mới)...")
        new_link = page.locator("a:text('new')").first
        await new_link.highlight() # Làm nổi bật viền phần tử trên màn hình
        await page.wait_for_timeout(1500)
        await new_link.click()
        await page.wait_for_load_state("networkidle")
        print(f"👉 Đã click thành công! Trang hiện tại: {page.url}")
        await page.wait_for_timeout(3000)

        # 3. Tự động click vào mục 'ask'
        print("🖱️ [3/4] Chuột chuẩn bị tự động click vào mục 'ask' (Hỏi đáp cộng đồng)...")
        ask_link = page.locator("a:text('ask')").first
        await ask_link.highlight()
        await page.wait_for_timeout(1500)
        await ask_link.click()
        await page.wait_for_load_state("networkidle")
        print(f"👉 Đã click thành công! Trang hiện tại: {page.url}")
        await page.wait_for_timeout(3000)

        # 4. Tự động click vào mục 'past'
        print("🖱️ [4/4] Chuột chuẩn bị tự động click vào mục 'past' (Xem bài viết cũ)...")
        past_link = page.locator("a:text('past')").first
        await past_link.highlight()
        await page.wait_for_timeout(1500)
        await past_link.click()
        await page.wait_for_load_state("networkidle")
        print(f"👉 Đã click thành công! Trang hiện tại: {page.url}")
        await page.wait_for_timeout(3000)

        print("\n🎉 Hoàn tất chuỗi demo trực quan! Đóng trình duyệt sau 2 giây...")
        await page.wait_for_timeout(2000)
        await browser.close()
        print("✅ Demo kết thúc thành công!")


if __name__ == "__main__":
    asyncio.run(run_visible_demo())
