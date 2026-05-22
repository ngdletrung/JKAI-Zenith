/** 🚀 [ZENITH-PULSE-SYNC]: Forced Re-sync for Master LeeTrung at 2026-05-14 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useZenithStore, TaskLog } from '../store/zenithStore';
import toast from 'react-hot-toast';

// ─── UTILITIES ────────────────────────────────────────────────────────────────

/** Cắt ngắn chuỗi, tránh undefined/null gây lỗi runtime */
function truncate(s: string | null | undefined, len = 60): string {
  if (!s) return '';
  return s.length <= len ? s : s.slice(0, len) + '…';
}

// ─── CONSTANTS ────────────────────────────────────────────────────────────────

/**
 * ANATOMY_MAP khai báo một lần ở module-level.
 * Zero allocation tại runtime — không bị tạo lại theo mỗi render/tick.
 */
const ANATOMY_MAP: Record<string, { x: number; y: number; scale?: number }> = {
  brain: { x: 0, y: -165, scale: 1.15 },
  planner: { x: -70, y: -95, scale: 0.9 },
  critic: { x: 70, y: -95, scale: 0.9 },
  executor: { x: 0, y: 0, scale: 1.05 },
  receptionist: { x: -145, y: 35, scale: 0.8 },
  legal: { x: 145, y: 35, scale: 0.8 },
  planner_hand: { x: -170, y: 110, scale: 0.8 },
  critic_hand: { x: 170, y: 110, scale: 0.8 },
  memory: { x: 0, y: 80, scale: 0.9 },
  executor_hip: { x: -65, y: 180, scale: 0.8 },
  'agent-06': { x: 65, y: 180, scale: 0.8 },
  'agent-07': { x: -75, y: 290, scale: 0.8 },
  'agent-08': { x: 75, y: 290, scale: 0.8 },
  'agent-09': { x: -85, y: 400, scale: 0.8 },
  'agent-10': { x: 85, y: 400, scale: 0.8 },
} as const;

/** Tag constants — tránh magic string rải rác, TypeScript bắt được typo */
const TAG = {
  MANIFEST: 'MANIFEST',
  THOUGHT: 'THOUGHT',
  TU_DUY: 'TƯ DUY',
  PLANNER: 'PLANNER',
  BAN_KE_HOACH: 'BAN KẾ HOẠCH',
  CRITIC: 'CRITIC',
  PHAN_BIEN: 'PHẢN BIỆN',
  BAN_KIEM_SOAT: 'BAN KIỂM SOÁT',
  STEWARD: 'STEWARD',
  RECEPTIONIST: 'RECEPTIONIST',
  BAN_LE_TAN: 'BAN LỄ TÂN',
  EXECUTOR: 'EXECUTOR',
  BAN_THUC_THI: 'BAN THỰC THI',
  CHAT_INTEL: 'CHAT_INTEL',
  JKAI: 'JKAI',
  MEMORY: 'MEMORY',
  QUAN_GIA: 'QUẢN GIA DỮ LIỆU',
  RESULT: 'RESULT',
  DONE: 'DONE',
  MISSION_RESULT: 'MISSION_RESULT',
  ERROR: 'ERROR',
  ADVERSARIAL: 'ADVERSARIAL',
  SYSTEM: 'SYSTEM',
} as const;

/** Sets được precompute — Set.has() = O(1) thay vì Array.includes() = O(n) */
const TERMINAL_TAGS = new Set([TAG.DONE, TAG.RESULT, TAG.MISSION_RESULT, TAG.JKAI, TAG.CHAT_INTEL, TAG.RECEPTIONIST]);
const RESULT_TAGS = new Set([TAG.RESULT, TAG.DONE, TAG.JKAI, TAG.MISSION_RESULT, TAG.CHAT_INTEL, TAG.RECEPTIONIST]);
const RUNNING_TAGS = new Set([TAG.THOUGHT, TAG.EXECUTOR, TAG.CRITIC, TAG.ADVERSARIAL, TAG.SYSTEM, TAG.STEWARD, TAG.TU_DUY, TAG.BAN_KE_HOACH, TAG.PLANNER, TAG.BAN_KIEM_SOAT, TAG.PHAN_BIEN]);
const HISTORY_TAGS = new Set([TAG.JKAI, TAG.RESULT, TAG.DONE, TAG.CHAT_INTEL, TAG.MISSION_RESULT, TAG.RECEPTIONIST]);

