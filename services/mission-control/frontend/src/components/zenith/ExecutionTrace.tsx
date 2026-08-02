import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, Brain, Terminal, Loader2, CheckCircle2, Clock, Activity } from 'lucide-react';
import { useZenithStore, TraceItem } from '../../store/zenithStore';

const formatTime = (ts: number): string => {
  try {
    const d = new Date(ts < 1e12 ? ts * 1000 : ts);
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return ''; }
};

// ─── SUB-COMPONENT: THOUGHT TRACE ITEM ───────────────────────────────────────
interface ThoughtTraceItemProps {
  item: TraceItem;
  isLatest: boolean;
  systemStatus: string;
}

const ThoughtTraceItem: React.FC<ThoughtTraceItemProps> = ({ item, isLatest, systemStatus }) => {
  const language = useZenithStore(s => s.language);
  const [seconds, setSeconds] = useState<number>(() => {
    if ((item as any).duration) return (item as any).duration;
    const elapsed = Math.floor((Date.now() - item.ts) / 1000);
    return Math.max(0, elapsed);
  });
  const [isExpanded, setIsExpanded] = useState(false);
  const isActive = isLatest && systemStatus === 'running' && !(item as any).duration;

  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      setSeconds((prev: number) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isActive]);

  const thinkingText = language === 'vi' ? 'đang tư duy' : 'thinking';

  return (
    <div className="flex flex-col gap-1 w-full font-mono text-[11px] text-white/70">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-white/60 hover:text-white/90 transition-colors w-full cursor-pointer text-left font-mono"
      >
        <span className="text-[9px] text-white/20 font-mono tabular-nums w-[62px] shrink-0">{formatTime(item.ts)}</span>
        <Brain className="w-3 h-3 text-sky-400 shrink-0" />
        <span className="flex-1 truncate select-text">{item.label}</span>
        <span className="text-white/30 text-[9px] ml-auto shrink-0 font-normal">
          ({isActive ? `${thinkingText} ${seconds}s` : `${seconds}s`})
        </span>
        {isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-white/30 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30 shrink-0" />}
      </button>
      
      {isExpanded && item.detail && (
        <div className="pl-6 mt-1 border-l border-white/10 text-white/40 leading-relaxed break-all bg-white/[0.01] rounded max-w-[95%] py-1">
          {item.detail}
        </div>
      )}
    </div>
  );
};

// ─── SUB-COMPONENT: FILE TRACE ITEM ──────────────────────────────────────────
interface FileTraceItemProps {
  item: TraceItem;
}

