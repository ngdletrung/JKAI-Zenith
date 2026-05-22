import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export type AgentStatus = 'idle' | 'running' | 'paused' | 'error';
export type CognitiveMode = 'auto' | 'fast' | 'deep';
export type RightTab = 'progress' | 'plan' | 'tasks' | 'walkthrough' | 'explorer' | 'changes' | 'logs' | 'terminal' | 'filelab';
export type StreamView = 'chat' | 'process' | 'full';

export interface Proposal {
  id: string;
  title: string;
  path: string;
  diff: string;
  status: 'pending' | 'applied' | 'rejected';
  ts: number;
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
}

export interface TraceItem {
  id: string;
  type: 'file' | 'folder' | 'search' | 'thought' | 'command';
  label: string;
  detail?: string;
  ts: number;
  status: 'pending' | 'completed';
  logId?: string; // 📡 [LOG-LINK]: ID của log gốc để cuộn đến
}

export interface AgentLog extends TaskLog {
  id: string;
  type?: 'user' | 'ai' | 'sys' | 'tool';
  action?: string;
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
    tab_filelab: 'File Lab',

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
    new_mission: 'Khởi tạo Sứ mệnh mới',
    placeholder: 'Master yêu cầu Sứ mệnh nào? Nhập lệnh hoặc Mật lệnh...',
    processing: 'Đang thực thi Giao thức Tập đoàn...',
    copied: 'Đã sao chép Chữ ký',
    system_online: 'Hệ thống Zenith Trực tuyến',
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
    official_artifact: 'Hồ sơ Sứ mệnh Chính thức',
    thinking_msg: 'Đang xử lý',
    tab_progress: 'Tiến trình',
    tab_terminal: 'Cửa sổ Lệnh',
    cmd_dispatch: 'Nhập mật khẩu lệnh điều hành...',
    no_artifact: '# Không tìm thấy Hồ sơ\nKhởi tạo sứ mệnh để tạo dữ liệu Tập đoàn.',
    artifact_error: '# Lỗi khi tải hồ sơ',
    tab_filelab: 'Phòng File',
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
    t_complete: 'Sứ mệnh hoàn tất. Báo cáo đã sẵn sàng trình Master.',
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
  inspectedFile: { path: string; content: string } | null;
  thinkingPhrase: string;
  showReasoning: boolean;
  streamView: StreamView;
  debateCount: number;

  currentMissionId: string | null;
  history: any[];
  modifiedFiles: string[];
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
  unreadTabs: Record<string, boolean>;
  pulse: { cpu: number; ram: number; gpu: number; status: string; active_thoughts: string };
  isConnected: boolean;

