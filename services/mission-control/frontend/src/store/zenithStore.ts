import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export type AgentStatus = 'idle' | 'running' | 'paused' | 'error';
export type CognitiveMode = 'auto' | 'fast' | 'deep';
export type RightTab = 'progress' | 'plan' | 'tasks' | 'walkthrough' | 'explorer' | 'changes' | 'logs' | 'terminal' | 'filelab' | 'connections';
export type StreamView = 'chat' | 'process' | 'full';

export interface Proposal {
  id: string;
  title: string;
  path: string;
  diff: string;
  status: 'pending' | 'applied' | 'rejected';
  ts: number;
}

export interface FileEditEvent {
  path: string;
  diff: string;
  ts: number;
  task_id?: string;
}

export interface BackgroundProposal {
  id: string;
  task_id: string;
  title: string;
  description: string;
  source_module: string;
  proposal_type: 'KNOWLEDGE_DISTILL' | 'SELF_SURGERY' | 'HITL_REALTIME' | string;
  is_red_zone: boolean;
  execute_goal: string;
  metadata: Record<string, any>;
  status: 'pending' | 'executing' | 'done';
  created_at: number;
}

export interface TaskLog {
  id?: string;
  tag: string;
  msg: string;
  ts: number;
  timeStr?: string; // ⏱️ [PRE-FORMATTED-CHRONOS]: Đã tính toán sẵn để tối ưu render
  source?: string; // 🔬 [GRANULAR-SOURCE]: Định danh tệp tin gốc
  type?: string;
  mode?: string;
  task_id?: string;
  is_delta?: boolean;
  duration?: number; // Thinking time or latency in seconds
}

export interface TraceItem {
  id: string;
  type: 'file' | 'folder' | 'search' | 'thought' | 'command';
  label: string;
  detail?: string;
  ts: number;
  duration?: number; // ⏱️ [FIX-FROZEN-TIMER]: Time spent on this task
  status: 'pending' | 'completed';
  logId?: string; // 📡 [LOG-LINK]: ID của log gốc để cuộn đến
}

export interface AgentLog extends TaskLog {
  id: string;
  type?: 'user' | 'ai' | 'sys' | 'tool' | 'CODE';
  action?: string;
  pct?: number;
  is_result?: boolean;
  is_core?: boolean;
}

