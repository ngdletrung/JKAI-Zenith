# -*- coding: utf-8 -*-
"""
scripts/pop_front_visible_chrome.py
BẬT TRÌNH DUYỆT GOOGLE CHROME THẬT LÊN MẶT TIỀN (FOREGROUND) MÀN HÌNH WINDOWS
Banner nổi phía dưới đáy màn hình để không che khuất thanh menu!
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import ctypes
import time
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET_URL = "https://news.ycombinator.com/"


def bring_window_to_front():
    """Ép cửa sổ Chrome nhảy lên trước tất cả các cửa sổ khác trên Windows."""
    user32 = ctypes.windll.user32
    time.sleep(1.0)
    
    def enum_windows_callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "Chrome" in title or "Hacker News" in title:
                    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
                    user32.SetForegroundWindow(hwnd)
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)


async def run_foreground_chrome():
    from playwright.async_api import async_playwright
    print("🚀 [CHROME FOREGROUND] Đang khởi chạy Google Chrome thật lên màn hình desktop...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=False,
            args=[
                "--start-maximized",
                "--new-window",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        # Ép Chrome nổi lên trên cùng
        bring_window_to_front()

        print(f"🌐 [1/3] Đang tải trang: {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="networkidle")
        bring_window_to_front()

        # Chèn Banner nổi phía dưới đáy màn hình
        await page.evaluate("""() => {
            const banner = document.createElement('div');
            banner.id = 'jkai-robot-banner';
            banner.innerHTML = '🤖 <b>JKAI ZENITH ĐANG ĐIỀU KHIỂN CHROME TRỰC TIẾP TRÊN MÀN HÌNH CỦA MASTER!</b> (Chuẩn bị click các nút)';
            banner.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:#e11d48;color:#ffffff;font-size:20px;font-family:sans-serif;padding:16px 28px;z-index:2147483647;text-align:center;font-weight:bold;box-shadow:0 10px 25px rgba(0,0,0,0.5);border-radius:12px;border:2px solid #ffe4e6;pointer-events:none;';
            document.body.appendChild(banner);
        }""")
        print("👀 Banner thông báo đã xuất hiện phía dưới màn hình Chrome!")
        await page.wait_for_timeout(3000)

        # Thao tác 1: Click nút 'new'
        print("🖱️ [2/3] JKAI đang định vị và click vào mục 'new'...")
        await page.evaluate("""() => {
            const el = document.querySelector("a[href='newest']");
            if (el) {
                el.style.outline = '4px solid #f43f5e';
                el.style.backgroundColor = '#fecdd3';
            }
        }""")
        await page.wait_for_timeout(1500)
        await page.click("a[href='newest']", force=True)
        await page.wait_for_load_state("networkidle")
        
        # Cập nhật banner trên trang mới
        await page.evaluate("""() => {
            const banner = document.createElement('div');
            banner.innerHTML = '✅ <b>BƯỚC 1 THÀNH CÔNG: Đã click nút [new] chuyển sang trang mới!</b> (Chuẩn bị click tiếp [ask])';
            banner.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:#059669;color:#ffffff;font-size:20px;font-family:sans-serif;padding:16px 28px;z-index:2147483647;text-align:center;font-weight:bold;box-shadow:0 10px 25px rgba(0,0,0,0.5);border-radius:12px;border:2px solid #a7f3d0;pointer-events:none;';
            document.body.appendChild(banner);
        }""")
        print(f"👉 Trang hiện tại: {page.url}")
        await page.wait_for_timeout(3500)

        # Thao tác 2: Click nút 'ask'
        print("🖱️ [3/3] JKAI đang định vị và click vào mục 'ask'...")
        await page.evaluate("""() => {
            const el = document.querySelector("a[href='ask']");
            if (el) {
                el.style.outline = '4px solid #059669';
                el.style.backgroundColor = '#a7f3d0';
            }
        }""")
        await page.wait_for_timeout(1500)
        await page.click("a[href='ask']", force=True)
        await page.wait_for_load_state("networkidle")

        # Cập nhật banner hoàn tất
        await page.evaluate("""() => {
            const banner = document.createElement('div');
            banner.innerHTML = '🎉 <b>HOÀN TẤT: JKAI đã tự động click xong 2 bước! Giữ màn hình 8 giây để Master xem...</b>';
            banner.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:#2563eb;color:#ffffff;font-size:20px;font-family:sans-serif;padding:16px 28px;z-index:2147483647;text-align:center;font-weight:bold;box-shadow:0 10px 25px rgba(0,0,0,0.5);border-radius:12px;border:2px solid #bfdbfe;pointer-events:none;';
            document.body.appendChild(banner);
        }""")
        print(f"👉 Trang hiện tại: {page.url}")
        print("⏳ Giữ cửa sổ trên màn hình 8 giây để Master quan sát...")
        await page.wait_for_timeout(8000)

        await browser.close()
        print("✅ Hoàn tất toàn bộ chu trình điều khiển trực tiếp trên màn hình!")


if __name__ == "__main__":
    asyncio.run(run_foreground_chrome())