  // 🧭 EXECUTION TRACE PROTOCOL
  executionTrace: {
    items: TraceItem[];
    isExpanded: boolean;
    lastUpdate: number;
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
  setInspectedFile: (file: { path: string; content: string } | null) => void;
  addModifiedFile: (path: string) => void;
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
  setUnreadTab: (tab: string, val: boolean) => void;
  setPulse: (pulse: any) => void;
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
        history: [],
        modifiedFiles: [],
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
        pulse: { cpu: 0, ram: 0, gpu: 0, status: 'STANDBY', active_thoughts: 'IDLE' },
        isConnected: false,
        executionTrace: {
          items: [],
          isExpanded: true,
          lastUpdate: Date.now()
        },

        setTraceExpanded: (isExpanded) => set(s => ({
          ...s,
          executionTrace: { ...s.executionTrace, isExpanded }
        })),
        clearTrace: () => set(s => ({
          ...s,
          executionTrace: { items: [], isExpanded: true, lastUpdate: Date.now() }
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
        setStatus: (status) => set(s => ({ ...s, status })),
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
            // 🛡️ [CONTENT-HASH-ID]: Tạo ID dựa trên nội dung để tránh lặp vòng
            log.id = `hash_${tag}_${msg.length}_${msg.slice(0, 30)}_${log.ts || '0'}`;
          }

          // 🚦 [LOG-ROUTING-PROTOCOL]: Tự động phân luồng nơ-ron
          const tag = log.tag?.toUpperCase() || 'SYS';
          const isHighPriority = ['MASTER', 'MASTER_WEB', 'MASTER_TELE', 'JKAI', 'MISSION_RESULT', 'ERROR'].includes(tag);

          const technicalTags = ['DEBUG', 'THOUGHT', 'PLANNER', 'DISPATCHER', 'RECEPTIONIST', 'TRACE', 'LATENCY', 'FORGE_V3', 'STEWARD'];
          const isTechnicalMsg = /\[(DEBUG|DELEGATED|DELEGATION|GATEWAY|MEMORY|EXEC|SKILL|PLAN|TASK)\]/i.test(log.msg || '');

          // 🧭 [TRACE-EXTRACTION]: Trích xuất dấu vết thực thi
          const msg = log.msg || '';
          let traceItem: TraceItem | null = null;

          if (tag.includes('EXECUTOR') || tag.includes('THỰC THI')) {
            if (msg.includes('`')) {
              const match = msg.match(/`([^`]+)`/);
              if (match) {
                const label = match[1];
                traceItem = { id: `tr-${Date.now()}`, type: 'file', label, ts: Date.now(), status: 'completed' };
                if (label.includes('.') && !label.includes('/')) traceItem.type = 'file';
                else if (label.includes('/') || label.includes('\\')) traceItem.type = 'folder';
              }
            }
          } else if (tag.includes('SEARCH') || tag.includes('TRUY TÌM')) {
            const match = msg.match(/`([^`]+)`/) || msg.match(/searching (.*)/i);
            if (match) {
              traceItem = { id: `tr-${Date.now()}`, type: 'search', label: match[1], ts: Date.now(), status: 'completed' };
            }
          } else if (tag.includes('THOUGHT') || tag.includes('TƯ DUY')) {
            traceItem = { id: `tr-${Date.now()}`, type: 'thought', label: 'Tư duy hệ thống', detail: msg.slice(0, 50), ts: Date.now(), status: 'completed' };
          }

          let newTrace = s.executionTrace;
          if (traceItem) {
            newTrace = {
              ...s.executionTrace,
              items: [...s.executionTrace.items, traceItem].slice(-10),
              lastUpdate: Date.now(),
              isExpanded: true
            };
          }

          // 🏛️ [DUAL-ROUTING-PROTOCOL]: Master và JKAI sẽ được ghi vào cả hai luồng
          if (isHighPriority) {
            const updatedOps = [...s.operationalLogs];
            const updatedProg = [...s.progressLogs];

            if (!updatedOps.some(ex => ex.id === log.id)) updatedOps.push(log);
            if (!updatedProg.some(ex => ex.id === log.id)) updatedProg.push(log);

            return {
              ...s,
              operationalLogs: updatedOps.slice(-200),
              progressLogs: updatedProg.slice(-2000),
              executionTrace: newTrace
            };
          }

          const effectiveTarget = (target === 'operational' && (technicalTags.some(t => tag.includes(t)) || isTechnicalMsg))
            ? 'progress'
            : target;

          const targetKey = effectiveTarget === 'progress' ? 'progressLogs' : 'operationalLogs';
          const logsToUpdate = s[targetKey];

          // 📌 [PIN-UPDATE-PROTOCOL]: Nếu cùng ID và là log stream (THOUGHT/PROGRESS), cập nhật tại chỗ
          const existingIdx = logsToUpdate.findIndex(existing => existing.id === log.id);
          if (existingIdx !== -1) {
            const existingLog = logsToUpdate[existingIdx];
            // Chỉ cập nhật nội dung nếu là THOUGHT (stream realtime) hoặc PROGRESS
            if (existingLog.tag.includes('THOUGHT') || existingLog.tag === 'PROGRESS') {
              const updatedLogs = [...logsToUpdate];
              updatedLogs[existingIdx] = { ...existingLog, msg: log.msg, ts: log.ts };
              return { ...s, [targetKey]: updatedLogs, executionTrace: newTrace };
            }
            // Các log khác cùng ID → bỏ qua (duplicate guard)
            return s;
          }

          // 💎 [PROGRESS-IN-PLACE]: Nếu là tin nhắn tiến độ, hãy cập nhật dòng cũ thay vì tạo mới
          if (tag === 'PROGRESS' && logsToUpdate.length > 0) {
            const lastLog = logsToUpdate[logsToUpdate.length - 1];
            if (lastLog.tag === 'PROGRESS' && lastLog.task_id === log.task_id) {
              const updatedLogs = [...logsToUpdate];
              updatedLogs[logsToUpdate.length - 1] = { ...lastLog, ...log };
              return { ...s, [targetKey]: updatedLogs, executionTrace: newTrace };
            }
          }

          // 🛡️ [STEALTH-WIPE-PROTOCOL]: Command cipher purification
          if ((log as any).stealth && (tag === 'AUTH' || tag === 'AUTHENTICATION')) {
            const updatedLogs = [...logsToUpdate];
            for (let i = updatedLogs.length - 1; i >= 0; i--) {
              if (updatedLogs[i].type === 'user') {
                updatedLogs[i] = { ...updatedLogs[i], msg: "🔐 [GIAO THỨC BẢO MẬT ĐÃ KÍCH HOẠT - DẤU VẾT ĐÃ ĐƯỢC THANH TẨY]" };
                break;
              }
            }
            return { ...s, [targetKey]: [...updatedLogs, log].slice(-200), executionTrace: newTrace };
          }

          return { ...s, [targetKey]: [...logsToUpdate, log].sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-200), executionTrace: newTrace };
        }),
        addLogs: (newLogsBatch, target = 'operational') => set((s) => {
          const processedBatch = newLogsBatch.map(nl => {
            const msg = nl.msg || '';
            const tag = nl.tag || 'SYS';
            // 🕒 [CHRONOS-NORMALIZE]: Đồng bộ đơn vị ts
            const rawTs = nl.ts || Date.now();
            const normalizedTs = rawTs < 1e10 ? rawTs * 1000 : rawTs;
            const timeStr = new Date(normalizedTs).toLocaleTimeString();
            const contentId = nl.id || `hash_${tag}_${msg.length}_${msg.slice(0, 20)}_${normalizedTs}`;

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
              if (existsInOps)  updatedOps[opIdx]   = { ...updatedOps[opIdx],   msg: nl.msg, ts: nl.ts };
              if (existsInProg) updatedProg[progIdx] = { ...updatedProg[progIdx], msg: nl.msg, ts: nl.ts };
              else              updatedProg.push(nl); // đảm bảo cũng có ở progress
              continue;
            }

            // 🔍 [EXECUTION-TRACE]: Trích xuất dấu vết thực thi cho ExecutionTrace widget
            if (tag.includes('SEARCH') || tag.includes('THOUGHT') || tag.includes('PLANNER')) {
              let traceType: TraceItem['type'] = 'command';
              if (tag.includes('SEARCH')) traceType = 'search';
              else if (tag.includes('THOUGHT') || tag.includes('PLANNER')) traceType = 'thought';
              else if (msg.includes('`')) traceType = 'file';
              newTraceItems.push({
                id: `tr-${Date.now()}-${Math.random()}`,
                type: traceType,
                label: traceType === 'thought' ? 'System Reasoning' : msg.slice(0, 50),
                detail: traceType === 'thought' ? msg : undefined,
                ts: Date.now(),
                status: 'completed',
                logId: nl.id
              });
            }

            // ════════════════════════════════════════════════════════
            // 🎯 [3-CHANNEL ROUTING ENGINE - FRONTEND]
            // Ưu tiên 1: Dùng channels[] do backend khai báo tường minh
            // Ưu tiên 2: Fallback heuristics từ tag (legacy backward-compat)
            // ════════════════════════════════════════════════════════
            const logChannels: string[] | null = (nl as any).channels ?? null;

            if (logChannels !== null) {
              // ── EXPLICIT ROUTING (new system) ──────────────────────
              if (logChannels.includes('executive')) updatedOps.push(nl);
              if (logChannels.includes('progress'))  updatedProg.push(nl);
              // 'telegram' không ảnh hưởng đến UI state — chỉ backend xử lý
            } else {
              // ── LEGACY ROUTING (backward-compatible) ───────────────
              // Executive: Master/JKAI/Error/MissionResult
              const executiveTags = ['MASTER', 'JKAI', 'MISSION_RESULT', 'ERROR'];
              const goesExec = executiveTags.includes(tag) || tag.startsWith('MASTER') || (nl as any).is_result;

              if (goesExec) {
                updatedOps.push(nl);
                updatedProg.push(nl);
              } else {
                // Technical logs → chỉ Progress
                const isTech = technicalTags.some(t => tag.includes(t)) || /\[(DEBUG|DELEGATED|DELEGATION|GATEWAY|MEMORY|EXEC|SKILL|PLAN|TASK)\]/i.test(msg);
                const targetKey = (target === 'operational' && isTech) ? 'progress' : target;
                if (targetKey === 'progress') updatedProg.push(nl);
                else updatedOps.push(nl);
              }
            }
          }


          return {
            ...s,
            operationalLogs: updatedOps.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-200),
            progressLogs: updatedProg.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-2000),
            executionTrace: { ...s.executionTrace, items: newTraceItems.slice(-10), lastUpdate: Date.now(), isExpanded: true }
          };
        }),
        setTab: (rightTab) => set(s => ({ ...s, rightTab })),
        setInspectedFile: (inspectedFile) => set(s => ({ ...s, inspectedFile })),
        addModifiedFile: (path) => set(s => ({
          ...s,
          modifiedFiles: Array.from(new Set([...s.operationalLogs.filter(l => l.msg?.toLowerCase().includes('edited') || l.msg?.toLowerCase().includes('wrote')).map(l => {
            const m = l.msg?.match(/([a-zA-Z0-9_\-\.\/]+\.[a-z0-9]+)/i);
            return m ? m[0] : null;
          }).filter(Boolean) as string[], path]))
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
          currentMissionId: null,
          activeAgent: null,
          activeSkills: [],
          missionGoal: ''
        })),
        setMissionId: (currentMissionId) => set(s => ({ ...s, currentMissionId })),
        setHistory: (history) => set(s => ({ ...s, history })),
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

          const historyLogs = Array.isArray(data.logs) ? data.logs : [];
          const serverOpsLogs = Array.isArray(opsData.logs) ? opsData.logs : [];
          const serverProgLogs = Array.isArray(progData.logs) ? progData.logs : [];

          // 🏛️ [OPS-MERGE]: Operational log consolidation
          const mergedOps = [...historyLogs];
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
            if (!mergedOps.some(ml => ml.msg === logObj.msg && (ml.timeStr === logObj.timeStr || ml.ts === logObj.ts))) {
              mergedOps.push(logObj);
            }
          });

          // 🔬 [PROG-MERGE]: Technical trace consolidation
          const mergedProg = [...historyLogs];
          serverProgLogs.forEach((sl: any) => {
            if (!mergedProg.some(ml => ml.msg === sl.msg && ml.ts === sl.ts)) {
              mergedProg.push(sl);
            }
          });

          set(s => ({
            ...s,
            currentMissionId: data.id,
            goal: s.goal || data.goal || '',
            missionGoal: data.goal || '',
            operationalLogs: mergedOps.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-200),
            progressLogs: mergedProg.sort((a, b) => (a.ts || 0) - (b.ts || 0)).slice(-2000),
            status: s.status === 'running' ? 'running' : 'idle',
            currentArtifacts: data.artifacts || {},
            modifiedFiles: data.modifiedFiles || []
          }));
        },
        socketActions: null,
        setSocketActions: (socketActions) => set(s => ({ ...s, socketActions })),
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
            activeSkills: manifest.skills || []
          }));
        },
        setUnreadTab: (tab, val) => set(s => ({ ...s, unreadTabs: { ...s.unreadTabs, [tab]: val } })),
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
          missionGoal: state.missionGoal
        }),
      }
    )
  )
);
