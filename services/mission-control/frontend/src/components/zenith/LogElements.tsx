import React, { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Zap, FileCode2, Terminal, ChevronRight, ChevronDown, Search, FileText, Loader2, GitCommit, Clock } from 'lucide-react';
import { useZenithStore } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';
import { MarkdownRenderer } from './MarkdownRenderer';

// ── FileEditRow: "Edited file.py  +118  -26" kiểu Antigravity ─────────────
interface FileEditRowProps {
  filePath: string;
  fileName: string;
  added: number;
  removed: number;
  diff: string;
  onInspect: () => void;
}

export const FileEditRow = memo(({ filePath, fileName, added, removed, diff, onInspect }: FileEditRowProps) => {
  const [expanded, setExpanded] = useState(false);
  const language = useZenithStore(s => s.language);

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="my-1 ml-14 font-sans w-fit max-w-[95%]"
    >
      {/* ── Header row ── */}
      <div className="flex items-center gap-2 group/row select-none">
        {/* Toggle expand */}
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-white/25 hover:text-white/60 transition-colors"
        >
          {expanded
            ? <ChevronDown className="w-3 h-3" />
            : <ChevronRight className="w-3 h-3" />}
        </button>

        {/* File icon */}
        <FileCode2 className="w-3.5 h-3.5 text-sky-400/70 shrink-0" />

        {/* Filename — clickable to open */}
        <button
          onClick={onInspect}
          className="text-[12.5px] font-medium text-white/60 hover:text-sky-300 transition-colors font-mono leading-none"
        >
          {fileName}
        </button>

        {/* +added badge */}
        {added > 0 && (
          <span className="text-[11px] font-bold font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded leading-none">
            +{added}
          </span>
        )}

        {/* -removed badge */}
        {removed > 0 && (
          <span className="text-[11px] font-bold font-mono text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded leading-none">
            -{removed}
          </span>
        )}
      </div>

      {/* ── Collapsible diff ── */}
      <AnimatePresence>
        {expanded && diff && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mt-2"
          >
            <SurgicalDiff diff={diff} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
});

// ── WorkingDots: spinner nhỏ "Working..." không chiếm chỗ ─────────────────
export const WorkingDots = memo(({ label }: { label?: string }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="ml-14 my-1.5 flex items-center gap-1.5 text-white/30"
  >
    <Loader2 className="w-3 h-3 animate-spin" />
    <span className="text-[11.5px] font-normal">{label || 'Working...'}</span>
  </motion.div>
));

export const MicroscopeIcon = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 18h8" /><path d="M3 22h18" /><path d="M14 22a7 7 0 1 0 0-14h-1" /><path d="M9 14h2" /><path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z" /><path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3" /></svg>
);

export const ToolBlock = memo(({ msg }: { msg: string }) => {
  const safeMsg = msg || '';
  const isRead = safeMsg.toLowerCase().includes('read') || safeMsg.toLowerCase().includes('view');
  const isWrite = safeMsg.toLowerCase().includes('write') || safeMsg.toLowerCase().includes('patch') || safeMsg.toLowerCase().includes('create');
  const icon = isWrite ? <FileCode2 className="w-3.5 h-3.5" /> : isRead ? <MicroscopeIcon className="w-3.5 h-3.5" /> : <Terminal className="w-3.5 h-3.5" />;
  const color = isWrite ? 'text-amber-400 border-amber-500/20 bg-amber-500/5' : isRead ? 'text-sky-400 border-sky-500/20 bg-sky-500/5' : 'text-purple-400 border-purple-500/20 bg-purple-500/5';
  const label = isWrite ? 'CẬP NHẬT DỮ LIỆU' : isRead ? 'PHÂN TÍCH DỮ LIỆU' : 'THỰC THI HỆ THỐNG';
  return (
    <div className={`my-2 p-2 rounded-xl border flex flex-col gap-1.5 ${color} font-mono text-[12px]`}>
      <div className="flex items-center gap-1.5 font-black uppercase tracking-tighter opacity-70">{icon} <span>{label}</span></div>
      <div className="bg-black/30 p-1.5 rounded-lg break-all opacity-90 leading-tight">{safeMsg.replace(/Tool result:|Tool call:/gi, '').trim()}</div>
    </div>
  );
});

