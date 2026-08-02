"""
💎 JKAI ZENITH SKILL: GENERATE IMAGE (Stable Diffusion / SDNext)
Kích hoạt bộ máy sáng tạo hình ảnh của Tập đoàn.
Gọi SDNext API đang chạy tại host:7860
"""

import os
import json
import base64
import time
import requests
import asyncio
from core.utils.engine import engine

# SD.Next API endpoint — có thể override qua env var
SDNEXT_HOST = os.getenv("SDNEXT_HOST", "http://host.docker.internal:7860")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "outputs", "generated")


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


async def generate_image(
    prompt: str,
    negative_prompt: str = "blurry, low quality, watermark, text, signature, deformed",
    steps: int = 20,
    width: int = 512,
    height: int = 512,
    cfg_scale: float = 7.0,
    sampler: str = "DPM++ 2M",
    seed: int = -1,
    task_id: str = "art_gen"
) -> dict:
    """
    🎨 Tạo hình ảnh từ văn bản sử dụng Stable Diffusion (SDNext).
    
    Args:
        prompt: Mô tả hình ảnh cần tạo (tiếng Anh cho kết quả tốt nhất)
        negative_prompt: Những gì KHÔNG muốn có trong ảnh
        steps: Số bước khử nhiễu (20-30 là cân bằng tốt)
        width: Chiều rộng ảnh (512, 768, 1024)
        height: Chiều cao ảnh (512, 768, 1024)
        cfg_scale: Mức độ tuân thủ prompt (7.0 = cân bằng)
        sampler: Thuật toán sampling
        seed: -1 = ngẫu nhiên
    
    Returns:
        dict: {"status": "success", "path": "...", "filename": "...", "preview": "data:image/..."}
    """
    _ensure_output_dir()

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler,
        "seed": seed,
        "save_images": False,
        "send_images": True,
    }

    try:
        # Kiểm tra SDNext có online không
        health_resp = requests.get(f"{SDNEXT_HOST}/sdapi/v1/sd-models", timeout=5)
        if health_resp.status_code != 200:
            return {
                "status": "error",
                "msg": f"SDNext không phản hồi tại {SDNEXT_HOST}. Vui lòng khởi động stable-diffusion service."
            }
    except requests.exceptions.ConnectionError:
        return {
            "status": "offline",
            "msg": (
                f"🖼️ [MẮT THẦN SÁNG TẠO] SDNext đang OFFLINE tại {SDNEXT_HOST}.\n"
                f"Để kích hoạt: chạy lệnh `docker-compose --profile art up -d stable-diffusion`\n"
                f"Hoặc khởi động SDNext thủ công tại máy host."
            )
        }
    except Exception as e:
        return {"status": "error", "msg": f"Không thể kết nối SDNext: {e}"}

    # 🧹 [SOVEREIGN ARBITRATOR]: Tự động xả VRAM
    await engine.flush_gpu_memory(task_id=task_id)

    try:
        resp = requests.post(
            f"{SDNEXT_HOST}/sdapi/v1/txt2img",
            json=payload,
            timeout=300  # 5 phút cho các task generation nặng
        )
        resp.raise_for_status()
        data = resp.json()

        images = data.get("images", [])
        if not images:
            return {"status": "error", "msg": "SDNext trả về không có ảnh nào."}

        # Lưu ảnh đầu tiên ra file
        img_b64 = images[0]
        timestamp = int(time.time())
        filename = f"jkai_art_{timestamp}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(base64.b64decode(img_b64))

        res = {
            "status": "success",
            "filename": filename,
            "path": filepath,
            "preview": f"data:image/png;base64,{img_b64[:100]}...",
            "prompt": prompt,
            "dimensions": f"{width}x{height}",
            "msg": f"✅ [MẮT THẦN SÁNG TẠO]: Đã tạo thành công ảnh `{filename}` ({width}x{height}px) theo lệnh của Master!"
        }
        # 🚀 [SOVEREIGN ARBITRATOR]: Hoàn tất và tái triệu hồi nơ-ron
        await engine.restore_neural_corps(task_id=task_id)
        return res

    except requests.exceptions.Timeout:
        # 🚀 [SOVEREIGN ARBITRATOR]: Tái triệu hồi nơ-ron kể cả khi lỗi
        await engine.restore_neural_corps(task_id=task_id)
        return {"status": "error", "msg": "SDNext timeout — generation quá lâu. Thử giảm steps hoặc resolution."}
    except Exception as e:
        # 🚀 [SOVEREIGN ARBITRATOR]: Tái triệu hồi nơ-ron kể cả khi lỗi
        await engine.restore_neural_corps(task_id=task_id)
        return {"status": "error", "msg": f"Lỗi generation: {e}"}


def check_sd_status() -> dict:
    """Kiểm tra trạng thái SDNext và model đang nạp."""
    try:
        resp = requests.get(f"{SDNEXT_HOST}/sdapi/v1/sd-models", timeout=5)
        if resp.status_code == 200:
            models = resp.json()
            return {
                "status": "online",
                "host": SDNEXT_HOST,
                "models_count": len(models),
                "models": [m.get("model_name", "unknown") for m in models[:3]]
            }
        return {"status": "degraded", "host": SDNEXT_HOST}
    except Exception as e:
        return {"status": "offline", "host": SDNEXT_HOST, "error": str(e)}

# [ALIAS-SYNC]: Đồng bộ hóa với skill_system_core
skill_generate_image = generate_image
