# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

task_id = sys.argv[1] if len(sys.argv) > 1 else 'TASK-001_attempt_2_1710-1848_a20928'
url = f'http://localhost:9998/api/task_progress/{task_id}'

try:
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        logs = data.get('logs', [])
        print(f'Total logs for {task_id}: {len(logs)}')
        for l in logs[-8:]:
            tag = l.get('tag', '')
            msg = str(l.get('msg', ''))[:120].replace('\n', ' ')
            print(f'  [{tag}] {msg}')
        # Check if terminal
        terminal = any(l.get('tag') in ('DONE', 'RESULT', 'JKAI', 'MISSION_RESULT') for l in logs)
        print(f'Is terminal: {terminal}')
except Exception as e:
    print(f'Error fetching progress: {e}')