export const SurgicalDiff = memo(({ diff }: { diff: string }) => {
  const lines = diff.split('\n');
  return (
    <div className="my-4 rounded-xl border border-white/10 bg-black/40 overflow-hidden font-mono text-[11px] shadow-2xl">
      <div className="px-4 py-2 bg-white/[0.03] border-b border-white/5 flex items-center justify-between">
        <span className="text-[9px] font-black uppercase tracking-widest text-white/30">Surgical Diff View</span>
        <div className="flex gap-1">
          <div className="w-1 h-1 rounded-full bg-emerald-500/50" />
          <div className="w-1 h-1 rounded-full bg-rose-500/50" />
        </div>
      </div>
      <div className="p-4 space-y-0.5 overflow-x-auto custom-scroll max-h-[300px]">
        {lines.map((line, i) => {
          const isAdd = line.startsWith('+');
          const isRem = line.startsWith('-');
          return (
            <div key={i} className={`flex gap-4 px-2 py-0.5 rounded ${isAdd ? 'bg-emerald-500/10 text-emerald-400' : isRem ? 'bg-rose-500/10 text-rose-400' : 'text-white/40'}`}>
              <span className="w-6 shrink-0 opacity-20 select-none text-right">{i + 1}</span>
              <span className="shrink-0 w-3 opacity-50">{isAdd ? '+' : isRem ? '-' : ' '}</span>
              <span className="whitespace-pre">{line.startsWith('+') || line.startsWith('-') ? line.slice(1) : line}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
});

export const ActionBadge = memo(({ label, rawMsg, onClick }: { label: string, rawMsg?: string, onClick?: () => void | Promise<void> }) => {
  const [isOpen, setIsOpen] = useState(false);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const language = useZenithStore(s => s.language);

  const msg = rawMsg || label;
  const isEditing = msg.toLowerCase().includes('edit') || msg.toLowerCase().includes('patch') || msg.toLowerCase().includes('writ') || msg.toLowerCase().includes('sửa') || msg.toLowerCase().includes('ghi');
  const isExploring = msg.toLowerCase().includes('view') || msg.toLowerCase().includes('analyz') || msg.toLowerCase().includes('explor') || msg.toLowerCase().includes('read') || msg.toLowerCase().includes('phân tích') || msg.toLowerCase().includes('đọc');
  const isSearching = msg.toLowerCase().includes('search') || msg.toLowerCase().includes('find') || msg.toLowerCase().includes('grep') || msg.toLowerCase().includes('tìm');

  // Phân tích tên file từ msg
  const fileRegex = /([a-zA-Z0-9_\-\.\/]+\.[a-z0-9]+)/i;
  const match = msg.match(fileRegex);
  const filePath = match ? match[0].replace(/[`"']/g, '') : '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Phân tích line range (nếu có, e.g. #L123-145)
  const lineMatch = msg.match(/(?:#L|line\s*)(\d+)(?:-(\d+))?/i);
  const lineInfo = lineMatch ? `#L${lineMatch[1]}${lineMatch[2] ? `-${lineMatch[2]}` : ''}` : '';

  // Xác định label chính
  let mainLabel = language === 'vi' ? 'Đang thực thi...' : 'Working...';
  if (isEditing) {
    mainLabel = language === 'vi' ? `Cập nhật ${fileName || 'tệp'}` : `Refactored ${fileName || 'file'}`;
  } else if (isExploring) {
    mainLabel = language === 'vi' ? `Khảo sát ${fileName || 'tệp'}` : `Exploring ${fileName || 'file'}`;
  } else if (isSearching) {
    mainLabel = language === 'vi' ? 'Tìm kiếm mã nguồn' : 'Searching codebase';
  }

  const handleInspect = async () => {
    if (!filePath) return;
    try {
      const data = await ZenithService.readFile(filePath);
      if (data?.content) {
        setInspectedFile({ path: filePath, content: data.content });
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    setIsOpen(!isOpen);
    if (onClick) {
      onClick();
    } else if (filePath) {
      handleInspect();
    }
  };

  return (
    <div className="my-1.5 ml-14 font-sans text-[12.5px] w-fit max-w-[95%]">
      {/* Minimalist Header resembling Cursor style */}
      <div 
        onClick={handleClick}
        className="flex items-center gap-1 text-white/40 hover:text-cyan-400 cursor-pointer select-none transition-colors py-0.5 group/badge"
      >
        {isOpen ? <ChevronDown className="w-3.5 h-3.5 opacity-60" /> : <ChevronRight className="w-3.5 h-3.5 opacity-60" />}
        <span className="font-normal transition-colors group-hover/badge:text-cyan-300">{mainLabel}</span>
        {lineInfo && <span className="opacity-40 text-[10.5px] font-mono ml-0.5">{lineInfo}</span>}
      </div>

      {/* Collapsible Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden bg-white/[0.01] border-l border-white/5 pl-3.5 ml-1.5 mt-1 flex flex-col gap-1.5"
          >
            <div className="text-white/30 font-mono leading-relaxed text-[11px] break-all">
              {msg}
            </div>
            {filePath && (
              <div 
                onClick={handleInspect}
                className="flex items-center gap-1.5 text-sky-400/70 hover:text-sky-300 cursor-pointer text-[10.5px] font-bold"
              >
                <FileText className="w-3 h-3" />
                <span className="underline">{language === 'vi' ? `Mở ${fileName}` : `Open ${fileName}`}</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

export const ReasoningBlock = memo(({ tag, msg, duration }: { tag: string, msg: string, duration?: number }) => {
  const language = useZenithStore(s => s.language);
  const safeTag = tag || '';
  const roleRaw = (safeTag.includes(':') ? safeTag.split(':')[1] : safeTag).trim();
  const roleUpper = roleRaw.toUpperCase();
  const tagUpper = safeTag.toUpperCase();
  
  const isImportant = roleUpper === 'MASTER' || roleUpper === 'DISPATCHER' || roleUpper === 'GATEWAY' || roleUpper === 'ERROR' || roleUpper === 'CRITIC' || tagUpper === 'PROGRESS' || tagUpper.includes('THOUGHT') || tagUpper.includes('PLANNING') || tagUpper.includes('TƯ DUY');
  
  let color = 'text-cyan-400';
  let displayRole = roleRaw;
  let bgClass = 'bg-cyan-500/[0.02] border-cyan-500/10';
  
  const isZenith = (msg && (msg.includes('ZENITH') || msg.includes('💎🫡'))) || (tag && tag.includes('ZENITH'));

  if (roleUpper.includes('GATEWAY') || roleUpper.includes('RECEPTIONIST') || isZenith) { 
    color = "text-emerald-400"; displayRole = 'Ban Trợ Lý'; bgClass = 'bg-emerald-500/[0.02] border-emerald-500/10';
  } else if (roleUpper.includes('PLANNER') || roleUpper.includes('THOUGHT')) { 
    color = "text-indigo-400"; displayRole = 'Ban Kế Hoạch'; bgClass = 'bg-indigo-500/[0.02] border-indigo-500/10';
  } else if (roleUpper.includes('EXECUTOR') || roleUpper.includes('ALPHA') || roleUpper.includes('BETA') || roleUpper === 'PROGRESS' || roleUpper === 'TIẾN TRÌNH' || roleUpper === 'TIẾN_TRÌNH') { 
    color = "text-blue-400"; displayRole = 'Ban Thực Thi'; bgClass = 'bg-blue-500/[0.02] border-blue-500/10';
  } else if (roleUpper === 'JKAI' || roleUpper === 'MISSION_RESULT' || roleUpper === 'RESULT' || roleUpper === 'DONE') {
    color = "text-cyan-400"; displayRole = 'JKAI'; bgClass = 'bg-cyan-500/[0.02] border-cyan-500/10';
  } else if (roleUpper.includes('SUMMARIZER') || roleUpper.includes('SYNTHESIS') || roleUpper.includes('LEGAL') || roleUpper.includes('THU_KY')) { 
    color = "text-fuchsia-400"; displayRole = 'Ban Thư Ký'; bgClass = 'bg-fuchsia-500/[0.02] border-fuchsia-500/10';
  } else if (roleUpper.includes('CRITIC') || roleUpper.includes('AUDIT') || roleUpper.includes('REVIEW') || roleUpper.includes('GUARDRAIL')) { 
    color = "text-rose-400"; displayRole = 'Ban Kiểm Soát'; bgClass = 'bg-rose-500/[0.02] border-rose-500/10';
  } else if (
    roleUpper.includes('DATA_SCOUT') || roleUpper.includes('RESEARCH') || roleUpper.includes('SEARCH') || 
    roleUpper.includes('ANTIGRAVITY') || roleUpper.includes('FORGE') ||
    roleUpper.includes('CREATOR') || roleUpper.includes('KIẾN TẠO') || roleUpper.includes('KIENTAO') || 
    roleUpper.includes('TÌNH BÁO') || roleUpper.includes('TINHBAO')
  ) { 
    color = "text-sky-400"; displayRole = 'Ban Hành Chính'; bgClass = 'bg-sky-500/[0.02] border-sky-500/10';
  } else if (roleUpper === 'MASTER' || roleUpper.includes('MASTER') || roleUpper.includes('USER')) { 
    color = "text-amber-400"; displayRole = 'Master'; bgClass = 'bg-amber-500/[0.02] border-amber-500/10';
  } else {
    color = "text-sky-400"; displayRole = 'Ban Hành Chính'; bgClass = 'bg-sky-500/[0.02] border-sky-500/10';
  }

  let cleanMsg = msg;
  if (!tagUpper.includes('PROGRESS') && !tagUpper.includes('EXECUTOR')) {
    cleanMsg = msg.replace(/^(?:[^\w\s]*)\s*\[(DEBUG|TRACE|LOG|INFO|SYS)\]:\s*/g, '').trim();
  }
  
  cleanMsg = cleanMsg.replace(/^Đang /i, 'Đang ').replace(/^Đã /i, 'Đã ');

  return (
    <div className={`my-2 p-2.5 rounded-xl border ${bgClass} leading-relaxed transition-all hover:bg-white/[0.01]`}>
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`text-[9.5px] font-black uppercase tracking-wider ${color}`}>{displayRole}</span>
        {duration !== undefined ? (
          <span className="text-[10px] font-mono text-sky-400/85 bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
            <Clock className="w-3 h-3 text-sky-400 opacity-80" />
            <span>{language === 'vi' ? `Đã tư duy ${duration}s` : `Thought for ${duration}s`}</span>
          </span>
        ) : (
          <span className="text-[8.5px] px-1.5 py-0.5 rounded-full bg-white/5 text-white/40 font-mono">
            {language === 'vi' ? 'TƯ DUY CHIẾN THUẬT' : 'STRATEGIC REASONING'}
          </span>
        )}
      </div>
      <div className={`text-[12px] font-medium leading-relaxed font-mono ${isImportant ? 'text-white/80' : 'text-slate-400'}`}>
        <MarkdownRenderer content={cleanMsg || msg} />
      </div>
    </div>
  );
});