// ─── LOCALIZATION DICTIONARY ────────────────────────────────────────────────
export const Dictionary = {
  en: {
    exec_graph: 'Zenith Personnel Structure',
    intel_stream: 'Operational Log',
    workspace_title: 'Command Center',
    tab_workspace: 'Elite Capabilities Catalog',
    tab_changes: 'System Structural Mutations',
    tab_intel: 'Mission & Strategy Files',
    full_neural: 'Karpathy Audit',
    active_model: 'Intelligence Core',
    vram: 'Graphics Memory Allocation',
    uplink_stable: 'Uplink: Optimal',
    uplink_lost: 'Uplink: Severed',
    analyze_stream: 'Synthesizing Executive Stream...',
    mod_files: 'Structural\nMutations',
    no_changes: 'Zero Mutations Detected',
    thinking: 'Thinking',
    critic: 'Supreme Control Board',
    awaiting: 'Awaiting Master\'s Executive Decree',
    mission_history: 'Archived Mission Files',
    new_mission: 'Initiate New Mission',
    placeholder: 'Dispatch Decree or Executive Code...',
    processing: 'Executing Corporate Protocol...',
    copied: 'Signature Copied',
    system_online: 'Zenith Systems Online',
    history_btn: 'Archives',
    copy_btn: 'Clone',
    proposal_title: 'Strategic Intervention',
    proposal_intel: 'Intelligence Analysis',
    apply_btn: 'Execute Strategy',
    tab_briefing: 'Plan',
    tab_mission: 'Mission',
    tab_solution: 'Solution',
    tab_vault: 'System',
    tab_surgical: 'Mutations',
    tg_active: 'Telegram Link Active',
    nuclear_ready: 'Supreme Approval Decree: READY',
    nuclear_auth: 'Chairman Authorization Required',
    prop_executed: 'Strategy Executed',
    prop_merged: 'System Updated',
    prop_verified: 'Verified Strategy',
    hitl_title: 'Master\'s Will Approval (Supreme Approval)',
    hitl_desc: 'Zenith Corp requests critical mutation at:',
    hitl_placeholder: "ENTER MASTER KEY TO AUTHORIZE",
    hitl_abort: 'Abort',
    hitl_execute: 'Thực thi',
    dismiss_btn: 'Dismiss',
    file_copy: 'Copy Source',
    official_artifact: 'Official Mission Artifact',
    thinking_msg: 'Processing...',
    tab_progress: 'Progress',
    tab_terminal: 'Terminal',
    cmd_dispatch: 'Dispatch executive command...',
    no_artifact: '# No Documentation Found\nStart a mission to generate Corporate data.',
    artifact_error: '# Error loading documentation',

    // 🧬 Node Labels
    node_brain: 'EXECUTIVE BOARD',
    node_planner: 'STRATEGY DESIGN OFFICE',
    node_critic: 'SUPREME CONTROL BOARD',
    node_executor: 'EXECUTIVE PERSONNEL',
    node_bridge: 'SYSTEM BRIDGE',
    node_eye: 'INTELLIGENCE EYE',
    node_memory: 'CORPORATE KNOWLEDGE VAULT',
    node_agent: 'ELITE PERSONNEL',

    // 🚦 Status Labels
    st_auditing: 'AUDITING',
    PLANNER: 'blue',
    CRITIC: 'indigo',
    DISPATCHER: 'purple',
    EXECUTOR: 'emerald',
    AUDIT: 'amber',
    RISK: 'rose',
    SYSTEM: 'slate',
    st_stable: 'STABLE',
    st_running: 'RUNNING',
    st_waiting: 'WAITING',
    st_error: 'ERROR',
    st_idle: 'AWAITING DECREE',

    // 🍞 Toasts
    t_processing: 'Deploying protocol...',
    t_queued: 'Request queued.',
    t_authorized: 'Authorized by Master.',
    t_complete: 'Mission complete. Strategic report ready for Master.',

    // 🏛 Header
    sub_header: 'JKAI Command Center'
  },
  vi: {
    exec_graph: 'Phòng Họp Điều Hành',
    intel_stream: 'Nhật ký Điều hành',
    workspace_title: 'Trung tâm điều hành',
    tab_workspace: 'Danh mục Kỹ năng Đặc cấp',
    tab_changes: 'Biến động Cấu trúc Hệ thống',
    tab_intel: 'Nhiệm vụ & Chiến lược',
    full_neural: 'Thẩm định Karpathy',
    mod_files: 'Hồ sơ\nBiến động Mã',
    no_changes: 'Hệ thống chưa có biến động',
    thinking: 'Đang Tư duy',
    critic: 'Ban Kiểm soát Tối cao',
    analyze_stream: 'Đang tổng hợp dữ liệu điều hành...',
    awaiting: 'Hệ thống đang túc trực chờ Yêu cầu từ Master.',
    mission_history: 'Lịch sử nhiệm vụ',
    new_mission: 'Khởi tạo nhiệm vụ mới',
    placeholder: 'Master yêu cầu nhiệm vụ nào không ? ...',
    processing: 'Đang thực thi nhiệm vụ...',
    copied: 'Đã sao chép Chữ ký',
    system_online: 'Hệ thống JKAI Zenith đang trực tuyến !',
    active_model: 'Lõi Trí tuệ',
    vram: 'Bộ nhớ Đồ họa',
    uplink_stable: 'Đường truyền: Tối ưu',
    uplink_lost: 'Đường truyền: Bị ngắt',
    history_btn: 'Kho hồ sơ',
    copy_btn: 'Sao chép',
    proposal_title: 'Đề xuất Can thiệp Chiến lược',
    proposal_intel: 'Phân tích Trí tuệ',
    apply_btn: 'Thực thi Chiến lược',
    tab_briefing: 'Kế hoạch',
    tab_mission: 'Nhiệm vụ',
    tab_solution: 'Giải pháp',
    tab_vault: 'Hệ thống',
    tab_surgical: 'Biến động',
    tg_active: 'Liên kết Telegram: Hoạt động',
    nuclear_ready: 'Quyền Phê duyệt Tối cao: SẴN SÀNG',
    nuclear_auth: 'Vui lòng nhập mật khẩu lệnh:',
    prop_executed: 'Chiến lược đã Thực thi',
    prop_merged: 'Thay đổi đã được cập nhật',
    prop_verified: 'Chiến lược đã Thẩm định',
    hitl_title: 'Phê duyệt Yêu cầu từ Master (Quyền Phê duyệt Tối cao)',
    hitl_desc: 'Tập đoàn đang yêu cầu thay đổi quan trọng tại:',
    hitl_placeholder: "Nhập mật khẩu lệnh để xác nhận",
    hitl_abort: 'Hủy bỏ',
    hitl_execute: 'Thực thi',
    dismiss_btn: 'Bỏ qua',
    file_copy: 'Sao chép Mã',
    official_artifact: 'Hồ sơ nhiệm vụ chính thức',
    thinking_msg: 'Đang xử lý',
    tab_progress: 'Tiến trình',
    tab_terminal: 'Cửa sổ Lệnh',
    cmd_dispatch: 'Nhập mật khẩu lệnh điều hành...',
    no_artifact: '# Không tìm thấy Hồ sơ\nKhởi tạo nhiệm vụ để tạo dữ liệu Tập đoàn.',
    artifact_error: '# Lỗi khi tải hồ sơ',
    node_brain: 'BAN ĐIỀU HÀNH',
    node_planner: 'BAN KẾ HOẠCH',
    node_critic: 'BAN KIỂM SOÁT',
    node_executor: 'BAN THỰC THI',
    node_bridge: 'CẦU NỐI HỆ THỐNG',
    node_eye: 'MẮT THẦN TRÍ TUỆ',
    node_memory: 'QUẢN GIA DỮ LIỆU',
    node_agent: 'NHÂN SỰ ƯU TÚ',
    st_auditing: 'ĐANG THẨM ĐỊNH',
    st_stable: 'ỔN ĐỊNH',
    st_running: 'ĐANG CHẠY',
    st_waiting: 'ĐANG CHỜ',
    st_error: 'SỰ CỐ',
    st_idle: 'CHỜ YÊU CẦU',
    t_processing: 'Đang triển khai giao thức...',
    t_queued: 'Yêu cầu đã được xếp hàng.',
    t_authorized: 'Đã được Master phê duyệt.',
    t_complete: 'Nhiệm vụ hoàn tất. Báo cáo đã sẵn sàng trình Master.',
    sub_header: 'Trung tâm Điều hành Lõi JKAI',
    sys_log: 'BAN KỸ THUẬT TẬP ĐOÀN',
    security_log: 'BỘ PHẬN AN NINH'
  }
};

