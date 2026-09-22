import sys
import json
import urllib.request
import base64
import pathlib
import time

sys.stdout.reconfigure(encoding='utf-8')
cfg_path = pathlib.Path.home() / '.config' / 'opencode' / 'service.json'
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
pwd = cfg.get('password', '')
port = cfg.get('port', 49374)
auth = base64.b64encode(f'opencode:{pwd}'.encode()).decode()

session_id = 'ses_f43206275ffeABN08FeBbr2fgw'
last_known_msg_id = 'msg_0c3b3b302001kwUm03Zu4DaSvP'

print(f"[POLL] Đang lắng nghe phản hồi mới hơn '{last_known_msg_id}' (Timeout 60s, chu kỳ 5s)...", flush=True)

for attempt in range(12): # 12 lần * 5s = 60s (Đúng nhịp Nguyên tắc 154)
    req = urllib.request.Request(f'http://127.0.0.1:{port}/api/session/{session_id}/message', headers={'Authorization': f'Basic {auth}'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode('utf-8'))
        items = res.get('data', [])
        last_m = items[-1]
        m_type = last_m.get('type')
        m_id = last_m.get('id')
        m_finish = last_m.get('finish')
        
        # Bỏ qua nếu là message cũ
        if m_id == last_known_msg_id:
            print(f'[{attempt*5}s/60s] Đang chờ message mới từ OpenCode...', flush=True)
        elif m_type == 'user':
            print(f'[{attempt*5}s/60s] Đã nhận user message trigger ({m_id}), OpenCode đang xử lý...', flush=True)
        elif m_type == 'assistant' and m_finish == 'stop':
            print(f'✅ OpenCode đã hoàn thành phản hồi mới (ID: {m_id})!', flush=True)
            full_text = []
            for p in last_m.get('content', []):
                if p.get('type') == 'text':
                    full_text.append(p.get('text', ''))
            reply_text = '\n'.join(full_text)
            print('--- NỘI DUNG PHẢN HỒI (PREVIEW) ---', flush=True)
            print(reply_text[:500], flush=True)
            with open('Thao luan AI/opencode_turn5_raw.md', 'w', encoding='utf-8') as f:
                f.write(reply_text)
            print("Đã lưu vào 'Thao luan AI/opencode_turn5_raw.md'!", flush=True)
            sys.exit(0)
        else:
            print(f'[{attempt*5}s/60s] ID: {m_id} | Type: {m_type} | Finish: {m_finish} (Đang xử lý...)', flush=True)
    except Exception as e:
        print(f'Lỗi kiểm tra ({e})', flush=True)
    time.sleep(5)

print('[TIMEOUT] OpenCode chưa hoàn thành trong 60s.', flush=True)
sys.exit(1)
