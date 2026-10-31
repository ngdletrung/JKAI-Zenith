#!/usr/bin/env python3
"""
scripts/demo_live_mission_control.py
====================================================================
Kịch bản Điều khiển Trực quan Trực tiếp trên Mission Control (http://localhost:9999/)
Dành cho Master trực tiếp quan sát bằng mắt trên màn hình Windows.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Đảm bảo PYTHONPATH trỏ về root dự án và ai-browser
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "services" / "ai-browser"))

# BẮT BUỘC HEADED MODE ĐỂ CỬA SỔ HIỆN LÊN MÀN HÌNH MASTER
os.environ["JKAI_BROWSER_HEADLESS"] = "false"

from semantic_actuator import SemanticBrowserActuator, ActRequest, ElementRef

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LiveMissionControlDemo")

ARTIFACT_DIR = Path(r"C:\Users\AdminPC-MMO\.gemini\antigravity\brain\34ab7517-7c5f-4cc8-b833-f816792b0802")


async def inject_hud_message(page, text: str, color: str = "#00ffcc"):
    """Cập nhật banner HUD trên đầu màn hình để Master theo dõi từng bước."""
    js = f"""
    (() => {{
        let hud = document.getElementById('jkai-live-hud');
        if (!hud) {{
            hud = document.createElement('div');
            hud.id = 'jkai-live-hud';
            hud.style.position = 'fixed';
            hud.style.top = '12px';
            hud.style.left = '50%';
            hud.style.transform = 'translateX(-50%)';
            hud.style.zIndex = '2147483647';
            hud.style.padding = '12px 28px';
            hud.style.borderRadius = '12px';
            hud.style.backgroundColor = 'rgba(10, 15, 29, 0.92)';
            hud.style.border = '2px solid {color}';
            hud.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px {color}66';
            hud.style.color = '#ffffff';
            hud.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            hud.style.fontSize = '16px';
            hud.style.fontWeight = 'bold';
            hud.style.letterSpacing = '0.5px';
            hud.style.pointerEvents = 'none';
            hud.style.transition = 'all 0.3s ease';
            hud.style.display = 'flex';
            hud.style.alignItems = 'center';
            hud.style.gap = '10px';
            document.body.appendChild(hud);
        }}
        hud.style.borderColor = '{color}';
        hud.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 25px {color}88';
        hud.innerHTML = `<span>🎯</span> <span>{text}</span>`;
    }})();
    """
    try:
        await page.evaluate(js)
    except Exception as e:
        logger.warning(f"Could not inject HUD: {e}")


async def draw_som_overlays(page, elements):
    """Hiển thị nhãn Set-of-Marks (@e1, @e2, ...) trực tiếp trên màn hình."""
    labels = []
    for el in elements[:25]:
        labels.append({
            "ref_id": el.ref_id,
            "selector": el.selector,
            "tag": el.tag,
            "name": el.name[:20] if el.name else el.tag
        })
    import json
    payload = json.dumps(labels)
    js = f"""
    (() => {{
        document.querySelectorAll('.jkai-som-badge').forEach(e => e.remove());
        const data = {payload};
        data.forEach(item => {{
            try {{
                const el = document.querySelector(item.selector);
                if (el) {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {{
                        const badge = document.createElement('div');
                        badge.className = 'jkai-som-badge';
                        badge.innerText = item.ref_id;
                        badge.style.position = 'fixed';
                        badge.style.left = (rect.left + window.scrollX) + 'px';
                        badge.style.top = (rect.top + window.scrollY - 18) + 'px';
                        badge.style.background = '#e11d48';
                        badge.style.color = '#ffffff';
                        badge.style.fontSize = '11px';
                        badge.style.fontWeight = 'bold';
                        badge.style.padding = '2px 6px';
                        badge.style.borderRadius = '4px';
                        badge.style.zIndex = '2147483640';
                        badge.style.boxShadow = '0 2px 8px rgba(0,0,0,0.5)';
                        badge.style.pointerEvents = 'none';
                        document.body.appendChild(badge);
                    }}
                }}
            }} catch(e) {{}}
        }});
    }})();
    """
    try:
        await page.evaluate(js)
    except Exception as e:
        logger.warning(f"Could not draw SoM: {e}")


async def clear_som_overlays(page):
    try:
        await page.evaluate("document.querySelectorAll('.jkai-som-badge').forEach(e => e.remove());")
    except Exception:
        pass


async def run_live_demo():
    target_url = "http://localhost:9999/"
    actuator = SemanticBrowserActuator()

    logger.info("🚀 [LIVE DEMO] Đang khởi động Headed Chromium trên màn hình...")
    page = await actuator.get_or_create_page()

    try:
        # Điều chỉnh kích thước cửa sổ rộng rãi
        await page.set_viewport_size({"width": 1400, "height": 900})
        await page.bring_to_front()

        # 1. Mở trang Mission Control
        logger.info(f"🌐 [LIVE DEMO] Đang điều hướng tới {target_url}...")
        await page.goto(target_url, wait_until="networkidle", timeout=15000)
        await page.bring_to_front()

        await inject_hud_message(page, "JKAI LIVE OPERATOR: Đã kết nối Mission Control (http://localhost:9999/)!", "#00ffcc")
        await asyncio.sleep(2.0)

        # 2. Quét DOM A11y Tree
        await inject_hud_message(page, "🔍 Đang quét cấu trúc giao diện & phần tử tương tác (A11y DOM)...", "#38bdf8")
        obs = await actuator.observe(page, goal="Khám phá giao diện Mission Control")
        logger.info(f"✨ Quét được {len(obs.elements)} phần tử tương tác trên trang.")
        await asyncio.sleep(1.0)

        # 3. Hiển thị Set-of-Marks trực quan trên màn hình
        await inject_hud_message(page, f"🏷️ Hiển thị Set-of-Marks ({len(obs.elements)} phần tử đã được đánh số)...", "#f59e0b")
        await draw_som_overlays(page, obs.elements)
        # Chụp ảnh SoM
        som_shot_path = ARTIFACT_DIR / "live_mission_control_som.png"
        await page.screenshot(path=str(som_shot_path))
        logger.info(f"📸 Đã chụp ảnh SoM: {som_shot_path}")
        await asyncio.sleep(2.5)
        await clear_som_overlays(page)

        # 4. Tìm các nút hoặc tab để tương tác
        # Ưu tiên các nút điều hướng hoặc chuyển đổi
        action_elements = [e for e in obs.elements if e.role in ("button", "tab", "link", "radio")]
        logger.info(f"Danh sách nút/tab tìm thấy: {[f'{e.ref_id}: {e.name} ({e.role})' for e in action_elements[:8]]}")

        # Tìm nút Tiếng Việt / English hoặc tab bất kỳ
        target_el = None
        for el in action_elements:
            name_lower = (el.name or "").lower()
            if any(k in name_lower for k in ["tiếng việt", "english", "vi", "en", "ngôn ngữ", "workspace", "nhiệm vụ", "cài đặt", "hệ thống", "status"]):
                target_el = el
                break
        
        if not target_el and action_elements:
            target_el = action_elements[0]

        if target_el:
            logger.info(f"👉 Chuẩn bị tương tác với phần tử: {target_el.ref_id} - '{target_el.name}'")
            await inject_hud_message(page, f"👉 Chuẩn bị Click mục tiêu: [{target_el.ref_id}] '{target_el.name}'", "#ff3b30")
            
            # Thực thi hành động click có visual highlight và nhịp dừng
            req = ActRequest(
                action="click",
                target=target_el.ref_id,
                expected_snapshot_version=obs.snapshot_version
            )
            res = await actuator.act(page, req)
            logger.info(f"Kết quả click: {res.status} - {res.msg}")
            
            await inject_hud_message(page, f"✅ Đã Click thành công: [{target_el.ref_id}] '{target_el.name}'", "#22c55e")
            await asyncio.sleep(1.5)

        # 5. Quan sát lại (Fresh Observe sau Mutation - Pattern Browser-Use & Agent-S)
        await inject_hud_message(page, "🔄 Tự động tái đồng bộ DOM sau khi giao diện chuyển trạng thái...", "#38bdf8")
        obs_after = await actuator.observe(page, goal="Cập nhật sau click")
        logger.info(f"✨ Snapshot mới sau click có {len(obs_after.elements)} phần tử.")
        await asyncio.sleep(1.0)

        # 6. Tìm ô nhập task / textarea để nhập văn bản
        input_elements = [e for e in obs_after.elements if e.tag == "textarea" or e.role in ("textbox", "searchbox") or e.tag in ("input",)]
        if input_elements:
            input_el = input_elements[0]
            logger.info(f"⌨️ Tìm thấy ô nhập liệu: {input_el.ref_id} - selector '{input_el.selector}'")
            await inject_hud_message(page, f"⌨️ Gõ lệnh trực tiếp vào ô [{input_el.ref_id}]...", "#a855f7")
            await asyncio.sleep(1.0)

            sample_text = "JKAI Zenith: Kiem thu dieu khien trinh duyet truc quan Master dang quan sat."
            type_req = ActRequest(
                action="type",
                target=input_el.ref_id,
                value=sample_text,
                expected_snapshot_version=obs_after.snapshot_version
            )
            res_type = await actuator.act(page, type_req)
            logger.info(f"Kết quả nhập: {res_type.status} - {res_type.msg}")
            await inject_hud_message(page, f"✅ Đã gõ lệnh thành công vào Mission Control!", "#22c55e")
            await asyncio.sleep(2.0)

        # 7. Cuộn trang mượt mà để quan sát toàn cảnh giao diện
        await inject_hud_message(page, "📜 Đang cuộn trang (Scroll) để quan sát toàn bộ bảng điều khiển...", "#06b6d4")
        for scroll_y in [350, 700, 200, 0]:
            await page.evaluate(f"window.scrollTo({{ top: {scroll_y}, behavior: 'smooth' }});")
            await asyncio.sleep(0.7)

        # 8. Chụp ảnh kết quả cuối cùng
        final_shot_path = ARTIFACT_DIR / "live_mission_control_final.png"
        await page.screenshot(path=str(final_shot_path))
        logger.info(f"📸 Đã lưu ảnh kết quả: {final_shot_path}")

        # 9. Banner hoàn tất và giữ cửa sổ mở 6 giây để Master ngắm nhìn
        await inject_hud_message(page, "🎉 HOÀN THÀNH KIỂM THỬ TRỰC TIẾP TRÊN MISSION CONTROL!", "#10b981")
        logger.info("⏳ Giữ cửa sổ hiển thị 6 giây để Master quan sát...")
        await asyncio.sleep(6.0)

    except Exception as e:
        logger.error(f"❌ Lỗi trong quá trình live demo: {e}", exc_info=True)
    finally:
        await actuator.close_session()
        logger.info("🏁 Đã kết thúc phiên tương tác trực tiếp.")


if __name__ == "__main__":
    asyncio.run(run_live_demo())