const FileTraceItem: React.FC<FileTraceItemProps> = ({ item }) => {
  const language = useZenithStore(s => s.language);
  const { fileName, lineSuffix } = useMemo(() => {
    const cleanLabel = (item.label || '').replace(/`/g, '');
    const lineMatch = cleanLabel.match(/(.*)(?::|#)(L\d+(?:-\d+)?)$/i) || cleanLabel.match(/(.*)(L\d+(?:-\d+)?)$/i);
    
    let filePath = cleanLabel;
    let lineSuffix = "";
    
    if (lineMatch) {
      filePath = lineMatch[1].trim();
      lineSuffix = lineMatch[2].trim();
    }
    
    const parts = filePath.split(/[/\\]/);
    const fileName = parts[parts.length - 1] || filePath;
    
    return { fileName, lineSuffix };
  }, [item.label]);

  const actionText = item.type === 'folder' 
    ? (language === 'vi' ? 'Đã liệt kê' : 'Listed') 
    : (language === 'vi' ? 'Đã phân tích' : 'Analyzed');

  return (
    <div className="flex items-center gap-2 group w-full min-w-0 font-mono text-[11px] text-white/70">
      <span className="text-[9px] text-white/20 font-mono tabular-nums w-[62px] shrink-0">{formatTime(item.ts)}</span>
      <span className="text-white/50 shrink-0">{actionText}</span>
      <span className="shrink-0">⚛️</span>
      <span 
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
        className="font-bold cursor-pointer hover:underline truncate"
      >
        {fileName}{lineSuffix && <span className="text-white/40 font-normal">#{lineSuffix}</span>}
      </span>
    </div>
  );
};

// ─── SUB-COMPONENT: SEARCH TRACE ITEM ────────────────────────────────────────
interface SearchTraceItemProps {
  item: TraceItem;
}

const SearchTraceItem: React.FC<SearchTraceItemProps> = ({ item }) => {
  const language = useZenithStore(s => s.language);
  const { query, resultsCount } = useMemo(() => {
    const rawLabel = item.label || '';
    const tavilyMatch = rawLabel.match(/TAVILY[^:]*:\s*Initiating[^"'`]*["'`]([^"'`]+)["'`]/i) ||
                       rawLabel.match(/TAVILY[^:]*:\s*Initiating[^f]*for\s+(.+)/i);
    const match = tavilyMatch ||
                  rawLabel.match(/searching (?:for\s+)?["'`]([^"'`]+)["'`]/i) || 
                  rawLabel.match(/searching (?:for\s+)?(.*)/i) ||
                  rawLabel.match(/`([^`]+)`/) ||
                  [null, rawLabel];
    
    const query = (match[1] || rawLabel).trim();
    
    let resultsCount = 0;
    const countMatch = (item.detail || '').match(/(\d+)\s+results/i) || 
                       rawLabel.match(/(\d+)\s+results/i) ||
                       (item.detail || '').match(/found\s+(\d+)/i) ||
                       (item.detail || '').match(/Discovered\s+(\d+)/i);
    if (countMatch) {
      resultsCount = parseInt(countMatch[1]);
    }

    return { query, resultsCount };
  }, [item.label, item.detail]);

  const searchedText = language === 'vi' ? 'Đã tìm kiếm' : 'Searched';
  const resultsText = language === 'vi' ? 'kết quả' : 'results';

  return (
    <div className="flex items-center gap-2 w-full min-w-0 font-mono text-[11px] text-white/70">
      <span className="text-[9px] text-white/20 font-mono tabular-nums w-[62px] shrink-0">{formatTime(item.ts)}</span>
      <span className="text-white/50 shrink-0">{searchedText}</span>
      <span className="truncate">"{query}"</span>
      {resultsCount > 0 && (
        <span className="text-white/40 shrink-0 bg-white/5 px-1.5 py-0.5 rounded">
          {resultsCount} {resultsText}
        </span>
      )}
    </div>
  );
};

// ─── SUB-COMPONENT: COMMAND TRACE ITEM ───────────────────────────────────────
interface CommandTraceItemProps {
  item: TraceItem;
}

const CommandTraceItem: React.FC<CommandTraceItemProps> = ({ item }) => {
  const language = useZenithStore(s => s.language);
  const executedText = language === 'vi' ? 'Đã thực thi' : 'Executed';

  return (
    <div className="flex items-center gap-2 group w-full min-w-0 font-mono">
      <span className="text-[9px] text-white/20 font-mono tabular-nums w-[62px] shrink-0">{formatTime(item.ts)}</span>
      <Terminal className="w-3 h-3 text-rose-400/60 shrink-0" />
      <span className="text-[10px] font-medium text-white/30 shrink-0">{executedText}</span>
      <span className="text-[10px] font-bold text-rose-300/80 truncate select-all bg-rose-500/5 px-1.5 py-0.5 rounded border border-rose-500/10">
        {item.label}
      </span>
    </div>
  );
};

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────
export const ExecutionTrace: React.FC = () => {
  const executionTrace = useZenithStore(s => s.executionTrace);
  const setTraceExpanded = useZenithStore(s => s.setTraceExpanded);
  const status = useZenithStore(s => s.status);
  const language = useZenithStore(s => s.language);
  const { items, isExpanded, lastUpdate } = executionTrace;

  // 🛡️ [AUTO-COLLAPSE]: Tự động thu nhỏ sau 1 phút không có hoạt động mới
  useEffect(() => {
    if (!isExpanded || items.length === 0 || status !== 'running') return;
    
    const timer = setTimeout(() => {
      setTraceExpanded(false);
    }, 60000);

    return () => clearTimeout(timer);
  }, [lastUpdate, isExpanded, items.length, status, setTraceExpanded]);

  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const finalElapsedRef = useRef<number>(0);

  // Live timer for ongoing missions
  useEffect(() => {
    if (status === 'running') {
      finalElapsedRef.current = 0;
      intervalRef.current = setInterval(() => {
        const currentElapsed = Date.now() - (executionTrace.startTime || Date.now());
        setElapsed(currentElapsed);
        finalElapsedRef.current = currentElapsed;
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (finalElapsedRef.current === 0 && executionTrace.startTime) {
        finalElapsedRef.current = Date.now() - executionTrace.startTime;
      }
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [status, executionTrace.startTime]);

  const firstTs = items.length > 0 ? formatTime(items[0].ts) : '';
  const lastTs = items.length > 0 ? formatTime(items[items.length - 1].ts) : '';

  const summary = useMemo(() => {
    const files = items.filter(i => i.type === 'file' || i.type === 'folder').length;
    const folders = items.filter(i => i.type === 'folder').length;
    const searches = items.filter(i => i.type === 'search').length;
    
    const parts = [];
    if (files) parts.push(`${files} ${language === 'vi' ? 'tệp' : 'files'}`);
    if (folders) parts.push(`${folders} ${language === 'vi' ? 'thư mục' : 'folders'}`);
    if (searches) parts.push(`${searches} ${language === 'vi' ? 'lượt tìm' : 'searches'}`);
    
    const statsStr = parts.length > 0 ? parts.join(', ') : (language === 'vi' ? 'hệ thống' : 'system');
    
    if (status === 'running') {
      return `${language === 'vi' ? 'Đang khám phá' : 'Exploring'} ${statsStr} — ${firstTs}`;
    }
    return `${language === 'vi' ? 'Đã khám phá' : 'Explored'} ${statsStr} — ${firstTs} → ${lastTs}`;
  }, [items, status, firstTs, lastTs, language]);

  if (items.length === 0) return null;

  const activeStreamLabel = language === 'vi' 
    ? 'Hệ thống luồng truy vết hoạt động' 
    : 'System Trace Stream Active';

  return (
    <div className="flex flex-col gap-2 mb-4 px-2">
      {/* ─── Header Line ─── */}
      <button 
        onClick={() => setTraceExpanded(!isExpanded)}
        className="flex items-center gap-2.5 text-[11px] font-semibold text-white/50 hover:text-white/70 transition-colors group cursor-pointer"
      >
        <span className="opacity-60 group-hover:opacity-100 transition-opacity">
          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </span>
        {status === 'running' ? (
          <Activity className="w-3 h-3 text-emerald-400 animate-pulse shrink-0" />
        ) : (
          <Clock className="w-3 h-3 text-white/20 shrink-0" />
        )}
        <span className="flex-1 text-left truncate tracking-tight font-mono">{summary}</span>
        {status === 'running' && <Loader2 className="w-3 h-3 animate-spin text-sky-500/50" />}
      </button>

      {/* ─── Trace Items ─── */}
      <AnimatePresence>
        {isExpanded && items.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden flex flex-col gap-2 pl-6 border-l border-white/[0.03] ml-1.5"
          >
            {items.map((item, idx) => {
              const typedItem = item as TraceItem;
              const isLatestThought = typedItem.type === 'thought' && 
                                      items.filter(it => it.type === 'thought').pop()?.id === typedItem.id;
              
              return (
                <motion.div
                  key={typedItem.id}
                  initial={{ x: -10, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: idx * 0.05 }}
                  className="flex items-center gap-3 group min-w-0"
                >
                  {typedItem.type === 'thought' ? (
                    <ThoughtTraceItem item={typedItem} isLatest={isLatestThought} systemStatus={status} />
                  ) : typedItem.type === 'file' ? (
                    <FileTraceItem item={typedItem} />
                  ) : typedItem.type === 'search' ? (
                    <SearchTraceItem item={typedItem} />
                  ) : (
                    <CommandTraceItem item={typedItem} />
                  )}
                  
                  {typedItem.type !== 'thought' && typedItem.status === 'completed' && (
                    <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500/20 shrink-0 ml-auto" />
                  )}
                </motion.div>
              );
            })}
            
            {/* System Trace Stream Line representation */}
            <div className="text-[8px] font-mono text-white/10 uppercase tracking-widest text-center mt-1 border-t border-dashed border-white/[0.02] pt-2">
              ─── {activeStreamLabel} ───
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