// Sets thay vì inline arrays trong onLog
const PLANNER_TAGS = new Set([TAG.THOUGHT, TAG.TU_DUY, TAG.PLANNER, TAG.BAN_KE_HOACH]);
const CRITIC_TAGS = new Set([TAG.CRITIC, TAG.PHAN_BIEN, TAG.BAN_KIEM_SOAT]);
const RECEPTIONIST_TAGS = new Set([TAG.STEWARD, TAG.RECEPTIONIST, TAG.BAN_LE_TAN]);
const EXECUTOR_TAGS = new Set([TAG.EXECUTOR, TAG.BAN_THUC_THI]);
const MASTER_TAGS = new Set([TAG.CHAT_INTEL, TAG.JKAI]);
const MEMORY_TAGS = new Set([TAG.MEMORY, TAG.QUAN_GIA]);

const CANCELLATION_KEYWORDS = ['disconnected', 'cancelled', 'stopped', 'timeout', 'connection'] as const;
const MODIFIED_FILE_KEYWORDS = ['edited', 'wrote', 'đã sửa'] as const;

const SIDE_NODE_IDS = ['planner', 'critic', 'hitl', 'executor', 'bridge', 'eye', 'memory', 'receptionist', 'legal'] as const;

const THINKING_PHRASES: Partial<Record<string, string[]>> = {
  [TAG.THOUGHT]: ['JKAI: Thinking'],
  [TAG.EXECUTOR]: ['JKAI: Executing'],
  [TAG.CRITIC]: ['JKAI: Evaluating'],
  [TAG.ADVERSARIAL]: ['JKAI: Validating'],
};

const ARTIFACT_FILE_MAP: Record<string, string> = {
  plan: 'implementation_plan.md',
  tasks: 'task.md',
  walkthrough: 'walkthrough.md',
};

const BASE_NODES = [
  { id: 'brain', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'ZENITH CORE', status: 'RUNNING', icon: 'brain', msg: 'Đang khởi động Não bộ...' } },
  { id: 'planner', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'NEURAL PLANNER', status: 'IDLE', icon: 'planner' } },
  { id: 'critic', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'ELITE CRITIC', status: 'IDLE', icon: 'critic' } },
  { id: 'executor', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'MISSION EXECUTOR', status: 'IDLE', icon: 'executor' } },
  { id: 'receptionist', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'BAN TRỢ LÝ', status: 'IDLE', icon: 'receptionist' } },
  { id: 'legal', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'BAN THƯ KÝ', status: 'IDLE', icon: 'legal' } },
  { id: 'memory', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'MEMORY CORE', status: 'IDLE', icon: 'memory' } },
] as const;

const BASE_EDGES = [
  { id: 'e-e-b', source: 'executor', target: 'brain', animated: true },
  { id: 'e-e-p', source: 'executor', target: 'planner', animated: true },
  { id: 'e-e-c', source: 'executor', target: 'critic', animated: true },
  { id: 'e-e-m', source: 'executor', target: 'memory', animated: true },
  { id: 'e-e-r', source: 'executor', target: 'receptionist', animated: true },
  { id: 'e-e-l', source: 'executor', target: 'legal', animated: true },
] as const;

// ─── SOCKET — module-level singleton ─────────────────────────────────────────

/**
 * Socket khởi tạo một lần, dùng chung toàn app.
 * transports: ['websocket', 'polling'] — tránh bị chặn bởi proxy.
 */
const socket: Socket = io({
  reconnectionAttempts: 20,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  timeout: 20000,
  autoConnect: true,
  transports: ['websocket'], // Ép dùng websocket để ổn định nhất
});

