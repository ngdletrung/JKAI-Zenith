import redis
import json
import time

r = redis.Redis(host='redis-ai', port=6379, db=0, decode_responses=True)
p = r.pubsub()
p.subscribe('monitor:log_channel')

print("🛰️ [SNIFFER] Đang bắt sóng kênh log... Nhấn Ctrl+C để dừng.")
try:
    for message in p.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            print(f"[{time.strftime('%H:%M:%S')}] TAG: {data.get('tag')} | MSG: {data.get('msg')[:50]}...")
except KeyboardInterrupt:
    print("\n🛑 Đã dừng bắt sóng.")