export interface ZenithState {
  goal: string;
  status: AgentStatus;
  isBooting: boolean;
  isPaused: boolean;
  cognitiveMode: CognitiveMode;
  attachedFiles: File[];
  operationalLogs: AgentLog[];
  progressLogs: AgentLog[];
  rightTab: RightTab;
  inspectedFile: { path: string; content: string; connId?: string } | null;
  thinkingPhrase: string;
  showReasoning: boolean;
  streamView: StreamView;
  debateCount: number;

  currentMissionId: string | null;
  sessionId: string;
  history: any[];
  modifiedFiles: string[];
  fileEdits: FileEditEvent[];
  language: 'en' | 'vi';
  missionGoal: string;
  inputHistory: string[];
  inputHistoryIndex: number;

  // 🧭 NEURAL DISPATCH SYNC
  activeSkills: string[];
  isStopping: boolean;
  isTelegramConnected: boolean;
  showArsenal: boolean;
  currentArtifacts: Record<string, string>;

  // ☢️ NUCLEAR AUTH PROTOCOL
  pendingMutation: { id: string; type: string; details: any } | null;
  pendingHitlId: string | null;
  confirmedMutations: string[];

  // 🔬 SURGICAL PRECISION PROTOCOL
  pendingProposals: Proposal[];
  backgroundProposals: BackgroundProposal[];
  unreadTabs: Record<string, number>;
  pulse: { cpu: number; ram: number; gpu: number; status: string; active_thoughts: string };
  isConnected: boolean;

  // 🧭 EXECUTION TRACE PROTOCOL
  executionTrace: {
    items: TraceItem[];
    isExpanded: boolean;
    lastUpdate: number;
    startTime?: number; // ⏱️ [MISSION-CHRONOS]: Thời điểm bắt đầu nhiệm vụ
  };
  setTraceExpanded: (val: boolean) => void;
  clearTrace: () => void;

  setGoal: (goal: string) => void;
  setLanguage: (lang: 'en' | 'vi') => void;
  setStatus: (status: AgentStatus) => void;
  setStopping: (val: boolean) => void;
  setBooting: (val: boolean) => void;
  setPaused: (v: boolean) => void;
  setMode: (mode: CognitiveMode) => void;
  setFiles: (files: File[]) => void;
  addLog: (log: AgentLog, target?: 'operational' | 'progress') => void;
  addLogs: (logs: AgentLog[], target?: 'operational' | 'progress') => void;
  setTab: (tab: RightTab) => void;
  setInspectedFile: (file: { path: string; content: string; connId?: string } | null) => void;
  addModifiedFile: (path: string) => void;
  registerFileEdit: (edit: FileEditEvent, openPreview?: boolean) => void;
  setThinkingPhrase: (phrase: string) => void;
  toggleReasoning: () => void;
  setStreamView: (view: StreamView) => void;
  incrementDebate: () => void;
  resetDebate: () => void;
  reset: () => void;
  setTelegramConnected: (val: boolean) => void;
  setShowArsenal: (val: boolean) => void;
  setIsConnected: (val: boolean) => void;

  // ☢️ NUCLEAR ACTIONS
  setPendingMutation: (mutation: { id: string; type: string; details: any } | null) => void;
  setPendingHitlId: (id: string | null) => void;
  confirmMutation: (id: string) => void;

  // 🔬 SURGICAL ACTIONS
  addProposal: (proposal: Proposal) => void;
  applyProposal: (id: string) => void;
  removeProposal: (id: string) => void;
  setMissionGoal: (goal: string) => void;
  addToInputHistory: (goal: string) => void;
  setInputHistoryIndex: (idx: number) => void;
  socketActions: { submitTask: any; resetDAG: any } | null;
  updateArtifact: (key: string, content: string) => void;
  updateManifest: (manifest: any) => void;
  setUnreadTab: (tab: string, val: number) => void;
  incrementUnreadTab: (tab: string) => void;
  
  setBackgroundProposals: (proposals: BackgroundProposal[]) => void;
  addBackgroundProposal: (proposal: BackgroundProposal) => void;
  removeBackgroundProposal: (id: string) => void;
  updateProposalStatus: (id: string, status: 'pending' | 'executing' | 'done') => void;
  setPulse: (pulse: any) => void;
  setMissionId: (currentMissionId: string | null) => void;
  setSessionId: (sessionId: string) => void;
  setHistory: (history: any[]) => void;
  setSocketActions: (socketActions: { submitTask: any; resetDAG: any } | null) => void;
  loadMissionData: (data: any) => Promise<void>;
}

