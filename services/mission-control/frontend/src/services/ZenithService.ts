import { CognitiveMode } from '../store/zenithStore';

const API_BASE = '';

export const ZenithService = {
  async submitTask(goal: string, mode: CognitiveMode) {
    try {
      const res = await fetch(`${API_BASE}/api/submit_task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, mode })
      });
      return res.json();
    } catch (e) {
      console.error('Submit task error:', e);
      return { ok: false, error: 'Network failure' };
    }
  },
  async stopAgent() {
    return fetch(`${API_BASE}/api/commander/stop`, { method: 'POST' }).catch(e => console.error('Stop error:', e));
  },
  async sendSystemCmd(cmd: string) {
    return fetch(`${API_BASE}/api/commander/${cmd}`, { method: 'POST' }).catch(e => console.error('Cmd error:', e));
  },
  async readFile(path: string) {
    try {
      const r = await fetch(`${API_BASE}/api/system/read_file?path=${encodeURIComponent(path)}`);
      return r.ok ? r.json() : { ok: false };
    } catch (e) {
      console.error('Read file error:', e);
      return { ok: false };
    }
  },
  async triggerAction(action: string) {
    return fetch(`${API_BASE}/api/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    }).catch(e => console.error('Action error:', e));
  },
  async getStatus() {
    try {
      const r = await fetch(`${API_BASE}/api/system_status`);
      return r.ok ? r.json() : {};
    } catch (e) {
      console.error('Status error:', e);
      return {};
    }
  },
  async saveMission(data: any) {
    return fetch(`${API_BASE}/api/mission/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => r.json()).catch(e => {
      console.error('Save mission error:', e);
      return { ok: false };
    });
  },
  async listMissions() {
    return fetch(`${API_BASE}/api/missions?t=${Date.now()}`, { cache: 'no-store' }).then(r => r.json()).catch(e => {
      console.error('List missions error:', e);
      return [];
    });
  },
  async listDir() {
    try {
      const r = await fetch(`${API_BASE}/api/system/explorer`);
      if (!r.ok) return [];
      const data = await r.json();
      return Array.isArray(data) ? data : (data?.children || []);
    } catch (e) {
      console.error('List dir error:', e);
      return [];
    }
  },
  async getMission(id: string) {
    return fetch(`${API_BASE}/api/mission/${id}?t=${Date.now()}`, { cache: 'no-store' }).then(r => r.json()).catch(e => {
      console.error('Get mission error:', e);
      return { ok: false };
    });
  },
  async getPendingHitl(): Promise<Record<string, any>> {
    try {
      const r = await fetch(`${API_BASE}/api/hitl_pending`);
      return r.ok ? r.json() : {};
    } catch { return {}; }
  },
  async approveHitl(task_id: string, code?: string) {
    try {
      const r = await fetch(`${API_BASE}/api/hitl_approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id, code })
      });
      return r.ok ? r.json() : { ok: false };
    } catch (e) {
      console.error('Approve HITL error:', e);
      return { ok: false };
    }
  },
  async rejectHitl(task_id: string) {
    try {
      const r = await fetch(`${API_BASE}/api/hitl_reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id })
      });
      return r.ok ? r.json() : { ok: false };
    } catch (e) {
      console.error('Reject HITL error:', e);
      return { ok: false };
    }
  },
  async deleteMission(id: string) {
    try {
      const r = await fetch(`${API_BASE}/api/mission/${id}`, { method: 'DELETE' });
      return r.ok ? r.json() : { ok: false };
    } catch (e) {
      console.error('Delete mission error:', e);
      return { ok: false };
    }
  },
  async clearMissions() {
    try {
      const r = await fetch(`${API_BASE}/api/missions`, { method: 'DELETE' });
      return r.ok ? r.json() : { ok: false };
    } catch (e) {
      console.error('Clear missions error:', e);
      return { ok: false };
    }
  },
  streamChat(goal: string, taskId: string, onToken: (t: string) => void, onDone: (full: string) => void, onError?: (e: string) => void): () => void {
    const ctrl = new AbortController();
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ goal, task_id: taskId }),
          signal: ctrl.signal
        });
        if (!res.body) return;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) onToken(data.token);
              if (data.done) { onDone(data.full || ''); return; }
              if (data.error) { onError?.(data.error); return; }
            } catch { }
          }
        }
      } catch (e: any) {
        if (e.name !== 'AbortError') onError?.(e.message);
      }
    })();
    return () => ctrl.abort();
  }
};
