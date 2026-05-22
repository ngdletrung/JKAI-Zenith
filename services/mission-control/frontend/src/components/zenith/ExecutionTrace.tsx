import React, { useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, FileText, Folder, Search, Brain, Terminal, Loader2, CheckCircle2 } from 'lucide-react';
import { useZenithStore, TraceItem } from '../../store/zenithStore';

export const ExecutionTrace: React.FC = () => {
  const executionTrace = useZenithStore(s => s.executionTrace);
  const setTraceExpanded = useZenithStore(s => s.setTraceExpanded);
  const status = useZenithStore(s => s.status);
  const { items, isExpanded, lastUpdate } = executionTrace;

  // 🛡️ [AUTO-COLLAPSE]: Tự động thu nhỏ sau 1 phút không có hoạt động mới
  useEffect(() => {
    if (!isExpanded || items.length === 0 || status !== 'running') return;
    
    const timer = setTimeout(() => {
      setTraceExpanded(false);
    }, 60000); // 60 giây

    return () => clearTimeout(timer);
  }, [lastUpdate, isExpanded, items.length, status, setTraceExpanded]);

  const summary = useMemo(() => {
    const files = items.filter(i => i.type === 'file').length;
    const folders = items.filter(i => i.type === 'folder').length;
    const searches = items.filter(i => i.type === 'search').length;
    
    const parts = [];
    if (files) parts.push(`${files} files`);
    if (folders) parts.push(`${folders} folder`);
    if (searches) parts.push(`${searches} searches`);
    
    return parts.length > 0 ? `Exploring ${parts.join(', ')}` : 'Initiating neural trace...';
  }, [items]);

  if (items.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mb-4 px-2">
      {/* ─── Header Line ─── */}
      <button 
        onClick={() => setTraceExpanded(!isExpanded)}
        className="flex items-center gap-2 text-[11px] font-bold text-white/40 hover:text-white/60 transition-colors group"
      >
        <span className="opacity-0 group-hover:opacity-100 transition-opacity">
          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </span>
        <span className="flex-1 text-left truncate tracking-tight">{summary}</span>
        {status === 'running' && <Loader2 className="w-3 h-3 animate-spin text-sky-500/50" />}
      </button>

      {/* ─── Trace Items ─── */}
      <AnimatePresence>
        {isExpanded && items.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden flex flex-col gap-1.5 pl-6 border-l border-white/[0.03] ml-1.5"
          >
            {items.map((item, idx) => (
              <motion.div
                key={item.id}
                initial={{ x: -10, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: idx * 0.05 }}
                className="flex items-center gap-3 group"
              >
                <div className="shrink-0">
                  {item.type === 'file' && <FileText className="w-3.5 h-3.5 text-sky-400/40" />}
                  {item.type === 'folder' && <Folder className="w-3.5 h-3.5 text-amber-400/40" />}
                  {item.type === 'search' && <Search className="w-3.5 h-3.5 text-emerald-400/40" />}
                  {item.type === 'thought' && <Brain className="w-3.5 h-3.5 text-purple-400/40" />}
                  {item.type === 'command' && <Terminal className="w-3.5 h-3.5 text-rose-400/40" />}
                </div>
                
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-medium text-white/30 tracking-tight truncate">
                      {item.type === 'file' || item.type === 'folder' ? 'Analyzed' : 
                       item.type === 'search' ? 'Searched' : 
                       item.type === 'thought' ? 'Thought' : 'Executed'}
                    </span>
                    <span 
                      className="text-[10px] font-bold text-white/60 truncate group-hover:text-sky-400/80 transition-colors cursor-pointer"
                      onClick={() => {
                        if (item.logId) {
                          // 🚀 [SMART-NAVIGATION]: Chuyển sang tab Tiến trình và cuộn đến
                          useZenithStore.getState().setTab('progress');
                          setTimeout(() => {
                            const el = document.getElementById(`log-${item.logId}`);
                            if (el) {
                              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                              el.classList.add('bg-sky-500/10');
                              setTimeout(() => el.classList.remove('bg-sky-500/10'), 2000);
                            }
                          }, 100);
                        }
                      }}
                    >
                      {item.label}
                    </span>
                    {item.status === 'completed' && <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500/20" />}
                  </div>
                  {item.detail && (
                    <span 
                      className="text-[9.5px] text-white/40 line-clamp-3 leading-relaxed mt-0.5 cursor-pointer hover:text-white/60"
                      onClick={() => {
                        if (item.logId) {
                          useZenithStore.getState().setTab('progress');
                          setTimeout(() => {
                            const el = document.getElementById(`log-${item.logId}`);
                            if (el) {
                              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                              el.classList.add('bg-sky-500/10');
                              setTimeout(() => el.classList.remove('bg-sky-500/10'), 2000);
                            }
                          }, 100);
                        }
                      }}
                    >
                      {item.detail}
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
