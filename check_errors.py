import os
import json

mission_dir = r'd:\Docker\JKAI\services\mission-control\backend\missions'
files = [f for f in os.listdir(mission_dir) if f.endswith('.json')]
files.sort(key=lambda x: os.path.getmtime(os.path.join(mission_dir, x)), reverse=True)

last_10 = files[:10]
errors = []

for f in last_10:
    path = os.path.join(mission_dir, f)
    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            logs = data.get('logs', [])
            for log in logs:
                tag = log.get('tag', '').upper()
                msg = log.get('msg', '')
                if tag == 'ERROR' or log.get('type') == 'error' or 'error' in msg.lower() or 'exception' in msg.lower():
                    errors.append(f'[{f}] {tag}: {msg[:200]}...')
    except Exception as e:
        errors.append(f'Could not read {f}: {e}')

with open('d:\\Docker\\JKAI\\recent_errors.txt', 'w', encoding='utf-8') as out:
    if errors:
        for e in errors:
            out.write(e + '\n')
    else:
        out.write('No errors found in the last 10 missions.\n')