export const useZenithStore = create<ZenithState>()(
  devtools(
    persist(
      (set, get) => ({
        goal: '',
        status: 'idle',
        isBooting: typeof window !== 'undefined' ? !sessionStorage.getItem('zenith_booted') : true,
        isPaused: false,
        cognitiveMode: 'fast',
        attachedFiles: [],
        operationalLogs: [{
          id: 'zenith_welcome_msg',
          tag: 'JKAI',
          msg: '⚡Chào mừng Master LeeTrung quay trở lại JKAI ZENITH ! 💎🫡🦾🚀🌌',
          ts: Date.now()
        }],
        progressLogs: [],
        rightTab: 'progress',
        inspectedFile: null,
        thinkingPhrase: '',
        showReasoning: false,
        streamView: 'chat',
        debateCount: 0,
        currentMissionId: null,
        sessionId: typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        history: [],
        modifiedFiles: [],
        fileEdits: [],
        language: 'vi', // Default to Vietnamese for Master
        isStopping: false,
        activeSkills: [],
        isTelegramConnected: false,
        showArsenal: false,
        currentArtifacts: {},
        pendingMutation: null,
        pendingHitlId: null,
        confirmedMutations: [],
        pendingProposals: [],
        missionGoal: '',
        inputHistory: (() => {
          try {
            const saved = localStorage.getItem('zenith_input_history_backup');
            return saved ? JSON.parse(saved) : [];
          } catch (e) {
            return [];
          }
        })(),
        inputHistoryIndex: -1,
        unreadTabs: {},
        backgroundProposals: [],
        pulse: { cpu: 0, ram: 0, gpu: 0, status: 'STANDBY', active_thoughts: 'IDLE' },
        isConnected: false,
        executionTrace: {
          items: [],
          isExpanded: true,
          lastUpdate: Date.now(),
          startTime: Date.now()
        },

        setTraceExpanded: (isExpanded) => set(s => ({
          ...s,
          executionTrace: { ...s.executionTrace, isExpanded }
        })),
        clearTrace: () => set(s => ({
          ...s,
          executionTrace: { items: [], isExpanded: true, lastUpdate: Date.now(), startTime: Date.now() }
        })),

        setGoal: (goal) => set(s => ({ ...s, goal })),
        addToInputHistory: (goal) => set(s => {
          if (!goal || s.inputHistory[s.inputHistory.length - 1] === goal) return s;
          const nextHistory = [...s.inputHistory, goal].slice(-50);
          try {
            localStorage.setItem('zenith_input_history_backup', JSON.stringify(nextHistory));
          } catch (e) { }
          return { ...s, inputHistory: nextHistory, inputHistoryIndex: -1 };
        }),
        setInputHistoryIndex: (inputHistoryIndex) => set(s => ({ ...s, inputHistoryIndex })),
        setMissionGoal: (missionGoal) => set(s => ({ ...s, missionGoal })),
        setLanguage: (language) => set(s => ({ ...s, language })),
        setStatus: (status) => set(s => {
          let updatedTraceItems = s.executionTrace.items;
          if (status !== 'running' && updatedTraceItems.length > 0) {
            const lastIdx = updatedTraceItems.length - 1;
            if (updatedTraceItems[lastIdx].type === 'thought' && !updatedTraceItems[lastIdx].duration) {
              updatedTraceItems = [...updatedTraceItems];
              updatedTraceItems[lastIdx] = {
                ...updatedTraceItems[lastIdx],
                duration: Math.max(1, Math.floor((Date.now() - updatedTraceItems[lastIdx].ts) / 1000))
              };
            }
          }
          return { 
            ...s, 
            status,
            executionTrace: { ...s.executionTrace, items: updatedTraceItems }
          };
        }),
        setStopping: (isStopping) => set(s => ({ ...s, isStopping })),
        setBooting: (isBooting) => set(s => ({ ...s, isBooting })),
        setPaused: (isPaused) => set(s => ({ ...s, isPaused })),
        setMode: (cognitiveMode) => set(s => ({ ...s, cognitiveMode })),
        setFiles: (attachedFiles) => set(s => ({ ...s, attachedFiles })),
        addLog: (log, target = 'operational') => set((s) => {
          if (!log.msg || log.msg.trim() === '') return s;

          // 🕒 [CHRONOS-NORMALIZE]: Chuẩn hóa ts về ms — bất kể backend (seconds) hay frontend (ms)
          const rawTs = log.ts || Date.now();
          const normalizedTs = rawTs < 1e10 ? rawTs * 1000 : rawTs;
          log.ts = normalizedTs;
          const now = new Date(normalizedTs);
          const ms = String(now.getMilliseconds()).padStart(3, '0');
          log.timeStr = `${now.toLocaleTimeString('en-GB', { hour12: false })}.${ms}`;

          if (!log.id) {
            const tag = log.tag?.toUpperCase() || 'SYS';
            const msg = log.msg || '';
            // 🛡️ [DETERMINISTIC-STREAM-ID]: For streaming logs (THOUGHT/PROGRESS), use a stable ID to prevent re-mounting/flashing
            if (['THOUGHT', 'PROGRESS', 'PLANNER', 'TƯ DUY', 'BAN KẾ HOẠCH'].includes(tag) && log.task_id) {
              log.id = `stream_${tag}_${log.task_id}`;
            } else {
              log.id = `hash_${tag}_${msg.length}_${msg.slice(0, 20)}_${normalizedTs}`;
            }
          }

          let traceItem: TraceItem | null = null;
          const tag = log.tag?.toUpperCase() || 'SYS';
          const msg = log.msg || '';

          if (tag === 'SEARCH_RESULT' || msg.includes('Found')) {
            const countMatch = msg.match(/Found (\d+) results/i);
            const count = countMatch ? countMatch[1] : '';
            const lastTrace = s.executionTrace.items.slice().reverse().find(i => i.type === 'search');
            if (lastTrace) {
              // Update last search item's detail with result count
              traceItem = null; // Don't create new, update existing via detail below
            }
          } else if (
            tag.includes('THOUGHT') || tag.includes('TƯ DUY') || 
            tag.includes('PLANNER') || tag.includes('RECEPTIONIST') || 
            tag.includes('ZENITH') || tag.includes('SYSTEM') ||
            tag.includes('MINI_PLANNER') || tag.includes('BAN KẾ HOẠCH') || 
            tag.includes('BAN THƯ KÝ') || tag.includes('BAN TRỢ LÝ')
          ) {
            let cleanMsg = msg
              .replace(/\[Task:\s*[^\]]+\]/gi, '')
              .replace(/\[ROUTING\]:/gi, '')
              .replace(/\[NEURAL-SYNC\]:/gi, '')
              .trim();
            if (cleanMsg && cleanMsg.length > 2) {
              traceItem = {
                id: `tr-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
                type: 'thought',
                label: cleanMsg.length > 90 ? cleanMsg.slice(0, 90) + '...' : cleanMsg,
                detail: msg,
                ts: Date.now(),
                status: 'completed'
              };
            }
          }


          let newTrace = s.executionTrace;
          if (traceItem) {
            const currentItems = [...s.executionTrace.items];
            const lastIdx = currentItems.length - 1;
            // ⏱️ [FIX-FROZEN-TIMER]: Khi thêm 1 trace mới, chốt thời gian cho thought trước đó
            if (lastIdx >= 0 && currentItems[lastIdx].type === 'thought' && !currentItems[lastIdx].duration) {
              currentItems[lastIdx] = { 
                ...currentItems[lastIdx], 
                duration: Math.max(1, Math.floor((Date.now() - currentItems[lastIdx].ts) / 1000)) 
              };
            }
            newTrace = {
              ...s.executionTrace,
              items: [...currentItems, traceItem].slice(-200),
              lastUpdate: Date.now(),
              isExpanded: true
            };
          }

          // Log filtering and routing is suspended per Master's request.
          // Both streams (operationalLogs and progressLogs) are kept 100% synchronized and identical thưa Master.
          const updatedOps = [...s.operationalLogs];
          const updatedProg = [...s.progressLogs];

          // Stealth Wipe Protocol
          if ((log as any).stealth && (tag === 'AUTH' || tag === 'AUTHENTICATION')) {
            for (let i = updatedOps.length - 1; i >= 0; i--) {
              if (updatedOps[i].type === 'user') {
                updatedOps[i] = { ...updatedOps[i], msg: "🔐 [GIAO THỨC BẢO MẬT ĐÃ KÍCH HOẠT - DẤU VẾT ĐÃ ĐƯỢC THANH TẨY]" };
                break;
              }
            }
            for (let i = updatedProg.length - 1; i >= 0; i--) {
              if (updatedProg[i].type === 'user') {
                updatedProg[i] = { ...updatedProg[i], msg: "🔐 [GIAO THỨC BẢO MẬT ĐÃ KÍCH HOẠT - DẤU VẾT ĐÃ ĐƯỢC THANH TẨY]" };
                break;
              }
            }
          }

          const opIdx = updatedOps.findIndex(el => el.id === log.id);
          const progIdx = updatedProg.findIndex(el => el.id === log.id);
          const existsInOps = opIdx !== -1;
          const existsInProg = progIdx !== -1;

          if (existsInOps || existsInProg) {
            if (existsInOps) {
              const existingLog = updatedOps[opIdx];
              const isNewer = (log.ts || 0) > (existingLog.ts || 0);
              const isSameButFullFlush = (log.ts || 0) === (existingLog.ts || 0) && !log.is_delta;
              if (isNewer || isSameButFullFlush) {
                const existingMsg = existingLog.msg;
                const newMsg = log.is_delta ? (existingMsg + log.msg) : log.msg;
                updatedOps[opIdx] = { ...existingLog, msg: newMsg, ts: log.ts };
              }
            } else {
              updatedOps.push(log);
            }

            if (existsInProg) {
              const existingLog = updatedProg[progIdx];
              const isNewer = (log.ts || 0) > (existingLog.ts || 0);
              const isSameButFullFlush = (log.ts || 0) === (existingLog.ts || 0) && !log.is_delta;
              if (isNewer || isSameButFullFlush) {
                const existingMsg = existingLog.msg;
                const newMsg = log.is_delta ? (existingMsg + log.msg) : log.msg;
                updatedProg[progIdx] = { ...existingLog, msg: newMsg, ts: log.ts };
              }
            } else {
              updatedProg.push(log);
            }

            return {
              ...s,
              operationalLogs: updatedOps.slice(-200),
              progressLogs: updatedProg.slice(-2000),
              executionTrace: newTrace
            };
          }

          // Progress in Place Protocol
          if (tag === 'PROGRESS' && updatedProg.length > 0) {
            const lastLogProg = updatedProg[updatedProg.length - 1];
            if (lastLogProg.tag === 'PROGRESS' && lastLogProg.task_id === log.task_id) {
              updatedProg[updatedProg.length - 1] = { ...lastLogProg, ...log };
              
              if (updatedOps.length > 0) {
                const lastLogOps = updatedOps[updatedOps.length - 1];
                if (lastLogOps.tag === 'PROGRESS' && lastLogOps.task_id === log.task_id) {
                  updatedOps[updatedOps.length - 1] = { ...lastLogOps, ...log };
                }
              }

              return {
                ...s,
                operationalLogs: updatedOps.slice(-200),
                progressLogs: updatedProg.slice(-2000),
                executionTrace: newTrace
              };
            }
          }

          updatedOps.push(log);
          updatedProg.push(log);

          return {
            ...s,
            operationalLogs: updatedOps.slice(-200),
            progressLogs: updatedProg.slice(-2000),
            executionTrace: newTrace
          };
        }),
        addLogs: (newLogsBatch, target = 'operational') => set((s) => {
          const processedBatch = newLogsBatch.map(nl => {
            const msg = nl.msg || '';
            const tag = nl.tag || 'SYS';
            // 🕒 [CHRONOS-NORMALIZE]: Đồng bộ đơn vị ts
            const rawTs = nl.ts || Date.now();
            const normalizedTs = rawTs < 1e10 ? rawTs * 1000 : rawTs;
            const timeStr = new Date(normalizedTs).toLocaleTimeString();
            
            let contentId = nl.id;
            if (!contentId) {
              const tag = (nl.tag || 'SYS').toUpperCase();
              if (['THOUGHT', 'PROGRESS', 'PLANNER', 'TƯ DUY', 'BAN KẾ HOẠCH'].includes(tag) && nl.task_id) {
                contentId = `stream_${tag}_${nl.task_id}`;
              } else {
                contentId = `hash_${tag}_${msg.length}_${msg.slice(0, 20)}_${normalizedTs}`;
              }
            }

            return {
              ...nl,
              ts: normalizedTs,
              timeStr,
              id: contentId
            };
          }).filter(nl => nl.msg && nl.msg.trim() !== '');

          if (processedBatch.length === 0) return s;

          // 🏛️ [LEGACY-TECH-TAGS]: Dùng cho fallback routing khi không có channels
          const technicalTags = ['DEBUG', 'THOUGHT', 'PLANNER', 'DISPATCHER', 'RECEPTIONIST', 'TRACE', 'LATENCY', 'FORGE_V3', 'STEWARD', 'PROGRESS', 'HEARTBEAT'];

          let updatedOps = [...s.operationalLogs];
          let updatedProg = [...s.progressLogs];
          let newTraceItems = [...s.executionTrace.items];

          for (const nl of processedBatch) {
            const tag = nl.tag.toUpperCase();
            const msg = nl.msg || '';

            // 📌 [PIN-UPDATE-PROTOCOL]: Cập nhật stream đang chạy (THOUGHT/PROGRESS/HEARTBEAT)
            // Dù routing theo kênh nào, nếu log đã tồn tại thì update in-place để stream mượt
            const opIdx   = updatedOps.findIndex(el => el.id === nl.id);
            const progIdx = updatedProg.findIndex(el => el.id === nl.id);
            const existsInOps  = opIdx !== -1;
            const existsInProg = progIdx !== -1;

            if (existsInOps || existsInProg) {
              // Streamable: cập nhật nội dung mà không tạo log mới
              if (existsInOps) {
                const existingLog = updatedOps[opIdx];
                const isNewer = (nl.ts || 0) > (existingLog.ts || 0);
                const isSameButFullFlush = (nl.ts || 0) === (existingLog.ts || 0) && !nl.is_delta;
                if (isNewer || isSameButFullFlush) {
                  const existingMsg = existingLog.msg;
                  const newMsg = nl.is_delta ? (existingMsg + nl.msg) : nl.msg;
                  updatedOps[opIdx] = { ...existingLog, msg: newMsg, ts: nl.ts };
                }
              } else {
                updatedOps.push(nl);
              }

              if (existsInProg) {
                const existingLog = updatedProg[progIdx];
                const isNewer = (nl.ts || 0) > (existingLog.ts || 0);
                const isSameButFullFlush = (nl.ts || 0) === (existingLog.ts || 0) && !nl.is_delta;
                if (isNewer || isSameButFullFlush) {
                  const existingMsg = existingLog.msg;
                  const newMsg = nl.is_delta ? (existingMsg + nl.msg) : nl.msg;
                  updatedProg[progIdx] = { ...existingLog, msg: newMsg, ts: nl.ts };
                }
              } else {
                updatedProg.push(nl);
              }
              continue;
            }

            // 🔍 [EXECUTION-TRACE]: Trích xuất dấu vết thực thi cho ExecutionTrace widget
            let traceItem: TraceItem | null = null;
            if (tag.includes('EXECUTOR') || tag.includes('THỰC THI')) {
              if (msg.includes('`')) {
                const match = msg.match(/`([^`]+)`/);
                if (match) {
                  const label = match[1];
                  traceItem = {
                    id: `tr-${Date.now()}-${Math.random()}`,
                    type: label.includes('.') && !label.includes('/') ? 'file' : (label.includes('/') || label.includes('\\') ? 'folder' : 'file'),
                    label,
                    ts: nl.ts || Date.now(),
                    status: 'completed',
                    logId: nl.id
                  };
                  if (msg.includes('Edited') || msg.includes('Wrote') || msg.includes('Patch')) {
                    s.addModifiedFile(label);
                  }
                }
              } else if (msg.includes('Ran command') || msg.includes('Executing')) {
                const match = msg.match(/`([^`]+)`/);
                if (match) {
                  traceItem = {
                    id: `tr-${Date.now()}-${Math.random()}`,
                    type: 'command',
                    label: match[1],
                    ts: nl.ts || Date.now(),
                    status: 'completed',
                    logId: nl.id
                  };
                }
              }
            } else if (tag.includes('SEARCH') || tag.includes('TRUY TÌM') || tag.includes('TRUY_TIM')) {
              const match = msg.match(/`([^`]+)`/) || msg.match(/searching (.*)/i);
              if (match) {
                traceItem = {
                  id: `tr-${Date.now()}-${Math.random()}`,
                  type: 'search',
                  label: match[1],
                  ts: nl.ts || Date.now(),
                  status: 'completed',
                  logId: nl.id
                };
              }
            } else if (msg.includes('TAVILY') && (msg.includes('search') || msg.includes('Initiating'))) {
              const tavilyMatch = msg.match(/TAVILY[^:]*:\s*Initiating[^"'`]*for\s+(.+)/i) || msg.match(/TAVILY[^:]*:\s*(.+)/i);
              const label = tavilyMatch ? tavilyMatch[1].slice(0, 80) : msg.slice(0, 80);
              traceItem = {
                id: `tr-${Date.now()}-${Math.random()}`,
                type: 'search',
                label: `TAVILY: Initiating global web search for "${label}"`,
                ts: nl.ts || Date.now(),
                status: 'completed',
                logId: nl.id
              };
            } else if (tag.includes('THOUGHT') || tag.includes('PLANNER') || tag.includes('TƯ DUY')) {
              traceItem = {
                id: `tr-${Date.now()}-${Math.random()}`,
                type: 'thought',
                label: s.language === 'vi' ? 'Hệ thống đang tư duy' : 'System Reasoning',
                detail: msg,
                ts: nl.ts || Date.now(),
                status: 'completed',
                logId: nl.id
              };
            }

            if (traceItem) {
              if (!newTraceItems.some(ti => ti.logId === nl.id)) {
                // ⏱️ [FIX-FROZEN-TIMER]: Chốt thời gian cho trace thought trước đó nếu chưa có
                const lastIdx = newTraceItems.length - 1;
                if (lastIdx >= 0 && newTraceItems[lastIdx].type === 'thought' && !newTraceItems[lastIdx].duration) {
                  newTraceItems[lastIdx].duration = Math.max(1, Math.floor((Date.now() - newTraceItems[lastIdx].ts) / 1000));
                }
                newTraceItems.push(traceItem);
              } else if (traceItem.type === 'thought') {
                const existingIdx = newTraceItems.findIndex(ti => ti.logId === nl.id);
                if (existingIdx !== -1) {
                  newTraceItems[existingIdx] = { ...newTraceItems[existingIdx], detail: msg, ts: nl.ts || Date.now() };
                }
              }
            }

            // Master requested to temporarily remove all routing and filtering for testing:
            updatedOps.push(nl);
            updatedProg.push(nl);
          }


          return {
            ...s,
            operationalLogs: updatedOps.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-200),
            progressLogs: updatedProg.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-2000),
            executionTrace: { ...s.executionTrace, items: newTraceItems.slice(-200), lastUpdate: Date.now(), isExpanded: true }
          };
        }),
        setTab: (rightTab) => set(s => ({ ...s, rightTab })),
        setInspectedFile: (inspectedFile) => set(s => ({ ...s, inspectedFile })),
        addModifiedFile: (path) => set(s => ({
          ...s,
          modifiedFiles: Array.from(new Set([...s.modifiedFiles, path]))
        })),
        registerFileEdit: (edit, openPreview = true) => set(s => ({
          ...s,
          fileEdits: [edit, ...s.fileEdits].slice(0, 40),
          modifiedFiles: Array.from(new Set([...s.modifiedFiles, edit.path])),
          rightTab: openPreview ? 'changes' : s.rightTab,
        })),
        setThinkingPhrase: (thinkingPhrase) => set(s => ({ ...s, thinkingPhrase })),
        toggleReasoning: () => set((s) => ({ ...s, showReasoning: !s.showReasoning })),
        setStreamView: (view) => set(s => ({ ...s, streamView: view })),
        incrementDebate: () => set((s) => ({ ...s, debateCount: s.debateCount + 1 })),
        resetDebate: () => set(s => ({ ...s, debateCount: 0 })),
        setTelegramConnected: (isTelegramConnected) => set(s => ({ ...s, isTelegramConnected })),
        setShowArsenal: (showArsenal) => set(s => ({ ...s, showArsenal })),
        setIsConnected: (isConnected) => set(s => ({ ...s, isConnected })),
        setPendingHitlId: (pendingHitlId) => set(s => ({ ...s, pendingHitlId })),
        setPendingMutation: (mutation) => set(s => ({ ...s, pendingMutation: mutation })),
        confirmMutation: (id) => set(s => ({
          ...s,
          confirmedMutations: [...s.confirmedMutations, id],
          pendingMutation: null
        })),
        addProposal: (proposal) => set(s => ({
          ...s,
          pendingProposals: [...s.pendingProposals, proposal]
        })),
        applyProposal: (id) => set(s => ({
          ...s,
          pendingProposals: s.pendingProposals.map(p => p.id === id ? { ...p, status: 'applied' } : p)
        })),
        removeProposal: (id) => set(s => ({
          ...s,
          pendingProposals: s.pendingProposals.filter(p => p.id !== id)
        })),
        reset: () => set(s => ({
          ...s,
          goal: '',
          attachedFiles: [],
          status: 'idle',
          debateCount: 0,
          operationalLogs: [{
            id: 'zenith_welcome_msg',
            tag: 'JKAI',
            msg: '⚡Chào mừng Master LeeTrung quay trở lại JKAI ZENITH ! 💎🫡🦾🚀🌌',
            ts: Date.now()
          }],
          progressLogs: [],
          modifiedFiles: [],
        fileEdits: [],
          currentMissionId: null,
          activeAgent: null,
          activeSkills: [],
          missionGoal: ''
        })),
        setMissionId: (currentMissionId: string | null) => set(s => ({ ...s, currentMissionId })),
        setSessionId: (sessionId: string) => set(s => ({ ...s, sessionId })),
        setHistory: (history: any[]) => set(s => ({ ...s, history })),
        loadMissionData: async (data: any) => {
          // 🛡️ [DUAL-STREAM-SYNC]: Bi-directional stream synchronization
          const [opsResp, progResp] = await Promise.all([
            fetch('/api/docker_logs'),
            fetch('/api/progress_logs')
          ]);
          const [opsData, progData] = await Promise.all([
            opsResp.json(),
            progResp.json()
          ]);

          const rawHistoryLogs = Array.isArray(data.logs) ? data.logs : [];
          // ⏳ [TIMESTAMP-NORMALIZATION]: Chuẩn hóa giây sang mili-giây giống như socket thưa Master
          const historyLogs = rawHistoryLogs.map((log: any) => {
            const newLog = { ...log };
            if (newLog.ts && newLog.ts < 2_000_000_000) {
              newLog.ts = newLog.ts * 1000;
            }
            return newLog;
          });

          const serverOpsLogs = Array.isArray(opsData.logs) ? opsData.logs : [];
          const serverProgLogs = Array.isArray(progData.logs) ? progData.logs : [];

          const isCompleted = data.status === 'completed';
          let mergedOps: any[] = [];
          let mergedProg: any[] = [];

          if (isCompleted) {
            // 🛡️ [HISTORY-ISOLATION-GUARD]: Nếu sứ mệnh đã xong, giữ nguyên log thật lịch sử, loại bỏ rác hệ thống hiện thời thưa Master
            mergedOps = [...historyLogs];
            mergedProg = [...historyLogs];
          } else {
            // 🏛️ [OPS-MERGE]: Operational log consolidation
            mergedOps = [...historyLogs];
            serverOpsLogs.forEach((sl: any) => {
              let logObj = sl;
              if (typeof sl === 'string') {
                const match = sl.match(/\[(.*?)\] \[(.*?)\] (.*)/);
                if (match) {
                  logObj = { ts: Date.now(), tag: match[2], msg: match[3], timeStr: match[1] };
                } else {
                  logObj = { ts: Date.now(), tag: 'SYS', msg: sl };
                }
              }
              if (logObj.ts && logObj.ts < 2_000_000_000) logObj.ts = logObj.ts * 1000;
              if (!mergedOps.some(ml => ml.msg === logObj.msg && (ml.timeStr === logObj.timeStr || ml.ts === logObj.ts))) {
                mergedOps.push(logObj);
              }
            });

            // 🔬 [PROG-MERGE]: Technical trace consolidation
            mergedProg = [...historyLogs];
            serverProgLogs.forEach((sl: any) => {
              const logObj = { ...sl };
              if (logObj.ts && logObj.ts < 2_000_000_000) logObj.ts = logObj.ts * 1000;
              if (!mergedProg.some(ml => ml.msg === logObj.msg && ml.ts === logObj.ts)) {
                mergedProg.push(logObj);
              }
            });
          }

          set(s => ({
            ...s,
            currentMissionId: data.id,
            goal: s.goal || data.goal || '',
            missionGoal: data.goal || '',
            operationalLogs: mergedOps.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(isCompleted ? -1000 : -200),
            progressLogs: mergedProg.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(isCompleted ? -2000 : -2000),
            status: s.status === 'running' ? 'running' : 'idle',
            currentArtifacts: data.artifacts || {},
            modifiedFiles: data.modifiedFiles || []
          }));
        },
        socketActions: null,
        setSocketActions: (socketActions: { submitTask: any; resetDAG: any } | null) => set(s => ({ ...s, socketActions })),
        updateArtifact: (key, content) => set(s => ({
          ...s,
          currentArtifacts: { ...s.currentArtifacts, [key]: content }
        })),

        updateManifest: (manifest: any) => {
          const agentPath = manifest.agent_soul || './agent_receptionist.md';
          const agentName = agentPath.split('/').pop()?.replace('.md', '').toUpperCase() || 'AGENT';

          set(s => ({
            ...s,
            activeAgent: {
              name: agentName,
              soul: agentPath,
              stars: 5,
              reason: manifest.reason || ''
            },
            activeSkills: manifest.skills || [],
            modifiedFiles: manifest.modified_files || s.modifiedFiles
          }));
        },
        setUnreadTab: (tab, val) => set(s => ({ ...s, unreadTabs: { ...s.unreadTabs, [tab]: val } })),
        incrementUnreadTab: (tab) => set(s => ({ ...s, unreadTabs: { ...s.unreadTabs, [tab]: (s.unreadTabs[tab] || 0) + 1 } })),
        
        setBackgroundProposals: (proposals) => set(s => {
          const uniqueMap = new Map();
          (proposals || []).forEach(p => { if (p && p.id) uniqueMap.set(p.id, p); });
          return { ...s, backgroundProposals: Array.from(uniqueMap.values()) };
        }),
        addBackgroundProposal: (proposal) => set(s => {
          if (!proposal || !proposal.id) return s;
          if (s.backgroundProposals.some(p => p.id === proposal.id)) return s;
          return { ...s, backgroundProposals: [proposal, ...s.backgroundProposals] };
        }),
        removeBackgroundProposal: (id) => set(s => ({ 
          ...s, 
          backgroundProposals: s.backgroundProposals.filter(p => p.id !== id) 
        })),
        updateProposalStatus: (id, status) => set(s => ({
          ...s,
          backgroundProposals: s.backgroundProposals.map(p => p.id === id ? { ...p, status } : p)
        })),
        setPulse: (pulse) => set(s => ({ ...s, pulse })),
      }),
      {
        name: 'zenith-supreme-storage-v4',
        partialize: (state) => ({
          cognitiveMode: state.cognitiveMode,
          rightTab: state.rightTab,
          isPaused: state.isPaused,
          showReasoning: state.showReasoning,
          language: state.language,
          inputHistory: state.inputHistory,
          streamView: state.streamView,
          currentMissionId: state.currentMissionId,
          sessionId: state.sessionId,
          missionGoal: state.missionGoal
        }),
      }
    )
  )
);
