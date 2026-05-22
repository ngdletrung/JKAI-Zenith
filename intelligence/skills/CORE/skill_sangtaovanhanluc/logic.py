import os
import json
import httpx
import base64
import asyncio
from datetime import datetime

# =================================================================
# 🎨 JKAI ZENITH: LOGIC SÁNG TẠO & ĐỒ HỌA (CREATIVE)
# =================================================================

async def phu_thuy_do_hoa(prompt: str, negative_prompt: str = "", steps: int = 25, width: int = 1024, height: int = 1024):
    """SIÊU CÔNG CỤ ĐỒ HỌA JKAI (Stable Diffusion ROCm)."""
    control_host = os.getenv("CONTROL_PLANE_URL", "http://ai-control-plane:8000")
    sd_host = os.getenv("SD_HOST", "http://stable-diffusion:7860")
    
    print(f"🎨 [JKAI-GRAPHIC] Master is requesting Art: '{prompt}'")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # 1. Gõ cửa Tổng quản xin bật GPU
            print("⚖️ [JKAI-STREWARD] Requesting GPU for Graphics...")
            gpu_req = await client.post(f"{control_host}/gpu/request", json={"service": "stable-diffusion"})
            if gpu_req.status_code != 200 or gpu_req.json().get("status") != "granted":
                return {"status": "error", "msg": "Tổng quản từ chối cấp GPU."}
            
            # Đợi thêm 20s để SD.Next khởi động hoàn toàn (vì SD.Next load nặng)
            print("⏳ [JKAI-WAIT] Waiting for SD.Next Engine to ignite...")
            await asyncio.sleep(20)

            # 2. Thực hiện vẽ
            sd_payload = {
                "prompt": prompt, "negative_prompt": negative_prompt,
                "steps": steps, "width": width, "height": height,
                "sampler_name": "Euler a", "cfg_scale": 7
            }
            sd_resp = await client.post(f"{sd_host}/sdapi/v1/txt2img", json=sd_payload)
            
            # 3. Báo cáo hoàn tất để Tổng quản tắt GPU ngay
            await client.post(f"{control_host}/gpu/release", json={"service": "stable-diffusion"})

            if sd_resp.status_code == 200:
                img_data = sd_resp.json()['images'][0]
                filename = f"jkai_art_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                full_path = os.path.join("/storage/graphics", filename)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                return {"status": "success", "image_path": full_path}
            else:
                return {"status": "error", "msg": f"SD Error: {sd_resp.text}"}
                
    except Exception as e:
        # Đảm bảo vẫn báo cáo release nếu có lỗi xảy ra
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{control_host}/gpu/release", json={"service": "stable-diffusion"})
        except: pass
        return {"status": "error", "msg": str(e)}

async def chup_anh_man_hinh():
    """Chụp ảnh màn hình hiện tại (Yêu cầu Visual Satellite)."""
    browser_url = os.getenv("BROWSER_SERVICE_URL", "http://ai-browser:8000")
    print("📸 [JKAI-VISION] Taking screenshot...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{browser_url}/screenshot")
            return resp.json()
    except Exception as e:
        return {"status": "error", "msg": str(e)}
