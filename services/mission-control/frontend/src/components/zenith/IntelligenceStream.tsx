import React, { memo, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, MessageSquare, History, Plus, Paperclip, Send, Square, Bot, Zap, Swords, ChevronUp, ChevronDown, Trash2, Target, FileText, X, Radar, Database, Search, Calendar, Clock, Archive } from 'lucide-react';
import toast from 'react-hot-toast';
import { useZenithStore, Dictionary, CognitiveMode } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';
import { useAgentController } from '../../hooks/useAgentController';
import { LogItem } from './LogItem';
import { ExecutionTrace } from './ExecutionTrace';
import { WorkingDots, AntigravityProcessTree } from './LogElements';
export const IntelligenceStream = memo(() => {
  const goal = useZenithStore(s => s.goal);
  const setGoal = useZenithStore(s => s.setGoal);
  const status = useZenithStore(s => s.status);
  const setStatus = useZenithStore(s => s.setStatus);
  const isStopping = useZenithStore(s => s.isStopping);
  const cognitiveMode = useZenithStore(s => s.cognitiveMode);
  const attachedFiles = useZenithStore(s => s.attachedFiles);
  const streamView = useZenithStore(s => s.streamView);
  const operationalLogs = useZenithStore(s => s.operationalLogs);
  const progressLogs = useZenithStore(s => s.progressLogs);
  const currentMissionId = useZenithStore(s => s.currentMissionId);
  const isConnected = useZenithStore(s => s.isConnected);
  const reset = useZenithStore(s => s.reset);
  const loadMissionData = useZenithStore(s => s.loadMissionData);
  const language = useZenithStore(s => s.language);

  const clearTrace = useZenithStore(s => s.clearTrace);
  const executionTrace = useZenithStore(s => s.executionTrace);
  const hasTraceItems = !!(executionTrace && executionTrace.items && executionTrace.items.length > 0);
  const setFiles = useZenithStore(s => s.setFiles);
  const setMode = useZenithStore(s => s.setMode);
  const inputHistory = useZenithStore(s => s.inputHistory);
  const inputHistoryIndex = useZenithStore(s => s.inputHistoryIndex);
  const setInputHistoryIndex = useZenithStore(s => s.setInputHistoryIndex);

  const { runAgent, stopAgent } = useAgentController();
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const wasAtBottom = useRef(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [missions, setMissions] = useState<any[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [localGoal, setLocalGoal] = useState(goal);

  // 🔄 [GOAL-SYNC]: Đồng bộ Local State với Store
  useEffect(() => {
    setLocalGoal(goal);
  }, [goal]);

  // 🔄 [TEXTAREA-HEIGHT-SYNC]: Tự động điều chỉnh độ cao của vùng gõ
  useEffect(() => {
    if (textareaRef.current) {
      if (!localGoal) {
        textareaRef.current.style.height = 'auto';
      } else {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      }
    }
  }, [localGoal]);

  const dict = Dictionary[language as keyof typeof Dictionary] || Dictionary.en;

  const visibleLogs = useMemo(() => { 
    if (streamView === 'process') 
      return progressLogs;
    if (streamView === 'full') { 
      // 🧬 [NEURAL-FUSION]: Hợp nhất cả hai luồng 
      const merged = [...operationalLogs]; 
      progressLogs.forEach(pl => { if (!merged.some(ol => ol.id === pl.id)) merged.push(pl); }); 
      return merged.sort((a, b) => (a.ts || 0) - (b.ts || 0));
    } 
    
    // Ở Nhật ký điều hành (Chat view chuẩn Antigravity):
    // Giữ đúng thứ tự lịch sử thời gian: Tin nhắn Master -> Tư duy & Hành động của lượt đó -> Phản hồi JKAI
    // 0. Hàm kiểm tra log rác nội bộ / tóm tắt nén compaction / status tiến trình
    const isInternalNoiseText = (text: string) => {
      const lower = (text || '').toLowerCase();
      return lower.includes('sovereign local runtime') ||
             lower.includes('local execution succeeded') ||
             lower.includes('safe execution:') ||
             lower.includes('[allow] tool') ||
             lower.includes('runtime ready') ||
             lower.includes('mission initialized') ||
             lower.includes('goal identity') ||
             lower.includes('policy topology') ||
             lower.includes('phản xạ tức thì') ||
             lower.includes('khởi chạy lộ trình') ||
             lower.includes('react loop') ||
             lower.includes('conversational_reflex') ||
             lower.includes('aqv-pass') ||
             lower.includes('aqv-') ||
             lower.includes('[latency]') ||
             lower.includes('reflex score=') ||
             lower.includes('fallback:') ||
             lower.includes('the system successfully created') ||
             lower.includes('step completed without errors') ||
             lower.includes('in-flight turn') ||
             lower.includes('active task sequence') ||
             lower.includes('multi-turn process with no errors') ||
             lower.includes('no further details were required') ||
             lower.includes('ongoing process involving') ||
             lower.includes('action marked step one') ||
             lower.includes('marked the beginning of an active task') ||
             lower.includes('[t6] báo cáo đã soạn thảo hoàn tất') ||
             lower.includes('[t6] ban thư ký đang soạn báo cáo') ||
             lower.includes('báo cáo đã soạn thảo hoàn tất') ||
             lower.includes('ban thư ký đang soạn báo cáo');
    };

    const ops = operationalLogs.filter(l => {
      const tag = (l.tag || '').toUpperCase();
      const msg = l.msg || '';
      if (isInternalNoiseText(msg)) return false;
      return tag.startsWith('MASTER') || tag === 'JKAI' || tag === 'DONE' || tag === 'RESULT' || tag.includes('RECEPTIONIST') || tag === 'SUMMARIZER' || tag === 'MISSION_RESULT' || l.type === 'user';
    });

    const actionsAndThoughts = progressLogs.filter(pl => {
      const tag = (pl.tag || '').toUpperCase();
      const msg = pl.msg || '';
      if (isInternalNoiseText(msg)) return false;

      // 1. Hành động công cụ (Tools, Searches, Files, Commands)
      const isTargetAction = ['EXECUTOR', 'SEARCH', 'RESEARCH', 'FILE', 'TOOL', 'COMMAND', 'EXEC', 'THỰC THI'].includes(tag);
      const hasActionKeyword = msg.includes('read') || msg.includes('view') || msg.includes('edit') || 
                               msg.includes('patch') || msg.includes('write') || msg.includes('analyz') ||
                               msg.includes('explor') || msg.includes('search') || msg.includes('find') ||
                               msg.includes('command') || msg.includes('exec') || msg.includes('chạy') ||
                               msg.includes('lệnh') || msg.includes('phân tích') || msg.includes('sửa') || msg.includes('truy xuất');
      
      // 2. Tư duy nhận thức (Thoughts / Planner)
      const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER') || tag.includes('TƯ DUY');
      
      // 3. File diffs và phân đoạn bước
      const isSpecial = tag === 'FILE-EDIT' || (tag === 'ZENITH' && msg.includes('[step'));

      return (isTargetAction && hasActionKeyword) || isThought || isSpecial;
    });

    const merged = [...ops];
    actionsAndThoughts.forEach(act => {
      if (!merged.some(m => m.id === act.id)) {
        merged.push(act);
      }
    });

    // 🛡️ [ANTIGRAVITY-DEDUP]: Khử trùng lặp huy hiệu hành động liên tiếp cho cùng 1 tác vụ
    const sorted = merged.sort((a, b) => (a.ts || 0) - (b.ts || 0));
    const deduplicated: typeof sorted = [];
    let lastActionKey = '';
    let lastActionTs = 0;

    sorted.forEach(item => {
      const tag = (item.tag || '').toUpperCase();
      const msg = (item.msg || '').toLowerCase();
      const isAction = ['EXECUTOR', 'SEARCH', 'RESEARCH', 'FILE', 'TOOL', 'COMMAND', 'EXEC', 'THỰC THI'].includes(tag);
      
      if (isAction) {
        // Rút gọn key hành động để nhận diện duplicate
        const actionKey = msg.replace(/\s+/g, ' ').slice(0, 40);
        const itemTs = item.ts || 0;
        if (actionKey === lastActionKey && Math.abs(itemTs - lastActionTs) < 4) {
          return; // Bỏ qua badge trùng
        }
        lastActionKey = actionKey;
        lastActionTs = itemTs;
      } else {
        lastActionKey = '';
      }
      deduplicated.push(item);
    });

    return deduplicated;
  }, [streamView, operationalLogs, progressLogs]);

  // 🌲 [ANTIGRAVITY-TURN-ARCHITECTURE]: Cấu trúc Turn chuẩn Antigravity
  // Mỗi Turn đại diện cho 1 chu kỳ đối thoại trọn vẹn:
  // Lời nhắn Master -> Cây tiến trình (tư duy, kế hoạch, tool calls) -> Phản hồi cuối cùng của JKAI
  interface Turn {
    id: string;
    isGreeting?: boolean;
    greetingLogs?: any[];
    userLog?: any;
    processLogs: any[];
    assistantLog?: any;
  }

  const turns = useMemo(() => {
    if (streamView === 'full' || streamView === 'process') {
      return null;
    }

    const resultTurns: Turn[] = [];
    let currentTurn: Turn | null = null;

    visibleLogs.forEach((l, idx) => {
      const tag = (l.tag || '').toUpperCase();
      const raw = (l.msg || '').trim();
      const isUser = tag.startsWith('MASTER') || l.type === 'user';
      // Chỉ coi là Assistant Final nếu không phải là kế hoạch json và có nội dung thực tế
      const isAssistantFinal = (tag === 'JKAI' || tag === 'DONE' || tag === 'RESULT' || tag === 'MISSION_RESULT' || tag.includes('RECEPTIONIST') || tag.includes('SUMMARIZER')) && !raw.startsWith('{');

      if (isUser) {
        // Bắt đầu 1 Turn mới của Master
        if (currentTurn) {
          resultTurns.push(currentTurn);
        }
        currentTurn = {
          id: l.id || `turn-${idx}`,
          userLog: l,
          processLogs: [],
          assistantLog: null,
        };
      } else if (!currentTurn) {
        // Chưa có tin nhắn Master nào (ví dụ banner chào mừng lúc đầu)
        let greetingTurn = resultTurns.find(t => t.isGreeting);
        if (!greetingTurn) {
          greetingTurn = {
            id: 'greeting-turn',
            isGreeting: true,
            greetingLogs: [],
            processLogs: [],
          };
          resultTurns.push(greetingTurn);
        }

        // Phân loại log trước tin nhắn Master:
        const isAction = ['EXECUTOR', 'SEARCH', 'RESEARCH', 'FILE', 'TOOL', 'COMMAND', 'EXEC', 'THỰC THI'].includes(tag);
        const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER') || tag.includes('TƯ DUY');
        const isProcess = isAction || isThought || tag === 'FILE-EDIT' || (tag === 'ZENITH' && raw.includes('[step'));

        if (isProcess) {
          greetingTurn.processLogs.push(l);
        } else if (isAssistantFinal) {
          greetingTurn.assistantLog = l;
        } else {
          greetingTurn.greetingLogs?.push(l);
        }
      } else {
        // Trong một Turn của Master
        if (isAssistantFinal) {
          if (currentTurn.assistantLog) {
            // Nếu đã có assistantLog trước đó trong cùng 1 turn (ví dụ bản thảo trước khi replan),
            // chuyển nó vào processLogs để giữ lịch sử và không làm phân mảnh timeline
            currentTurn.processLogs.push(currentTurn.assistantLog);
          }
          currentTurn.assistantLog = l;
        } else {
          // Các bước tư duy, trinh sát, kế hoạch, thực thi công cụ
          currentTurn.processLogs.push(l);
        }
      }
    });

    if (currentTurn) {
      resultTurns.push(currentTurn);
    }

    return resultTurns;
  }, [visibleLogs, streamView]);

  // 🔍 [PROCESS-LINE-SYNC]: Lấy các log kỹ thuật gần nhất để hiển thị
  const technicalLogs = useMemo(() => {
    return progressLogs.slice(-3);
  }, [progressLogs]);

  const userScrolledRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 🛡️ [SMOOTH-SCROLL-THROTTLE]: Tránh "giật" UI khi log về quá nhanh
  const lastScrollTime = useRef(0);
  useEffect(() => {
    const now = Date.now();
    if (!userScrolledRef.current && now - lastScrollTime.current > 100) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      lastScrollTime.current = now;
    }
  }, [visibleLogs, technicalLogs]);

  useEffect(() => {
    return () => { if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current); };
  }, []);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    setScrollProgress((scrollTop / (scrollHeight - clientHeight)) * 100);

    // 🛡️ [MANUAL-SCROLL-PRIORITY]: Nếu khoảng cách tới đáy > 100px, ưu tiên Master xem log
    const isAtBottom = scrollHeight - (scrollTop + clientHeight) < 100;
    
    if (isAtBottom) {
      userScrolledRef.current = false;
      wasAtBottom.current = true;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    } else {
      userScrolledRef.current = true;
      wasAtBottom.current = false;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
      resumeTimerRef.current = setTimeout(() => {
        userScrolledRef.current = false;
        wasAtBottom.current = true;
      }, 120_000); // 2 phút
    }
  };

  const handleNewMission = async (silent: boolean = false) => {
    // Chỉ xóa cờ stop_signal để chuẩn bị cho mission mới, không gọi stopAgent gây spam log dừng
    await ZenithService.sendSystemCmd('clear_stop');
    reset();
    clearTrace();
    setGoal('');
    wasAtBottom.current = true;
    if (!silent) {
      toast.dismiss();
      toast.success('Neural environment reset complete.', { id: 'ZENITH_PULSE' });
    }
  };

  const handleLoadMission = async (id: string) => {
    const loadingToast = toast.loading('Đang khôi phục ngữ cảnh...', { id: 'ZENITH_PULSE' });
    try {
      const data = await ZenithService.getMission(id);
      loadMissionData(data);
      wasAtBottom.current = true;
      setShowHistory(false);
      toast.success(language === 'vi' ? 'Hồ sơ thần kinh đã tải!' : 'Neural records loaded!', { id: 'ZENITH_PULSE' });
    } catch {
      toast.error(language === 'vi' ? 'Lỗi khi tải dữ liệu' : 'Error loading records', { id: 'ZENITH_PULSE' });
    }
  };

  const handleDeleteMission = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const confirmMsg = language === 'vi' ? 'Xoá nhiệm vụ này?' : 'Delete this mission?';
    if (!window.confirm(confirmMsg)) return;

    await ZenithService.deleteMission(id);
    loadMissions();
    toast.success(language === 'vi' ? 'Record deleted.' : 'Mission deleted.', { id: 'ZENITH_PULSE' });
  };

  const handleClearAll = async () => {
    const confirmMsg = language === 'vi' ? 'Xoá toàn bộ lịch sử nhiệm vụ?' : 'Clear all mission history?';
    if (!window.confirm(confirmMsg)) return;

    await ZenithService.clearMissions();
    loadMissions();
    toast.success(language === 'vi' ? 'Đã xóa toàn bộ lịch sử.' : 'All history cleared.', { id: 'ZENITH_PULSE' });
  };

  const loadMissions = useCallback(async () => {
    try {
      const data = await ZenithService.listMissions();
      setMissions(data);
    } catch (e) {
      console.error("Failed to load missions", e);
    }
  }, []);

  useEffect(() => {
    if (showHistory) loadMissions();
  }, [showHistory, loadMissions]);

  useEffect(() => {
    const handleReload = () => {
      loadMissions();
    };
    window.addEventListener('zenith:reload-missions', handleReload);
    return () => {
      window.removeEventListener('zenith:reload-missions', handleReload);
    };
  }, [loadMissions]);

  // 🚀 [AUTO-INIT]: Khởi động Sứ mệnh mới hoặc khôi phục Sứ mệnh đang chạy khi mount/reload
  useEffect(() => {
    const initOrRestore = async () => {
      // Chờ một chút để các kết nối Socket ổn định
      await new Promise(r => setTimeout(r, 500));
      
      const activeMissionId = useZenithStore.getState().currentMissionId;
      if (activeMissionId) {
        try {
          const data = await ZenithService.getMission(activeMissionId);
          await loadMissionData(data);
          wasAtBottom.current = true;
          console.log(`📡 [AUTO-INIT]: Restored active mission: ${activeMissionId}`);
        } catch (e) {
          console.warn('📡 [AUTO-INIT]: Failed to restore active mission, starting new...', e);
          handleNewMission(true);
        }
      } else {
        handleNewMission(true);
      }
    };
    initOrRestore();
  }, [loadMissionData]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // 🛡️ [FLICKER-PROTECTION]: Chỉ tắt dragging khi chuột thực sự rời khỏi container
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setFiles([...attachedFiles, ...files]);
      toast.success(`Đã đính kèm ${files.length} tệp.`, { id: 'ZENITH_PULSE' });
    }
  }, [attachedFiles, setFiles]);

  return (
    <div className="flex-1 flex flex-col gap-3 min-h-0">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`flex-1 flex flex-col min-h-0 rounded-2xl border transition-all duration-500 bg-[#07090f]/90 overflow-hidden shadow-2xl relative ${isDragging ? 'border-sky-500 shadow-[0_0_30px_rgba(14,165,233,0.2)] scale-[0.99]' : 'border-white/[0.06]'
          }`}
      >
        {isDragging && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-sky-500/10 backdrop-blur-sm pointer-events-none border-2 border-dashed border-sky-500/50 m-4 rounded-xl">
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex flex-col items-center gap-4"
            >
              <div className="p-6 rounded-full bg-sky-500/20 border border-sky-500/40">
                <Plus className="w-12 h-12 text-sky-400 animate-bounce" />
              </div>
              <span className="text-sm font-black text-sky-400 uppercase tracking-[0.3em]">{language === 'vi' ? 'Drop Files to Assimilate' : 'Drop Files Here'}</span>
            </motion.div>
          </div>
        )}

        <div className="absolute top-0 left-0 w-full h-[1px] bg-white/5 z-20">
          <motion.div className="h-full bg-sky-500/40" style={{ width: `${scrollProgress}%` }} />
        </div>

        <AnimatePresence>
          {showHistory && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="absolute inset-0 z-40 bg-[#060910] flex flex-col min-h-0 overflow-hidden border-l border-white/10 shadow-2xl"
            >
              <div className="shrink-0 flex items-center justify-between p-6 border-b border-white/5">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.1)]">
                      <Archive className="w-5 h-5 text-amber-400" />
                    </div>
                     <div>
                      <h3 className="text-sm font-black text-white uppercase tracking-[0.2em]">{dict.mission_history || 'Mission History'}</h3>
                      <p className="text-[10px] text-amber-500/40 font-bold uppercase tracking-widest">
                        {language === 'vi' ? 'Lịch sử nhiệm vụ' : 'Archived Mission Log Files'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {missions.length > 0 && (
                    <button 
                      onClick={handleClearAll}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-all group"
                      title={language === 'vi' ? 'Xóa toàn bộ' : 'Clear All'}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span className="text-[9px] font-black uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">
                        {language === 'vi' ? 'Xoá' : 'Clear'}
                      </span>
                    </button>
                  )}
                  <button onClick={() => setShowHistory(false)} className="p-2 text-white/20 hover:text-white transition-colors">
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 custom-scroll space-y-3">
                {missions.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center opacity-10 gap-4">
                    <Database className="w-10 h-10" />
                    <span className="text-[10px] font-black uppercase tracking-widest">
                      {language === 'vi' ? 'Chưa ghi nhận sứ mệnh nào' : 'No Missions Recorded'}
                    </span>
                  </div>
                ) : (
                  missions.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => handleLoadMission(m.id)}
                      className={`w-full text-left p-4 rounded-2xl border transition-all group ${currentMissionId === m.id
                        ? 'bg-sky-500/10 border-sky-500/30'
                        : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05] hover:border-white/10'
                        }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 group-hover:bg-sky-500/20 transition-all">
                            <Database className="w-3.5 h-3.5 text-sky-400" />
                          </div>
                          <span className="text-[9px] font-black text-white/20 tracking-tighter uppercase">{m.id}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-bold text-white/20">{new Date(m.ts * 1000).toLocaleDateString()}</span>
                          <button
                            onClick={(e) => handleDeleteMission(m.id, e)}
                            className="p-1.5 rounded-lg hover:bg-rose-500/20 text-white/5 hover:text-rose-400 transition-all opacity-0 group-hover:opacity-100"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                      <h4 className="text-[13px] font-bold text-white/80 line-clamp-2 group-hover:text-white transition-colors">{m.title}</h4>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex-1 relative min-h-0 border-b border-white/[0.03]">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="absolute inset-0 overflow-y-auto px-6 pt-6 space-y-3 custom-scroll scroll-smooth"
            style={{ paddingBottom: '40px' }}
          >
            {visibleLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-[0.08] gap-5">
                <Brain className="w-20 h-20 text-white" strokeWidth={1} />
                <p className="text-[11px] font-black uppercase tracking-[0.8em]">{dict.awaiting}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2.5 pb-20">
                {turns ? (
                  // Chế độ Antigravity Turn-based chuẩn mực:
                  // Master Prompt -> Process Tree (ngay dưới) -> WorkingDots (nếu đang chạy) -> Final JKAI Answer
                  turns.map((turn, tIdx) => {
                    const isLastTurn = tIdx === turns.length - 1;
                    const isRunningOnThisTurn = isLastTurn && status === 'running';

                    if (turn.isGreeting) {
                      return (
                        <div key={turn.id} className="space-y-3">
                          {turn.greetingLogs?.map((gl, gIdx) => (
                            <LogItem key={gl.id || gIdx} l={gl} forceReasoning={false} />
                          ))}
                          {turn.processLogs.length > 0 && (
                            <AntigravityProcessTree 
                              items={turn.processLogs} 
                              isRunning={false}
                              startTs={turn.processLogs[0]?.ts}
                              finishTs={turn.assistantLog?.ts}
                            />
                          )}
                          {turn.assistantLog && (
                            <LogItem l={turn.assistantLog} forceReasoning={false} />
                          )}
                        </div>
                      );
                    }

                    return (
                      <div key={turn.id} className="flex flex-col gap-3">
                        {/* 1. Câu hỏi / Lệnh của Master */}
                        {turn.userLog && (
                          <LogItem l={turn.userLog} forceReasoning={false} />
                        )}

                        {/* 2. Cây Tiến Trình (Tư duy, Kế hoạch, Công cụ) - LUÔN nằm ngay dưới câu hỏi */}
                        {turn.processLogs.length > 0 && (
                          <AntigravityProcessTree 
                            items={turn.processLogs} 
                            isRunning={isRunningOnThisTurn && !turn.assistantLog}
                            startTs={turn.userLog?.ts || turn.processLogs[0]?.ts}
                            finishTs={turn.assistantLog?.ts}
                          />
                        )}

                        {/* 3. Hiệu ứng đang chạy nếu đang xử lý lượt này và chưa có bước tiến trình nào */}
                        {isRunningOnThisTurn && !turn.assistantLog && turn.processLogs.length === 0 && (
                          <div className="my-1">
                            <WorkingDots label={language === 'vi' ? 'Đang thực thi..' : 'Working..'} />
                          </div>
                        )}

                        {/* 4. Câu trả lời chính thức của JKAI */}
                        {turn.assistantLog && (
                          <LogItem l={turn.assistantLog} forceReasoning={false} />
                        )}

                        {/* 5. Nếu đang chạy thêm sau phản hồi (ví dụ hậu kiểm) */}
                        {isRunningOnThisTurn && turn.assistantLog && (
                          <div className="my-1">
                            <WorkingDots label={language === 'vi' ? 'Đang hoàn tất..' : 'Finalizing..'} />
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  // Chế độ Full / Process log
                  visibleLogs.map((l, i) => (
                    <LogItem key={l.id || i} l={l} forceReasoning={streamView === 'full'} />
                  ))
                )}
                {/* ⚓ [NEURAL-ANCHOR]: Mỏ neo cưỡng chế cuộn  */}
                <div ref={messagesEndRef} className="h-4 shrink-0" />
              </div>
            )}
          </div>

          {/* 🌑 [FADE-OUT]: Hiệu ứng mờ dần ở đáy  */}
          <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-[#07090f] to-transparent pointer-events-none z-10" />
        </div>

        {/* Input Area */}
        <div className="shrink-0 p-6 pt-2 border-t border-white/[0.03] bg-black/40 relative z-30">
          <div className="relative bg-[#020408]/60 backdrop-blur-3xl border border-white/[0.05] rounded-2xl overflow-hidden focus-within:border-cyan-400/40 transition-all duration-500">
            {attachedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 p-3 pb-0">
                {attachedFiles.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20">
                    <Paperclip className="w-3 h-3 text-sky-400" />
                    <span className="text-[10px] font-bold text-white/70 truncate max-w-[120px]">{f.name}</span>
                    <button onClick={() => setFiles(attachedFiles.filter((_, idx) => idx !== i))} className="text-white/20 hover:text-rose-400">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-end gap-3 p-3 px-4">
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                multiple
                onChange={(e) => {
                  const files = Array.from(e.target.files || []);
                  setFiles([...attachedFiles, ...files]);
                }}
              />
              <div className="flex items-center gap-1 mb-1">
                <button onClick={handleNewMission} className="p-2 text-white/20 hover:text-emerald-400 transition-colors">
                  <Plus className="w-[20px] h-[20px]" />
                </button>
                <button onClick={() => fileInputRef.current?.click()} className="p-2 text-white/20 hover:text-sky-400 transition-colors">
                  <Paperclip className="w-[18px] h-[18px]" />
                </button>
              </div>

              <textarea
                ref={textareaRef}
                value={localGoal}
                disabled={!isConnected}
                onChange={(e) => {
                  setLocalGoal(e.target.value);
                  setGoal(e.target.value);
                }}
                 onKeyDown={(e) => { 
                  if (e.key === 'Enter' && !e.shiftKey) { 
                    e.preventDefault(); 
                    if (isConnected && localGoal.trim()) {
                      runAgent();
                    }
                  } else if (e.key === 'ArrowUp') {
                    const target = e.target as HTMLTextAreaElement;
                    if (target.selectionStart === 0) {
                      e.preventDefault();
                      const history = inputHistory || [];
                      let idx = inputHistoryIndex;
                      if (idx === -1) idx = history.length;
                      if (idx > 0) {
                        const nextIdx = idx - 1;
                        setInputHistoryIndex(nextIdx);
                        const prevGoal = history[nextIdx];
                        setLocalGoal(prevGoal);
                        setGoal(prevGoal);
                      }
                    }
                  } else if (e.key === 'ArrowDown') {
                    const target = e.target as HTMLTextAreaElement;
                    if (target.selectionStart === target.value.length) {
                      e.preventDefault();
                      const history = inputHistory || [];
                      let idx = inputHistoryIndex;
                      if (idx !== -1 && idx < history.length) {
                        const nextIdx = idx + 1;
                        setInputHistoryIndex(nextIdx);
                        const nextGoal = nextIdx === history.length ? '' : history[nextIdx];
                        setLocalGoal(nextGoal);
                        setGoal(nextGoal);
                      }
                    }
                  }
                }}
                placeholder={!isConnected ? '📡 [SYSTEM]: Neural Bridge Offline. Awaiting restoration...' : status === 'running' ? dict.processing : dict.placeholder}
                className={`flex-1 bg-transparent border-none outline-none ring-0 text-base py-2.5 h-auto max-h-48 resize-none transition-all duration-300 custom-scroll ${!isConnected ? 'opacity-20 cursor-not-allowed italic' : 'placeholder:text-white/10 text-white/90'}`}
                rows={1}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${target.scrollHeight}px`;
                }}
              />

              <div className="flex items-center gap-2 mb-1">
                {/* 🧠 [AUTO-HYBRID-BADGE]: Hiển thị trạng thái thích ứng tự động AUTO */}
                <div
                  title="Chế độ Tự Động Thích Ứng (Auto Hybrid): Tự động phản xạ nhanh 0.3s cho câu hỏi đơn giản và kích hoạt Deep Reasoning cho bài toán lớn."
                  className="px-3.5 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all duration-500 shadow-lg border bg-cyan-500/20 text-cyan-400 border-cyan-500/40 shadow-cyan-500/10 flex items-center gap-1.5 select-none"
                >
                  <Zap className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                  <span>AUTO</span>
                </div>

                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className={`p-3 rounded-xl transition-all ${showHistory ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-white/5 text-white/20 hover:text-white/40 border border-transparent'}`}
                >
                  <History className="w-[20px] h-[20px]" />
                </button>

                {/* [FIX-P2]: 3 trạng thái rõ ràng: stopping → loading disabled, running → stop, idle → send */}
                <button
                  disabled={isStopping}
                  onClick={
                    isStopping
                      ? undefined
                      : status === 'running'
                        ? () => stopAgent()
                        : () => runAgent()
                  }
                  className={`p-3 rounded-xl transition-all shadow-xl ${
                    isStopping
                      ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30 opacity-70 cursor-wait'
                      : status === 'running'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : 'bg-sky-500 text-white hover:scale-105 active:scale-95 shadow-sky-500/20'
                  }`}
                >
                  {isStopping
                    ? <span className="w-[20px] h-[20px] flex items-center justify-center"><span className="w-3 h-3 border-2 border-orange-400 border-t-transparent rounded-full animate-spin" /></span>
                    : status === 'running'
                      ? <Square className="w-[20px] h-[20px]" />
                      : <Send className="w-[20px] h-[20px]" />
                  }
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});