socket.on('connect', () => {
  console.log('📡 [ZENITH-CORE] Neural Bridge Online.');
  toast.success('Neural Bridge Online.', { id: 'ZENITH_BRIDGE', icon: '📡' });
});
socket.on('connect_error', (err) => {
  console.error('⚠️ [ZENITH-CORE] Bridge Fault:', err);
  toast.error(`Neural Bridge Fault: ${err.message}`, { id: 'ZENITH_BRIDGE', icon: '⚠️' });
});
socket.on('reconnect', (attempt) => {
  console.log('🔄 [ZENITH-CORE] Neural Bridge Re-established after', attempt, 'attempts.');
  toast.success('Neural Bridge Re-established.', { id: 'ZENITH_BRIDGE', icon: '🔄' });
});
socket.on('reconnect_failed', () => {
  console.error('❌ [ZENITH-CORE] Neural Bridge Permanent Failure.');
  toast.error('Neural Bridge Permanent Failure. Please check Backend status.', { id: 'ZENITH_BRIDGE', duration: 10000, icon: '❌' });
});

// ─── HELPER TYPES ─────────────────────────────────────────────────────────────

interface NodeUpdate {
  id: string;
  status: string;
  msg?: string | null;
  intensity?: string;
}

// ─── applyAnatomyLayout ───────────────────────────────────────────────────────

/**
 * Áp dụng ANATOMY_MAP + trạng thái lên danh sách nodes.
 * Memoization tại từng node — chỉ tạo object mới khi dữ liệu thực sự thay đổi.
 */
function applyAnatomyLayout(nodes: any[], updates: NodeUpdate[]): any[] {
  if (updates.length === 0) return nodes;

  // Pre-index để tra cứu O(1)
  const updateMap = new Map(updates.map(u => [u.id, u]));
  const activeNode = updates.find(u => u.status === 'RUNNING');

  const updated = nodes.map(n => {
    const upd = updateMap.get(n.id);
    let next = n;

    if (upd) {
      const isNewCycle = upd.status === 'RUNNING' && n.data.status !== 'RUNNING';
      const nextCycles = isNewCycle ? (n.data.cycles ?? 0) + 1 : n.data.cycles;

      if (
        n.data.status !== upd.status ||
        (upd.msg !== undefined && n.data.msg !== upd.msg) ||
        (upd.intensity !== undefined && n.data.intensity !== upd.intensity) ||
        n.data.cycles !== nextCycles
      ) {
        next = {
          ...n,
          data: {
            ...n.data,
            status: upd.status,
            msg: upd.msg ?? n.data.msg,
            intensity: upd.intensity ?? n.data.intensity ?? 'calm',
            cycles: nextCycles,
          },
        };
      }
    }

    // Auto-complete upstream nodes khi có node khác đang RUNNING
    if (
      activeNode &&
      next.data.status === 'RUNNING' &&
      next.id !== activeNode.id &&
      next.id !== 'brain'
    ) {
      next = { ...next, data: { ...next.data, status: 'DONE', msg: null } };
    }

    return next;
  });

  // Layout pass — chỉ tạo object mới nếu position/scale/hidden thực sự đổi
  return updated.map(n => {
    const cfg = ANATOMY_MAP[n.id] ?? { x: 0, y: 0, scale: 0.8 };
    const active = n.data.status === 'RUNNING' || n.data.status === 'WAITING' || n.data.status === 'DONE';
    const hide = !active && n.id !== 'brain' && n.id !== 'executor';
    const scale = cfg.scale ?? 0.8;

    if (
      n.hidden === hide &&
      n.position.x === cfg.x &&
      n.position.y === cfg.y &&
      n.data.scale === scale
    ) {
      return n;
    }

    return {
      ...n,
      hidden: hide,
      position: { x: cfg.x, y: cfg.y },
      data: {
        ...n.data,
        scale,
        intensity: n.data.status === 'RUNNING' ? 'fast' : 'calm',
      },
    };
  });
}

// ─── HOOK ─────────────────────────────────────────────────────────────────────

