# -*- coding: utf-8 -*-
"""
scripts/run_live_autonomous_clicks.py
Thực thi kiểm nghiệm tương tác tự động đa bước (Multi-Step Visual Browser Action):
Mở trang web thật, quét Set-of-Marks, thực hiện chuỗi click chuột thật và đo Visual Diff từng bước.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import io
import json
import os
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "services" / "ai-browser"))

from visual_aci_gateway import VisualACIGateway

ARTIFACT_DIR = Path(r"C:\Users\AdminPC-MMO\.gemini\antigravity\brain\34ab7517-7c5f-4cc8-b833-f816792b0802")
TARGET_URL = "https://news.ycombinator.com/"


async def run_multistep_clicks():
    from playwright.async_api import async_playwright
    print(f"🚀 [MULTI-STEP CLICK TEST] Khởi chạy Playwright Chromium tới {TARGET_URL}...")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # ── BƯỚC 1: MỞ TRANG GỐC (BASELINE) ──
        print(f"\n[BƯỚC 1] Điều hướng tới {TARGET_URL}")
        resp = await page.goto(TARGET_URL, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        title_1 = await page.title()
        print(f"   - HTTP Status: {resp.status if resp else 'N/A'}")
        print(f"   - Tiêu đề: '{title_1}'")

        base_bytes = await page.screenshot(type="png")
        base_path = ARTIFACT_DIR / "live_step1_baseline.png"
        base_path.write_bytes(base_bytes)
        print(f"   - Đã lưu ảnh chụp gốc: {base_path.name} ({len(base_bytes):,} bytes)")

        # Quét phần tử tương tác trên menu
        elements_1 = await extract_interactables(page)
        print(f"   - Phát hiện {len(elements_1)} phần tử tương tác trên DOM.")

        som_bytes_1 = VisualACIGateway.render_set_of_marks(base_bytes, elements_1)
        som_path_1 = ARTIFACT_DIR / "live_step1_som.png"
        som_path_1.write_bytes(som_bytes_1)
        print(f"   - Đã tạo Set-of-Marks overlay: {som_path_1.name}")

        # ── BƯỚC 2: CLICK LẦN 1 — CHỌN MỤC 'new' ──
        print(f"\n[BƯỚC 2] Thực hiện CLICK lần 1 vào mục 'new' (Bài đăng mới nhất)")
        target_new = next((el for el in elements_1 if el["name"].strip().lower() == "new"), None)
        if not target_new:
            # Fallback lấy link thứ 2
            target_new = elements_1[1]

        cx1 = (target_new["bbox"][0] + target_new["bbox"][2]) / 2
        cy1 = (target_new["bbox"][1] + target_new["bbox"][3]) / 2
        print(f"   - Click tọa độ: ({cx1:.1f}, {cy1:.1f}) | Phần tử: {target_new['id']} ('{target_new['name']}')")
        
        await page.mouse.click(cx1, cy1)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        step2_bytes = await page.screenshot(type="png")
        step2_path = ARTIFACT_DIR / "live_step2_after_click_new.png"
        step2_path.write_bytes(step2_bytes)
        title_2 = await page.title()
        url_2 = page.url
        print(f"   - URL mới: {url_2}")
        print(f"   - Đã lưu ảnh chụp sau click 1: {step2_path.name}")

        diff_1 = VisualACIGateway.compute_visual_diff(base_bytes, step2_bytes)
        print(f"   - Visual Diff so với gốc: {diff_1.get('diff_percentage')} % | state_changed={diff_1.get('state_changed')}")

        results.append({
            "step": 1,
            "action": "click",
            "target": target_new["name"],
            "url_after": url_2,
            "diff_pct": diff_1.get("diff_percentage"),
            "state_changed": diff_1.get("state_changed"),
            "image": step2_path.name
        })

        # Quét phần tử trên trang mới
        elements_2 = await extract_interactables(page)
        som_bytes_2 = VisualACIGateway.render_set_of_marks(step2_bytes, elements_2)
        som_path_2 = ARTIFACT_DIR / "live_step2_som.png"
        som_path_2.write_bytes(som_bytes_2)

        # ── BƯỚC 3: CLICK LẦN 2 — CHỌN MỤC 'ask' ──
        print(f"\n[BƯỚC 3] Thực hiện CLICK lần 2 vào mục 'ask' (Hỏi đáp cộng đồng)")
        target_ask = next((el for el in elements_2 if el["name"].strip().lower() == "ask"), None)
        if not target_ask:
            target_ask = elements_2[4] if len(elements_2) > 4 else elements_2[0]

        cx2 = (target_ask["bbox"][0] + target_ask["bbox"][2]) / 2
        cy2 = (target_ask["bbox"][1] + target_ask["bbox"][3]) / 2
        print(f"   - Click tọa độ: ({cx2:.1f}, {cy2:.1f}) | Phần tử: {target_ask['id']} ('{target_ask['name']}')")

        await page.mouse.click(cx2, cy2)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        step3_bytes = await page.screenshot(type="png")
        step3_path = ARTIFACT_DIR / "live_step3_after_click_ask.png"
        step3_path.write_bytes(step3_bytes)
        url_3 = page.url
        print(f"   - URL mới: {url_3}")
        print(f"   - Đã lưu ảnh chụp sau click 2: {step3_path.name}")

        diff_2 = VisualACIGateway.compute_visual_diff(step2_bytes, step3_bytes)
        print(f"   - Visual Diff so với bước 2: {diff_2.get('diff_percentage')} % | state_changed={diff_2.get('state_changed')}")

        results.append({
            "step": 2,
            "action": "click",
            "target": target_ask["name"],
            "url_after": url_3,
            "diff_pct": diff_2.get("diff_percentage"),
            "state_changed": diff_2.get("state_changed"),
            "image": step3_path.name
        })

        # ── BƯỚC 4: CLICK LẦN 3 — CHỌN MỤC 'past' ──
        print(f"\n[BƯỚC 4] Thực hiện CLICK lần 3 vào mục 'past' (Xem lịch sử bài viết)")
        elements_3 = await extract_interactables(page)
        target_past = next((el for el in elements_3 if el["name"].strip().lower() == "past"), None)
        if not target_past:
            target_past = elements_3[2] if len(elements_3) > 2 else elements_3[0]

        cx3 = (target_past["bbox"][0] + target_past["bbox"][2]) / 2
        cy3 = (target_past["bbox"][1] + target_past["bbox"][3]) / 2
        print(f"   - Click tọa độ: ({cx3:.1f}, {cy3:.1f}) | Phần tử: {target_past['id']} ('{target_past['name']}')")

        await page.mouse.click(cx3, cy3)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        step4_bytes = await page.screenshot(type="png")
        step4_path = ARTIFACT_DIR / "live_step4_after_click_past.png"
        step4_path.write_bytes(step4_bytes)
        url_4 = page.url
        print(f"   - URL mới: {url_4}")
        print(f"   - Đã lưu ảnh chụp sau click 3: {step4_path.name}")

        diff_3 = VisualACIGateway.compute_visual_diff(step3_bytes, step4_bytes)
        print(f"   - Visual Diff so với bước 3: {diff_3.get('diff_percentage')} % | state_changed={diff_3.get('state_changed')}")

        results.append({
            "step": 3,
            "action": "click",
            "target": target_past["name"],
            "url_after": url_4,
            "diff_pct": diff_3.get("diff_percentage"),
            "state_changed": diff_3.get("state_changed"),
            "image": step4_path.name
        })

        await browser.close()
        print("\n✅ HOÀN TẤT CHUỖI 3 BƯỚC CLICK THỰC TẾ TRÊN WEB THẬT!")

        return {
            "initial_url": TARGET_URL,
            "steps": results,
            "baseline_image": base_path.name,
            "som_image_1": som_path_1.name,
            "som_image_2": som_path_2.name
        }


async def extract_interactables(page):
    return await page.evaluate("""() => {
        const interactables = [];
        const tags = ['button', 'a', 'input', 'select', 'textarea', '[role="button"]', '[role="tab"]'];
        const elems = document.querySelectorAll(tags.join(', '));
        let idx = 1;
        for (const el of elems) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 5 && rect.height > 5 && rect.top >= 0 && rect.left >= 0 && rect.top < 800) {
                const style = window.getComputedStyle(el);
                if (style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0') {
                    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || '').trim();
                    if (text.length > 0 && text.length < 50) {
                        interactables.push({
                            id: '@e' + idx,
                            name: text,
                            tag: el.tagName.toLowerCase(),
                            role: el.getAttribute('role') || el.tagName.toLowerCase(),
                            bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
                            selector: el.id ? '#' + el.id : el.tagName.toLowerCase()
                        });
                        idx++;
                    }
                }
            }
        }
        return interactables;
    }""")


if __name__ == "__main__":
    report = asyncio.run(run_multistep_clicks())
    print("\n[BÁO CÁO TỔNG HỢP KIỂM CHỨNG]:")
    print(json.dumps(report, indent=2, ensure_ascii=False))
