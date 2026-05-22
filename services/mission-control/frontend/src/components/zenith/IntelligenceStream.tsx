import React, { memo, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, MessageSquare, History, Plus, Paperclip, Send, Square, Bot, Zap, Swords, ChevronUp, ChevronDown, Trash2, Target, FileText, X, Radar, Database, Search, Calendar, Clock, Archive } from 'lucide-react';
import toast from 'react-hot-toast';
import { useZenithStore, Dictionary } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';
import { useAgentController } from '../../hooks/useAgentController';
import { LogItem } from './LogItem';
import { ExecutionTrace } from './ExecutionTrace';
export const IntelligenceStream = memo(() => {
  const goal = useZenithStore(s => s.goal);
  const setGoal = useZenithStore(s => s.setGoal);
  const status = useZenithStore(s => s.status);
  const setStatus = useZenithStore(s => s.setStatus);
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
    if (streamView === 'process') return progressLogs;
    if (streamView === 'full') {
      // 🧬 [NEURAL-FUSION]: Hợp nhất cả hai luồng
      const merged = [...operationalLogs];
      progressLogs.forEach(pl => {
        if (!merged.some(ol => ol.id === pl.id)) merged.push(pl);
      });
      return merged.sort((a, b) => (a.ts || 0) - (b.ts || 0));
    }
    // 👑 [EXECUTIVE-PURIFICATION v2]: Nhật ký Điều hành chỉ giữ lại:
    //   - Câu hỏi của Master
    //   - Câu trả lời cuối cùng của JKAI (không phải bản nháp trung gian)
    //   - Kết quả Nhiệm vụ và Lỗi
    //   Tất cả THOUGHT/SUMMARIZER/PLANNER trung gian -> TAB TIẦN TRÌNH
    return operationalLogs.filter(l => {
      const tag = l.tag?.toUpperCase() || 'SYS';
      return (
        tag === 'JKAI' || 
        tag.startsWith('MASTER') || 
        tag === 'ERROR' || 
        tag === 'MISSION_RESULT'
      );
    });
  }, [streamView, operationalLogs, progressLogs]);

  // 🏁 [ANSWER-INDEX-DETECTOR]: Xác định vị trí bắt đầu của câu trả lời để chèn Nhật ký tiến trình
  const firstAnswerIndex = useMemo(() => {
    // 1. Tìm index của câu hỏi MASTER cuối cùng
    const lastMasterIdx = [...visibleLogs].reverse().findIndex(l => {
      const tag = l.tag?.toUpperCase() || '';
      return tag.startsWith('MASTER');
    });
    
    // Chuyển đổi index ngược về index xuôi trong mảng gốc
    const lastMasterIndex = lastMasterIdx === -1 ? -1 : (visibleLogs.length - 1 - lastMasterIdx);
    
    if (lastMasterIndex === -1) return -1;
    
    // 2. Tìm câu trả lời đầu tiên xuất hiện SAU câu hỏi Master cuối cùng
    const ansIdx = visibleLogs.slice(lastMasterIndex + 1).findIndex(l => {
      const tag = l.tag?.toUpperCase() || '';
      return tag === 'JKAI' || tag === 'SUMMARIZER' || tag === 'MISSION_RESULT';
    });
    
    return ansIdx === -1 ? -1 : (lastMasterIndex + 1 + ansIdx);
  }, [visibleLogs]);

  // 🔍 [PROCESS-LINE-SYNC]: Lấy các log kỹ thuật gần nhất để hiển thị
  const technicalLogs = useMemo(() => {
    return progressLogs.slice(-3);
  }, [progressLogs]);

  const userScrolledRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!userScrolledRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
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

  const handleNewMission = async () => {
    await ZenithService.stopAgent();
    await ZenithService.sendSystemCmd('clear_stop');
    reset();
    clearTrace();
    setGoal('');
    wasAtBottom.current = true;
    toast.success('Neural environment reset complete.', { id: 'ZENITH_PULSE' });
  };

  const handleLoadMission = async (id: string) => {
    const loadingToast = toast.loading('Đang khôi phục ngữ cảnh...', { id: 'ZENITH_PULSE' });
    try {
      const data = await ZenithService.getMission(id);
      loadMissionData(data);
      wasAtBottom.current = true;
      setShowHistory(false);
      toast.success('Neural records loaded!', { id: 'ZENITH_PULSE' });
    } catch {
      toast.error('Lỗi khi tải dữ liệu', { id: 'ZENITH_PULSE' });
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
          handleNewMission();
        }
      } else {
        handleNewMission();
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
              className="absolute inset-0 z-40 bg-[#060910] flex flex-col border-l border-white/10 shadow-2xl"
            >
              <div className="flex items-center justify-between p-6 border-b border-white/5">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.1)]">
                      <Archive className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                      <h3 className="text-sm font-black text-white uppercase tracking-[0.2em]">Mission History</h3>
                      <p className="text-[10px] text-amber-500/40 font-bold uppercase tracking-widest">Lịch sử nhiệm vụ</p>
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
              <div className="flex-1 overflow-y-auto p-4 custom-scroll space-y-3">
                {missions.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center opacity-10 gap-4">
                    <Database className="w-10 h-10" />
                    <span className="text-[10px] font-black uppercase tracking-widest">No Missions Recorded</span>
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
            className="absolute inset-0 overflow-y-auto px-6 pt-6 space-y-6 custom-scroll scroll-smooth"
            style={{ paddingBottom: '40px' }}
          >
            {visibleLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-[0.08] gap-5">
                <Brain className="w-20 h-20 text-white" strokeWidth={1} />
                <p className="text-[11px] font-black uppercase tracking-[0.8em]">{dict.awaiting}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-6 pb-20">
                {(() => {
                  const elements: React.ReactNode[] = [];
                  
                  // Nếu không tìm thấy bất kỳ câu trả lời nào, hiện list log và trace ở đáy
                  if (firstAnswerIndex === -1) {
                    visibleLogs.forEach((l: any, i: number) => {
                      elements.push(<LogItem key={l.id || i} l={l} forceReasoning={streamView === 'full'} />);
                    });
                    elements.push(
                      <div key="exec-trace-holder" className="flex flex-col gap-1.5 px-2 py-1">
                        <ExecutionTrace />
                      </div>
                    );
                  } else {
                    // Nếu đã có câu trả lời, chèn trace NGAY TRƯỚC câu trả lời đó
                    visibleLogs.forEach((l: any, i: number) => {
                      if (i === firstAnswerIndex) {
                        elements.push(
                          <div key="exec-trace-holder" className="flex flex-col gap-1.5 px-2 py-1">
                            <ExecutionTrace />
                          </div>
                        );
                      }
                      elements.push(<LogItem key={l.id || i} l={l} forceReasoning={streamView === 'full'} />);
                    });
                  }

                  return elements;
                })()}

                {status === 'running' && (
                  <div className="flex flex-col gap-1.5 px-2 py-1">
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-sky-500/5 border border-sky-500/10 backdrop-blur-sm w-fit mt-1"
                    >
                      <Zap className="w-3 h-3 text-sky-400 animate-pulse" />
                      <span className="text-[10px] font-black tracking-widest text-sky-400/80">
                        {dict.processing}
                        <span className="animate-pulse">...</span>
                      </span>
                    </motion.div>
                  </div>
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
                {/* 🧠 [SUPREME-TOGGLE]: Nút chuyển đổi chế độ nhất thể với sắc màu rực rỡ  */}
                <button
                  onClick={() => {
                    const modes: CognitiveMode[] = ['auto', 'fast', 'deep'];
                    const nextMode = modes[(modes.indexOf(cognitiveMode) + 1) % modes.length];
                    setMode(nextMode);
                  }}
                  className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all duration-500 shadow-lg border ${cognitiveMode === 'auto' ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 shadow-cyan-500/20 shadow-[0_0_15px_rgba(34,211,238,0.2)]' :
                    cognitiveMode === 'fast' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 shadow-emerald-500/20 shadow-[0_0_15px_rgba(52,211,153,0.2)]' :
                      'bg-amber-500/20 text-amber-400 border-amber-500/40 shadow-amber-500/20 shadow-[0_0_15px_rgba(251,191,36,0.2)]'
                    }`}
                >
                  <div className="flex items-center gap-2">
                    <Zap className={`w-3.5 h-3.5 ${cognitiveMode === 'auto' ? 'text-cyan-400' :
                      cognitiveMode === 'fast' ? 'text-emerald-400' :
                        'text-amber-400'
                      }`} />
                    <span>{cognitiveMode}</span>
                  </div>
                </button>

                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className={`p-3 rounded-xl transition-all ${showHistory ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-white/5 text-white/20 hover:text-white/40 border border-transparent'}`}
                >
                  <History className="w-[20px] h-[20px]" />
                </button>

                <button
                  onClick={status === 'running' ? () => { stopAgent(); setStatus('idle'); } : () => runAgent()}
                  className={`p-3 rounded-xl transition-all shadow-xl ${status === 'running'
                    ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    : 'bg-sky-500 text-white hover:scale-105 active:scale-95 shadow-sky-500/20'
                    }`}
                >
                  {status === 'running' ? <Square className="w-[20px] h-[20px]" /> : <Send className="w-[20px] h-[20px]" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});
