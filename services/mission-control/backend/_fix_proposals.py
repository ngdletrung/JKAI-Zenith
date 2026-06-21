"""Script to fix mangled escape quotes in main.py proposals API section."""
import re

filepath = 'main.py'
content = open(filepath, 'r', encoding='utf-8').read()

# Step 1: Fix broken "clarified" return line 
content = content.replace(
    'return jsonify({\\"status\\": \\"clarified\\", \\"task_id\\": task_id})',
    'return jsonify({"status": "clarified", "task_id": task_id})'
)
content = content.replace(
    "return jsonify({\\\"status\\\": \\\"clarified\\\", \\\"task_id\\\": task_id})",
    'return jsonify({"status": "clarified", "task_id": task_id})'
)

# Step 2: Find and replace the broken Plan Board section
marker_start = '# ====================== API: AUTONOMOUS PLAN BOARD ======================'
marker_end = "/api/docker_logs"

s = content.find(marker_start)
# Find the @app.route line for docker_logs
e = content.find(marker_end)
if e != -1:
    # Go back to find the @app.route( before it
    e = content.rfind('@', 0, e)

if s == -1 or e == -1:
    print(f'ERROR: markers not found. start={s}, end={e}')
    exit(1)

print(f'Found section from index {s} to {e}')

before = content[:s]
after = content[e:]

new_section = r"""# ====================== API: AUTONOMOUS PLAN BOARD ======================

@app.route('/api/proposals')
def get_proposals():
    '''Get all pending proposals for Master to review on Plan Tab.'''
    try:
        raw = redis_safe(lambda r: r.lrange('zenith:proposals', 0, 99), [])
        proposals = []
        for item in raw:
            try:
                p = json.loads(item)
                if p.get('status') == 'pending':
                    proposals.append(p)
            except Exception:
                pass
        proposals.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        return jsonify({'proposals': proposals, 'count': len(proposals)})
    except Exception as e:
        return jsonify({'proposals': [], 'error': str(e)})

@app.route('/api/proposals/reject', methods=['POST'])
def reject_proposal():
    '''Master rejects/deletes a proposal - no execution.'''
    data = request.get_json(silent=True) or {}
    proposal_id = data.get('proposal_id')
    if not proposal_id:
        return jsonify({'error': 'Missing proposal_id'}), 400
    try:
        raw = redis_safe(lambda r: r.lrange('zenith:proposals', 0, 99), [])
        updated = []
        removed_title = proposal_id
        for item in raw:
            try:
                p = json.loads(item)
                if p.get('id') != proposal_id:
                    updated.append(item)
                else:
                    removed_title = p.get('title', proposal_id)
            except Exception:
                pass
        redis_safe(lambda r: r.delete('zenith:proposals'))
        for item in updated:
            redis_safe(lambda r: r.rpush('zenith:proposals', item))
        log_msg = 'PLAN BOARD: Master da xoa de xuat ' + str(removed_title)
        redis_safe(lambda r: r.publish('monitor:log_channel', json.dumps({'tag': 'ZENITH', 'msg': log_msg, 'ts': time.time()})))
        socketio.emit('proposal_resolved', {'proposal_id': proposal_id, 'action': 'rejected'})
        return jsonify({'ok': True, 'proposal_id': proposal_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proposals/execute', methods=['POST'])
def execute_proposal():
    '''Master approves proposal - run via Deep Pipeline.'''
    import requests as req
    data = request.get_json(silent=True) or {}
    proposal_id = data.get('proposal_id')
    code = data.get('code', '')
    if not proposal_id:
        return jsonify({'error': 'Missing proposal_id'}), 400
    try:
        raw = redis_safe(lambda r: r.lrange('zenith:proposals', 0, 99), [])
        proposal = None
        updated = []
        for item in raw:
            try:
                p = json.loads(item)
                if p.get('id') == proposal_id:
                    proposal = p
                    p['status'] = 'executing'
                    updated.append(json.dumps(p, ensure_ascii=False))
                else:
                    updated.append(item)
            except Exception:
                pass
        if not proposal:
            return jsonify({'error': 'Proposal not found'}), 404
        if proposal.get('is_red_zone') and not code:
            return jsonify({'error': 'Red zone requires nuclear key', 'need_auth': True}), 403
        redis_safe(lambda r: r.delete('zenith:proposals'))
        for item in updated:
            redis_safe(lambda r: r.rpush('zenith:proposals', item))
        execute_goal = proposal.get('execute_goal') or proposal.get('description', 'Execute proposal')
        title = proposal.get('title', proposal_id)
        log_msg = 'PLAN BOARD: Master phe duyet ' + str(title) + '. Khoi dong Deep Pipeline...'
        redis_safe(lambda r: r.publish('monitor:log_channel', json.dumps({'tag': 'ZENITH', 'msg': log_msg, 'ts': time.time()})))
        task_payload = {
            'goal': execute_goal,
            'mode': 'deep',
            'source': 'plan_board',
            'proposal_id': proposal_id,
            'proposal_type': proposal.get('proposal_type', 'APPROVED'),
            'metadata': proposal.get('metadata', {})
        }
        try:
            r = req.post(AI_CONTROL_PLANE_URL + '/run', json=task_payload, timeout=10)
            if r.status_code == 200:
                result = r.json()
                new_task_id = result.get('task_id', 'unknown')
                socketio.emit('proposal_resolved', {'proposal_id': proposal_id, 'action': 'executing', 'task_id': new_task_id})
                return jsonify({'ok': True, 'task_id': new_task_id, 'proposal_id': proposal_id})
            else:
                return jsonify({'ok': False, 'error': 'Control Plane error: ' + str(r.status_code)}), 500
        except Exception as plane_err:
            log_fb = 'PLAN BOARD: Control Plane offline. De xuat da ghi nhan.'
            redis_safe(lambda r: r.publish('monitor:log_channel', json.dumps({'tag': 'ZENITH', 'msg': log_fb, 'ts': time.time()})))
            socketio.emit('proposal_resolved', {'proposal_id': proposal_id, 'action': 'queued'})
            return jsonify({'ok': True, 'queued': True, 'proposal_id': proposal_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""

new_content = before + new_section + after
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'SUCCESS: Rewrote {filepath}')
print(f'New size: {len(new_content)} chars')
