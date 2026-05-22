import time
import json
import os
from core.redis_client import redis_safe

def start_warmup_sequence(socketio):
    import gevent
    print("🎬 [JKAI] Warmup Sequence Starting...")
    gevent.sleep(2)  # Chờ Redis sẵn sàng
    
    # 🧠 Thực sự kiểm tra kho Import!
    import_path = "/intelligence/vault/00_Import"
    has_intel = False
    try:
        if os.path.exists(import_path):
            files = [f for f in os.listdir(import_path) if os.path.isfile(os.path.join(import_path, f))]
            if len(files) > 0:
                has_intel = True
    except: pass

    messages = [
        {"tag": "JKAI", "msg": "⚡ Chào mừng Master LeeTrung quay trở lại Tập đoàn JKAI Zenith! 💎🫡🦾🚀🌌", "ts": time.time()},
    ]

    if has_intel:
        messages.append({"tag": "SYSTEM", "msg": "🔍 Đang quy quét Kho Tri thức... Phát hiện tín hiệu dữ liệu mới trong khu vực Import.", "ts": time.time() + 0.3})
        messages.append({
            "tag": "PROPOSAL", 
            "msg": "Phát hiện các tài liệu chiến sự mới trong thư mục Import. Master có muốn nâng cấp Ma trận Tri thức ngay bây giờ không?", 
            "ts": time.time() + 0.6,
            "action": "import_intel"
        })
    else:
        messages.append({"tag": "SYSTEM", "msg": "✨ Hệ thống ổn định. Ma trận Tri thức đã đạt trạng thái Zenith. Không phát hiện dữ liệu ngoại lai.", "ts": time.time() + 0.3})

    for msg in messages:
        # Sử dụng log_channel để hiển thị trực tiếp trong chat
        payload = json.dumps(msg, ensure_ascii=False)
        redis_safe(lambda r: r.publish("monitor:log_channel", payload))
        # Lưu vào history để không bị mất khi load trang
        redis_safe(lambda r: r.lpush("monitor:log_history", payload))
        gevent.sleep(0.4)
    
    print("✅ [JKAI] Warmup complete.")