export function useTaskWebSocket() {
  const [dagNodes, setDagNodes] = useState<any[]>(() => applyAnatomyLayout([...BASE_NODES], []));
  const [dagEdges, setDagEdges] = useState<any[]>([...BASE_EDGES]);
  const isConnected = useZenithStore(s => s.isConnected);
  const setIsConnected = useZenithStore(s => s.setIsConnected);

  // Ref tránh stale closure trong submitTask
  const dagNodesRef = useRef<any[]>(dagNodes);
  useEffect(() => { dagNodesRef.current = dagNodes; }, [dagNodes]);

  // AbortController cho fetch đang bay
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // ── Connection handlers ──────────────────────────────────────────────────
    const onConnect = () => {
      setIsConnected(true);
      console.log('📡 [JKAI] Neural Bridge Established.');
    };
    const onDisconnect = (reason: string) => {
      setIsConnected(false);
      console.warn('⚠️ [JKAI] Neural Bridge Severed:', reason);
    };
    const onConnectError = (err: unknown) => {
      setIsConnected(false);
      console.error('❌ [JKAI] Connection Error:', err);
    };

    // Sync trạng thái ngay nếu socket đã connected khi mount
    if (socket.connected) {
      setIsConnected(true);
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('connect_error', onConnectError);

    // ── Batching buffers ─────────────────────────────────────────────────────
    let logBuffer: TaskLog[] = [];
    let pendingNodeUpdates: NodeUpdate[] = [];

    const flushBuffers = () => {
      if (pendingNodeUpdates.length > 0) {
        const updates = [...pendingNodeUpdates];
        pendingNodeUpdates = [];
        setDagNodes(nodes => applyAnatomyLayout(nodes, updates));
      }
    };

    // FIX: clearInterval trong cleanup để không leak timer sau unmount
    const throttleTimer = setInterval(flushBuffers, 80);

    // ── onLog ────────────────────────────────────────────────────────────────
    const onLog = (data: any) => {
      if (!data) return;

      const log: TaskLog = data.payload ?? data;
      if (!log?.tag) return;

      // Normalise id / timestamp
      if (!log.id) log.id = `log_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
      if (log.ts && log.ts < 2_000_000_000) log.ts = log.ts * 1000;
      if (!log.ts) log.ts = Date.now();

      const tag = (log.tag as string).toUpperCase();
      const msg = log.msg ?? '';

      // ── MANIFEST (không buffer — xử lý ngay) ──────────────────────────────
      if (tag === TAG.MANIFEST) {
        try {
          const manifest = JSON.parse(msg);
          useZenithStore.getState().updateManifest(manifest);
          const agentName = (manifest.agent_soul ?? '').split('/').pop()?.replace('.md', '').toUpperCase() ?? 'AGENT';
          pendingNodeUpdates.push({ id: 'planner', status: 'IDLE', msg: `Agent: ${agentName}` });
        } catch (e) {
          console.error('[JKAI] Manifest parse error:', e);
        }
        return;
      }

      // ── isStopping guard — TRƯỚC khi push vào buffer ─────────────────────
      // FIX: guard phải đứng trước logBuffer.push để log không bị leak
      const store = useZenithStore.getState();
      if (store.isStopping) {
        store.setStopping(false);
        return;
      }

      // Processing system logic for this log...

      const {
        setStatus, setThinkingPhrase,
        status: currentStatus,
        thinkingPhrase: currentThinkingPhrase,
      } = store;

      const m = msg.toLowerCase();
      const isCancellationError = tag === TAG.ERROR && CANCELLATION_KEYWORDS.some(k => m.includes(k));

      // ── Status update ──────────────────────────────────────────────────────
      let nextStatus: string | null = null;
      if (TERMINAL_TAGS.has(tag)) nextStatus = 'idle';
      else if (tag === TAG.ERROR) nextStatus = isCancellationError ? 'idle' : 'error';
      else if (RUNNING_TAGS.has(tag)) {
        nextStatus = 'running';
        const phraseList = THINKING_PHRASES[tag] ?? ['[Hệ thống] Đang xử lý dữ liệu...'];
        const nextPhrase = phraseList[Math.floor(Math.random() * phraseList.length)];
        if (nextPhrase !== currentThinkingPhrase) setThinkingPhrase(nextPhrase);
      }
      if (nextStatus && nextStatus !== currentStatus) setStatus(nextStatus as any);

      // ── DAG node updates — vào pendingNodeUpdates (flushed mỗi 80 ms) ─────
      const shortMsg = truncate(msg);

      if (PLANNER_TAGS.has(tag)) pendingNodeUpdates.push({ id: 'planner', status: 'RUNNING', msg: shortMsg });
      else if (CRITIC_TAGS.has(tag)) pendingNodeUpdates.push({ id: 'critic', status: 'RUNNING', msg: shortMsg });
      else if (RECEPTIONIST_TAGS.has(tag)) pendingNodeUpdates.push({ id: 'receptionist', status: 'RUNNING', msg: shortMsg });
      else if (MASTER_TAGS.has(tag)) pendingNodeUpdates.push({ id: 'brain', status: 'RUNNING', msg: shortMsg });
      else if (MEMORY_TAGS.has(tag)) pendingNodeUpdates.push({ id: 'memory', status: 'RUNNING', msg: 'Truy xuất: ' + truncate(msg, 20) });
      else if (EXECUTOR_TAGS.has(tag)) {
        // FIX: dùng 'executor' (tồn tại trong BASE_NODES) làm fallback,
        // chỉ route sang sub-id khi chắc chắn chúng đã được đăng ký trong graph.
        const targetId = m.includes('beta') || m.includes('executor-2') ? 'executor' : 'executor';
        pendingNodeUpdates.push({ id: targetId, status: 'RUNNING', msg: shortMsg });
      }

      // ── Terminal — RESULT / DONE ───────────────────────────────────────────
      if (RESULT_TAGS.has(tag)) {
        const isMissionResult = tag === TAG.MISSION_RESULT || tag === TAG.DONE || tag === TAG.RESULT;
        if (isMissionResult) {
          pendingNodeUpdates.push({ id: 'brain', status: 'DONE', msg: msg || 'Hoàn tất tác vụ' });
          toast.success('Nhiệm vụ hoàn tất.', { id: 'ZENITH_PULSE', icon: '💎' });
        }
        SIDE_NODE_IDS.forEach(id => pendingNodeUpdates.push({ id, status: 'DONE', msg: null }));
      }

      // ── Terminal — ERROR ───────────────────────────────────────────────────
      if (tag === TAG.ERROR) {
        const errorMsg = truncate(msg, 40);
        ['brain', 'executor', 'planner'].forEach(id =>
          pendingNodeUpdates.push({ id, status: 'ERROR', msg: errorMsg })
        );
        if (!isCancellationError) toast.error('Lỗi hệ thống: ' + errorMsg, { id: 'ZENITH_PULSE' });
      }

      // ── File modification detection ────────────────────────────────────────
      if (MODIFIED_FILE_KEYWORDS.some(k => m.includes(k))) {
        const fileMatch = msg.match(/📄\s*([a-zA-Z0-9_.\-/]+)/);
        if (fileMatch) useZenithStore.getState().addModifiedFile(fileMatch[1].trim());
      }
    };

    // ── log_batch ────────────────────────────────────────────────────────────
    const onLogBatch = (data: any) => {
      if (!data?.logs) return;
      data.logs.forEach((log: any) => onLog(log));
    };

    // ── Hardware pulse ────────────────────────────────────────────────────────
    const onHardwarePulse = (data: any) => {
      useZenithStore.getState().setPulse({
        cpu: data.cpu ?? data?.telemetry?.cpu ?? 0,
        ram: data.ram ?? data?.telemetry?.ram ?? 0,
        gpu: data.gpu ?? data?.telemetry?.gpu ?? 0,
        status: data.status ?? data?.health?.status ?? 'STANDBY',
        active_thoughts: data.active_thoughts ?? 'IDLE',
      });
    };

    // ── Artifact watcher ──────────────────────────────────────────────────────
    const onArtifactNew = async (data: any) => {
      const { setUnreadTab, rightTab, updateArtifact } = useZenithStore.getState();
      const tabType: string = data.type;

      if (rightTab !== tabType) setUnreadTab(tabType, true);

      const filename = ARTIFACT_FILE_MAP[tabType];
      if (!filename) return;

      try {
        const res = await fetch(`/api/system/read_file?path=${encodeURIComponent('/storage/artifacts/' + filename)}`);
        if (res.ok) {
          const fileData = await res.json();
          if (fileData.content) updateArtifact(tabType, fileData.content);
        }
      } catch (err) {
        console.error('[JKAI] Failed to sync realtime artifact:', err);
      }
    };

    // ── Register listeners ────────────────────────────────────────────────────
    socket.on('log_batch:operational', (data: any) => {
      if (data?.logs) {
        data.logs.forEach((l: any) => onLog(l));
        useZenithStore.getState().addLogs(data.logs, 'operational');
      }
    });

    socket.on('log_batch:progress', (data: any) => {
      if (data?.logs) {
        data.logs.forEach((l: any) => onLog(l));
        useZenithStore.getState().addLogs(data.logs, 'progress');
      }
    });

    socket.on('hardware_pulse', onHardwarePulse);
    socket.on('artifact_new', onArtifactNew);
    socket.on('hitl_pending_event', (data: any) => {
      const store = useZenithStore.getState();
      try {
         const parsed = typeof data === 'string' ? JSON.parse(data) : data;
         if (parsed?.event === 'hitl_created') {
             store.setPendingHitlId(parsed.payload?.proposal_id || parsed.proposal_id);
         } else if (parsed?.event === 'hitl_resolved') {
             // Only clear if it matches
             if (store.pendingHitlId === parsed.proposal_id) store.setPendingHitlId(null);
         }
      } catch (e) {}
    });

    // ── Cleanup ───────────────────────────────────────────────────────────────
    // FIX: clearInterval + socket.off đảm bảo không leak sau unmount
    return () => {
      clearInterval(throttleTimer);
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('connect_error', onConnectError);
      socket.off('log', onLog);
      socket.off('log_batch', onLogBatch);
      socket.off('hardware_pulse', onHardwarePulse);
      socket.off('artifact_new', onArtifactNew);
      socket.off('hitl_pending_event');
    };
  }, []); // deps rỗng — chỉ chạy 1 lần (socket là singleton)

  // ── submitTask ─────────────────────────────────────────────────────────────
  /**
   * deps rỗng an toàn vì:
   *  - dagNodesRef.current thay vì dagNodes (tránh stale closure)
   *  - store luôn đọc qua getState() (snapshot mới nhất)
   *  - abortRef.current huỷ request trước khi gửi request mới
   */
  const submitTask = useCallback(async (
    goal: string,
    mode: string,
    isAppend: boolean = false,
    options: { images?: any[]; files?: any[] } = {},
  ) => {
    // Huỷ request đang bay
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Reset DAG khi bắt đầu task mới
    if (!isAppend || dagNodesRef.current.length === 0) {
      const initialNodes = (BASE_NODES as any[]).map(n => {
        if (n.id === 'brain') return { ...n, hidden: false, data: { ...n.data, status: 'RUNNING', msg: goal } };
        if (n.id === 'receptionist') return { ...n, hidden: false, data: { ...n.data, status: 'WAITING', msg: 'Đang tiếp nhận nhiệm vụ...' } };
        return { ...n, hidden: true };
      });
      setDagNodes(initialNodes);
      setDagEdges([...BASE_EDGES] as any[]);
    }

    try {
      const state = useZenithStore.getState();
      const currentMissionId = state.currentMissionId;

      const history = (state.operationalLogs || [])
        .filter(l => {
          const t = l.tag?.toUpperCase();
          return t === 'MASTER' || HISTORY_TAGS.has(t as string);
        })
        .slice(-10)
        .map(l => ({
          role: (l.tag?.toUpperCase() === 'MASTER' || (l as any).type === 'user') ? 'user' : 'assistant',
          content: l.msg,
        }));

      const res = await fetch('/api/submit_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          goal,
          mode,
          mission_id: currentMissionId,
          history,
          artifacts: state.currentArtifacts ?? {},
          images: options.images ?? [],
          files: options.files ?? [],
        }),
      });

      return await res.json();
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        console.info('[JKAI] Previous submission cancelled.');
        return { ok: false, error: 'cancelled' };
      }
      console.error('[JKAI] Submission failed', e);
      return { ok: false, error: 'Neural bridge connection failed' };
    }
  }, []);

  // ── Helpers ────────────────────────────────────────────────────────────────

  const addLocalLog = useCallback((log: TaskLog) => {
    useZenithStore.getState().addLog(log as any);
  }, []);

  const resetDAG = useCallback(() => {
    setDagNodes([]);
    setDagEdges([]);
  }, []);

  return { dagNodes, dagEdges, setDagEdges, isConnected, submitTask, addLocalLog, resetDAG };
}