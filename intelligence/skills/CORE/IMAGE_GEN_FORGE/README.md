# 🎨 Skill: generate_image

**Danh mục:** Sáng tạo Hình ảnh (Visual Creation)
**Phiên bản:** v1.0 — JKAI Zenith

## Mô tả
Kích hoạt bộ máy sáng tạo hình ảnh của Tập đoàn thông qua Stable Diffusion (SDNext).
Tạo hình ảnh từ văn bản mô tả (Text-to-Image) với GPU RX 6600 của Master.

## Các hàm

### `generate_image(prompt, negative_prompt, steps, width, height, cfg_scale, sampler, seed)`
Tạo một hình ảnh mới từ prompt.

**Ví dụ gọi từ Planner:**
```json
{
  "tool": "generate_image",
  "args": {
    "prompt": "a futuristic cyberpunk city at night, neon lights, ultra detailed, 8k",
    "negative_prompt": "blurry, low quality, watermark",
    "steps": 25,
    "width": 768,
    "height": 512
  }
}
```

### `check_sd_status()`
Kiểm tra trạng thái SDNext và danh sách model đang available.

## Yêu cầu
- SDNext phải đang chạy tại `host.docker.internal:7860`
- Có thể start bằng: `docker-compose --profile art up -d stable-diffusion`
- Hoặc chạy thủ công SDNext tại máy host

## Kết quả trả về
```json
{
  "status": "success",
  "filename": "jkai_art_1234567890.png",
  "path": "/app/outputs/generated/jkai_art_1234567890.png",
  "prompt": "...",
  "dimensions": "768x512",
  "msg": "✅ Đã tạo thành công ảnh..."
}
```
