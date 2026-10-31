# -*- coding: utf-8 -*-
"""
scripts/run_mission_control_live_test.py
Thực thi kiểm nghiệm trực tiếp trên Trung tâm Điều hành JKAI: http://localhost:9999/
Sử dụng Playwright Chromium thật + Visual ACI Gateway (Set-of-Marks & Visual Diff).
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
URL = "http://localhost:9999/"


async def run_live_mission_control_test():
    from playwright.async_api import async_playwright
    print(f"[LIVE MISSION CONTROL TEST] Khoi chay Playwright Chromium toi {URL}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print(f"[NAVIGATE] Dang dieu huong toi: {URL}")
        resp = await page.goto(URL, wait_until="networkidle", timeout=15000)
        print(f"[HTTP] Status: {resp.status if resp else 'N/A'}")

        # Cho DOM va React render
        await page.wait_for_timeout(2500)
        title = await page.title()
        print(f"[TITLE] Tieu de trang: '{title}'")

        # 1. Chup anh man hinh Baseline that
        baseline_bytes = await page.screenshot(type="png")
        baseline_path = ARTIFACT_DIR / "mission_control_baseline_live.png"
        baseline_path.write_bytes(baseline_bytes)
        print(f"[BASELINE] Da luu anh chup: {baseline_path.name} ({len(baseline_bytes):,} bytes)")

        # 2. Trich xuat cac phan tu tuong tac thuc te tren DOM
        elements_data = await page.evaluate("""() => {
            const interactables = [];
            const tags = ['button', 'a', 'input', 'select', 'textarea', '[role="button"]', '[role="tab"]'];
            const elems = document.querySelectorAll(tags.join(', '));
            let idx = 1;
            for (const el of elems) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 5 && rect.height > 5 && rect.top >= 0 && rect.left >= 0) {
                    const style = window.getComputedStyle(el);
                    if (style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0') {
                        const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || '').trim();
                        interactables.push({
                            id: '@e' + idx,
                            name: text.substring(0, 40) || (el.tagName.toLowerCase() + '_' + idx),
                            tag: el.tagName.toLowerCase(),
                            role: el.getAttribute('role') || el.tagName.toLowerCase(),
                            bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
                            selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase())
                        });
                        idx++;
                    }
                }
            }
            return interactables;
        }""")

        print(f"[SOM] Phat hien {len(elements_data)} phan tu tuong tac thuc te tren giao dien!")
        for el in elements_data[:10]:
            print(f"   - {el['id']}: [{el['tag']}] '{el['name']}' tai {el['bbox']}")

        # 3. Ve Set-of-Marks (SoM Engine)
        som_bytes = VisualACIGateway.render_set_of_marks(baseline_bytes, elements_data)
        som_path = ARTIFACT_DIR / "mission_control_som_live.png"
        som_path.write_bytes(som_bytes)
        print(f"[SOM-IMAGE] Da ve Set-of-Marks overlay va luu tai: {som_path.name}")

        # 4. Thuc hien hanh dong click that vao mot tab/nut dieu huong
        clicked_target = None
        if len(elements_data) > 0:
            target = elements_data[0]
            clicked_target = target
            print(f"[ACTION] Dang thuc hien CLICK that vao phan tu {target['id']} ('{target['name']}')...")
            
            # Click vao toa do trung tam cua bbox
            cx = (target['bbox'][0] + target['bbox'][2]) / 2
            cy = (target['bbox'][1] + target['bbox'][3]) / 2
            await page.mouse.click(cx, cy)
            await page.wait_for_timeout(2000)

        # 5. Chup anh man hinh sau khi tuong tac
        action_bytes = await page.screenshot(type="png")
        action_path = ARTIFACT_DIR / "mission_control_action_live.png"
        action_path.write_bytes(action_bytes)
        print(f"[ACTION-IMAGE] Da luu anh chup sau khi click: {action_path.name} ({len(action_bytes):,} bytes)")

        # 6. Do luong Visual Diff that
        diff_res = VisualACIGateway.compute_visual_diff(baseline_bytes, action_bytes)
        diff_pct = diff_res.get("diff_percentage", 0.0)
        state_changed = diff_res.get("state_changed", False)
        print(f"[VISUAL-DIFF] Do bien thien hinh anh thuc te: {diff_pct:.2f}% | state_changed={state_changed}")

        await browser.close()
        print("[SUCCESS] Hoan tat bai kiem nghiem truc tiep tren Mission Control!")

        return {
            "title": title,
            "url": URL,
            "elements_count": len(elements_data),
            "elements": elements_data,
            "clicked_target": clicked_target,
            "diff_pct": diff_pct,
            "diff_res": diff_res,
            "baseline_path": str(baseline_path),
            "som_path": str(som_path),
            "action_path": str(action_path)
        }


if __name__ == "__main__":
    res = asyncio.run(run_live_mission_control_test())
    print("\n[SUMMARY]:")
    print(json.dumps({
        "url": res["url"],
        "title": res["title"],
        "elements_count": res["elements_count"],
        "clicked": res["clicked_target"]["name"] if res["clicked_target"] else None,
        "diff_pct": f"{res['diff_pct']:.2f}%"
    }, indent=2, ensure_ascii=False))
