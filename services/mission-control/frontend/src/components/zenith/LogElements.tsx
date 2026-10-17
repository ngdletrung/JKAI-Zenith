import React, { memo, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Zap, FileCode2, Terminal, ChevronRight, ChevronDown, Search, FileText, Loader2, GitCommit, Clock, CheckCircle2, Globe, ShieldCheck } from 'lucide-react';
import { useZenithStore, AgentLog } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';
import { MarkdownRenderer } from './MarkdownRenderer';

// ── Helper: Loại bỏ hoàn toàn siêu dữ liệu log backend thô ──────────────────
export const stripLogMetadata = (raw: string): string => {
  if (!raw) return '';
  let text = raw;
  // 1. Loại bỏ tag thời lượng [⏱ 12.3s] hoặc [⏱️ 12.3s]
  text = text.replace(/\[(?:⏱️|⏱)\s*[\d.]+\s*s\]/gi, '');
  // 2. Lặp để bóc sạch mọi block ngoặc vuông header rác ở đầu chuỗi:
  // Ví dụ: [INFO] [17/10/2026 13:26:56.284793] [RECEPTIONIST] [Task: ZENITH_1710-1326_bc8922]
  // hoặc [INFO] [2026-10-17T06:28:00.472137] [SUMMARIZER] [Task: omni_synthesis_fast]
  const headerBlockRegex = /^\s*\[(INFO|WARN|WARNING|ERROR|DEBUG|TRACE|SYS|SYSTEM|RECEPTIONIST|SUMMARIZER|PLANNER|CRITIC|EXECUTOR|BOT|JKAI|\d{1,4}[\/\-:T]\S*|Task:\s*[^\]]+)\]:?\s*/i;
  let prev = '';
  while (prev !== text && headerBlockRegex.test(text)) {
    prev = text;
    text = text.replace(headerBlockRegex, '');
  }
  // 3. Nếu còn sót các chuỗi Task hoặc Date dạng [DD/MM/YYYY ...]
  text = text.replace(/^\[Task:\s*[^\]]+\]\s*/i, '');
  text = text.replace(/^\[\d{1,2}\/\d{1,2}\/\d{2,4}[^\]]*\]\s*/i, '');
  text = text.replace(/^\[\d{4}-\d{2}-\d{2}[^\]]*\]\s*/i, '');
  // 4. Bỏ các ký tự phân cách rác ở đầu
  text = text.replace(/^[\s:\-–—]+/, '');
  return text.trim();
};

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

  const raw = (rawMsg || label || '').trim();
  const clean = stripLogMetadata(raw);
  const lower = clean.toLowerCase();

  // 1. Phân loại loại hành động (Action Type)
  const isWebSearch = lower.includes('search_web') || lower.includes('web_search') || lower.includes('tavily') || lower.includes('ddg') || lower.includes('search web for') || lower.includes('tìm kiếm trên web') || lower.includes('tra cứu tri thức');
  const isWebRead = lower.includes('read_url') || lower.includes('browse') || lower.includes('url_content') || clean.includes('http://') || clean.includes('https://');
  const isEditing = lower.includes('edit') || lower.includes('patch') || lower.includes('writ') || lower.includes('sửa') || lower.includes('cập nhật');
  const isExploring = !isWebRead && (lower.includes('view') || lower.includes('read') || lower.includes('analyz') || lower.includes('explor') || lower.includes('khảo sát') || lower.includes('phân tích') || lower.includes('đọc'));
  const isCodeSearch = !isWebSearch && (lower.includes('search') || lower.includes('find') || lower.includes('grep') || lower.includes('tìm kiếm'));
  const isCommand = !isWebSearch && !isWebRead && (lower.includes('command') || lower.includes('exec') || lower.includes('chạy') || lower.includes('thực thi') || lower.includes('pytest') || lower.includes('python'));

  // 2. Trích xuất tên tệp tin và line
  const fileRegex = /([a-zA-Z0-9_\-\.\/]+\.[a-z0-9]+)/i;
  const matchFile = clean.match(fileRegex);
  const filePath = matchFile ? matchFile[0].replace(/[`"']/g, '') : '';
  const fileName = filePath ? filePath.split(/[\/\\]/).pop() || filePath : '';
  const lineMatch = clean.match(/(?:#L|line\s*)(\d+)(?:-(\d+))?/i);
  const lineInfo = lineMatch ? `#L${lineMatch[1]}${lineMatch[2] ? `-${lineMatch[2]}` : ''}` : '';

  // 3. Trích xuất truy vấn tìm kiếm
  let searchQuery = '';
  if (isWebSearch) {
    const webMatch = clean.match(/search web for:?\s*([^\n\r]{2,80})/i) ||
                     clean.match(/cho\s+['"]([^'"]{2,80})['"]/i) ||
                     clean.match(/["'`]([^"'`]{2,80})["'`]/);
    if (webMatch && webMatch[1]) {
      const q = webMatch[1].replace(/[`"']/g, '').trim();
      if (!q.toUpperCase().includes('SEARCH_WEB_GLOBAL')) {
        searchQuery = q;
      }
    }
    if (!searchQuery) {
      const forMatch = clean.match(/(?:for|cho)\s+([^\n\r,.:]{2,60})/i);
      if (forMatch && forMatch[1] && !forMatch[1].toLowerCase().includes('tavily')) {
        searchQuery = forMatch[1].trim();
      }
    }
  } else if (isCodeSearch) {
    const qMatch = clean.match(/["'`]([^"'`]{2,80})["'`]/) || 
                   clean.match(/for\s+["']?([^"'\n\r,]{2,80})["']?/i);
    if (qMatch && qMatch[1]) {
      searchQuery = qMatch[1].replace(/[`"']/g, '').trim();
    }
  }

  // 4. Trích xuất domain / web URL
  let webDomain = '';
  if (isWebRead) {
    const urlMatch = clean.match(/https?:\/\/([^\s\/\)"']+)/i);
    if (urlMatch && urlMatch[1]) {
      webDomain = urlMatch[1].replace(/^www\./i, '');
    }
  }

  // 5. Trích xuất lệnh thực thi (Command Line)
  let cmdLine = '';
  if (isCommand) {
    const cMatch = clean.match(/`([^`]+)`/) || clean.match(/command:?\s*["']?([^"'\n\r]{2,80})["']?/i);
    if (cMatch && cMatch[1]) {
      cmdLine = cMatch[1].trim();
    }
    // Loại bỏ rác [ / ] hoặc các ngoặc rỗng
    cmdLine = cmdLine.replace(/^\[\/?\]$/g, '').trim();
  }

  // 6. Cấu hình Visual & Label theo chuẩn Antigravity
  let actionTitle = language === 'vi' ? 'Đang thực thi' : 'Executing';
  let targetChip = '';
  let ActionIcon = Zap;
  let accentColor = 'sky';
  let borderHover = 'hover:border-sky-500/40';

  if (isWebSearch) {
    actionTitle = language === 'vi' ? 'Tìm kiếm Web' : 'Searched the web';
    targetChip = searchQuery ? `"${searchQuery}"` : '';
    ActionIcon = Search;
    accentColor = 'sky';
    borderHover = 'hover:border-sky-500/40';
  } else if (isWebRead) {
    actionTitle = language === 'vi' ? 'Đọc trang web' : 'Read web page';
    targetChip = webDomain ? webDomain : '';
    ActionIcon = Globe;
    accentColor = 'indigo';
    borderHover = 'hover:border-indigo-500/40';
  } else if (isCodeSearch) {
    actionTitle = language === 'vi' ? 'Tìm trong mã nguồn' : 'Searched codebase';
    targetChip = searchQuery ? `"${searchQuery}"` : '';
    ActionIcon = Search;
    accentColor = 'sky';
    borderHover = 'hover:border-sky-500/40';
  } else if (isEditing) {
    actionTitle = language === 'vi' ? 'Cập nhật tệp' : 'Edited file';
    targetChip = fileName ? `${fileName}${lineInfo}` : '';
    ActionIcon = FileText;
    accentColor = 'amber';
    borderHover = 'hover:border-amber-500/40';
  } else if (isExploring) {
    actionTitle = language === 'vi' ? 'Khảo sát tệp' : 'Explored file';
    targetChip = fileName ? `${fileName}${lineInfo}` : '';
    ActionIcon = FileCode2;
    accentColor = 'emerald';
    borderHover = 'hover:border-emerald-500/40';
  } else if (isCommand) {
    actionTitle = language === 'vi' ? 'Thực thi lệnh' : 'Ran command';
    targetChip = cmdLine ? cmdLine : '';
    ActionIcon = Terminal;
    accentColor = 'purple';
    borderHover = 'hover:border-purple-500/40';
  }

  const handleInspect = async (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
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

  const handleToggle = () => {
    setIsOpen(!isOpen);
    if (onClick) onClick();
  };

  const colorMap = {
    sky: {
      text: 'text-sky-400',
      badge: 'text-sky-300/90 bg-sky-500/10 border-sky-500/20',
      glow: 'group-hover/badge:text-sky-300'
    },
    indigo: {
      text: 'text-indigo-400',
      badge: 'text-indigo-300/90 bg-indigo-500/10 border-indigo-500/20',
      glow: 'group-hover/badge:text-indigo-300'
    },
    emerald: {
      text: 'text-emerald-400',
      badge: 'text-emerald-300/90 bg-emerald-500/10 border-emerald-500/20',
      glow: 'group-hover/badge:text-emerald-300'
    },
    amber: {
      text: 'text-amber-400',
      badge: 'text-amber-300/90 bg-amber-500/10 border-amber-500/20',
      glow: 'group-hover/badge:text-amber-300'
    },
    purple: {
      text: 'text-purple-400',
      badge: 'text-purple-300/90 bg-purple-500/10 border-purple-500/20',
      glow: 'group-hover/badge:text-purple-300'
    }
  }[accentColor as 'sky' | 'indigo' | 'emerald' | 'amber' | 'purple'] || {
    text: 'text-cyan-400',
    badge: 'text-cyan-300/90 bg-cyan-500/10 border-cyan-500/20',
    glow: 'group-hover/badge:text-cyan-300'
  };

  return (
    <div className="my-1.5 ml-14 font-sans w-fit max-w-[95%]">
      {/* 🌟 [ANTIGRAVITY-CARD]: Thanh thẻ hành động hiện đại chuẩn Antigravity */}
      <div 
        onClick={handleToggle}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] ${borderHover} backdrop-blur-md transition-all duration-200 cursor-pointer select-none text-[12px] group/badge shadow-sm`}
      >
        <div className="text-white/40 group-hover/badge:text-white/80 transition-colors shrink-0">
          {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </div>
        
        <ActionIcon className={`w-3.5 h-3.5 ${colorMap.text} shrink-0`} />
        
        <span className="font-semibold text-white/70 tracking-tight group-hover/badge:text-white/90 transition-colors">
          {actionTitle}
        </span>

        {targetChip && (
          <span className={`font-mono text-[11px] px-1.5 py-0.5 rounded border max-w-[320px] truncate ${colorMap.badge}`}>
            {targetChip}
          </span>
        )}

        <CheckCircle2 className="w-3 h-3 text-emerald-400/70 ml-1 shrink-0 opacity-60 group-hover/badge:opacity-100 transition-opacity" />
      </div>

      {/* 📜 [COLLAPSIBLE-DRAWER]: Hộp chi tiết khi mở rộng */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden bg-[#070a12]/95 border border-white/[0.08] rounded-xl p-3 mt-1.5 flex flex-col gap-2 shadow-xl backdrop-blur-xl"
          >
            <div className="text-white/60 font-mono leading-relaxed text-[11px] break-all bg-black/40 p-2.5 rounded-lg border border-white/5 max-h-56 overflow-y-auto custom-scroll select-text">
              {msg}
            </div>

            {filePath && (
              <div className="flex items-center justify-between pt-1 border-t border-white/5">
                <button 
                  onClick={handleInspect}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-300 text-[11px] font-semibold transition-all cursor-pointer"
                >
                  <FileText className="w-3 h-3" />
                  <span>{language === 'vi' ? `Mở tệp ${fileName} trong Studio` : `Inspect ${fileName} in Studio`}</span>
                </button>
                <span className="text-[10px] font-mono text-white/30">{filePath}</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

// ── Helper: Định dạng kế hoạch / tư duy dạng JSON thành markdown dễ đọc ──────
function formatReasoningContent(content: string, language: string): string {
  if (!content) return '';
  const trimmed = content.trim();
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      const data = JSON.parse(trimmed);
      let output = '';
      if (data.expert_mindset || data.mindset) {
        output += `**${language === 'vi' ? 'Định hướng tư duy' : 'Mindset'}:** ${data.expert_mindset || data.mindset}\n\n`;
      }
      if (data.strategy || data.rationale) {
        output += `**${language === 'vi' ? 'Phương pháp' : 'Strategy'}:** ${data.strategy || data.rationale}\n\n`;
      }
      if (data.steps && Array.isArray(data.steps)) {
        output += `**${language === 'vi' ? 'Các bước kế hoạch' : 'Execution Steps'}:**\n`;
        data.steps.forEach((s: any, idx: number) => {
          const name = s.title || s.instruction || s.tool || `Bước ${idx + 1}`;
          output += `- **Bước ${idx + 1}**: ${name}\n`;
        });
      } else if (data.sub_tasks && Array.isArray(data.sub_tasks)) {
        output += `**${language === 'vi' ? 'Các bước kế hoạch' : 'Execution Steps'}:**\n`;
        data.sub_tasks.forEach((s: any, idx: number) => {
          const name = s.instruction || s.tool || `Bước ${idx + 1}`;
          output += `- **${s.id || `Bước ${idx + 1}`}**: ${name}\n`;
        });
      } else if (data.plan && Array.isArray(data.plan)) {
        output += `**${language === 'vi' ? 'Kế hoạch hành động' : 'Action Plan'}:**\n`;
        data.plan.forEach((item: any, idx: number) => {
          output += `- ${typeof item === 'string' ? item : item.action || item.step || JSON.stringify(item)}\n`;
        });
      }
      if (output.trim()) return output;
    } catch {
      // Bỏ qua nếu parse JSON thất bại
    }
  }
  return content;
}

export const ReasoningBlock = memo(({ tag, msg, duration }: { tag: string, msg: string, duration?: number }) => {
  const [isOpen, setIsOpen] = useState(false);
  const language = useZenithStore(s => s.language);
  const safeTag = tag || '';
  const tagUpper = safeTag.toUpperCase();
  
  let cleanMsg = stripLogMetadata(msg);
  if (!tagUpper.includes('PROGRESS') && !tagUpper.includes('EXECUTOR')) {
    cleanMsg = cleanMsg.replace(/^(?:[^\w\s]*)\s*\[(DEBUG|TRACE|LOG|INFO|SYS)\]:\s*/g, '').trim();
  }
  cleanMsg = cleanMsg.replace(/^Đang /i, 'Đang ').replace(/^Đã /i, 'Đã ');

  const isPlan = tagUpper.includes('PLAN') || cleanMsg.includes('"expert_mindset"') || cleanMsg.includes('"sub_tasks"');
  const isAudit = tagUpper.includes('CRITIC') || tagUpper.includes('AUDIT') || tagUpper.includes('AQV');

  let blockTitle = language === 'vi' ? 'Quá trình suy luận...' : 'System reasoning...';
  if (isPlan) {
    blockTitle = language === 'vi' ? 'Kế hoạch chiến lược' : 'Strategic Plan';
  } else if (isAudit) {
    blockTitle = language === 'vi' ? 'Thẩm định chất lượng' : 'Quality Assessment';
  } else if (duration !== undefined) {
    blockTitle = language === 'vi' ? `Đã tư duy (${duration}s)` : `Thought for ${duration}s`;
  }

  const formattedContent = formatReasoningContent(cleanMsg, language);

  return (
    <div className="my-1.5 ml-14 font-sans w-fit max-w-[95%]">
      {/* 🧠 [ANTIGRAVITY-THOUGHT-PILL]: Pill tư duy thu gọn giống Antigravity */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-500/[0.06] hover:bg-indigo-500/[0.12] border border-indigo-500/20 hover:border-indigo-500/35 backdrop-blur-md transition-all duration-200 cursor-pointer select-none text-[12px] group/thought shadow-sm"
      >
        <div className="text-indigo-400/60 group-hover/thought:text-indigo-300 transition-colors shrink-0">
          {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </div>
        
        <Brain className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        
        <span className="font-semibold text-indigo-200/80 tracking-tight group-hover/thought:text-indigo-100 transition-colors">
          {blockTitle}
        </span>

        {duration !== undefined && (
          <span className="text-[10px] font-mono text-indigo-300/70 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20 ml-1">
            {duration}s
          </span>
        )}
      </div>

      {/* 📜 [REASONING-CONTENT]: Nội dung suy nghĩ khi bấm mở */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden bg-[#070914]/95 border border-indigo-500/20 rounded-xl p-3.5 mt-1.5 shadow-xl backdrop-blur-xl"
          >
            <div className="text-[12px] font-medium leading-relaxed font-mono text-indigo-100/75 select-text">
              <MarkdownRenderer content={formattedContent || cleanMsg || msg} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

// ── 🌲 [ANTIGRAVITY-PROCESS-TREE]: Khối hiển thị toàn bộ tiến trình như Antigravity ──
export const ProcessTreeItem = memo(({ log }: { log: AgentLog }) => {
  const [isOpen, setIsOpen] = useState(false);
  const language = useZenithStore(s => s.language);
  const raw = log.msg || '';
  const clean = stripLogMetadata(raw);
  const tag = (log.tag || '').toUpperCase();
  const lower = clean.toLowerCase();

  // Phân loại hạng mục
  const isWebSearch = lower.includes('search_web') || lower.includes('web_search') || lower.includes('tavily') || lower.includes('ddg') || lower.includes('search web for') || lower.includes('tìm kiếm trên web');
  const isWebRead = lower.includes('read_url') || lower.includes('browse') || lower.includes('url_content') || clean.includes('http://') || clean.includes('https://');
  const isCommand = !isWebSearch && !isWebRead && (lower.includes('command') || lower.includes('exec') || lower.includes('chạy') || lower.includes('thực thi') || tag === 'COMMAND');
  const isPlan = tag.includes('PLAN') || clean.includes('"expert_mindset"') || clean.includes('"sub_tasks"') || clean.includes('PHÊ CHÍNH KẾ HOẠCH') || clean.includes('LỘ TRÌNH TRIỂN KHAI');
  const isAudit = tag.includes('CRITIC') || tag.includes('AUDIT') || tag.includes('AQV');
  const isThought = tag.includes('THOUGHT') || tag.includes('TƯ DUY');

  // Trích xuất tiêu đề thân thiện
  let title = '';
  let ItemIcon = Brain;
  let iconColor = 'text-white/40';

  if (isWebSearch) {
    ItemIcon = Search;
    iconColor = 'text-sky-400';
    const match = clean.match(/(?:for|cho):\s*([^\n\r"]+)/i) || clean.match(/["'`]([^"'`]{2,80})["'`]/);
    const q = match ? match[1].replace(/[`"']/g, '').trim() : '';
    title = q ? (language === 'vi' ? `Tìm kiếm web: "${q}"` : `Search web: "${q}"`) : (language === 'vi' ? 'Tìm kiếm trên Web' : 'Searched the web');
  } else if (isWebRead) {
    ItemIcon = Globe;
    iconColor = 'text-indigo-400';
    const urlMatch = clean.match(/https?:\/\/([^\s\/\)"']+)/i);
    const domain = urlMatch ? urlMatch[1].replace(/^www\./i, '') : '';
    title = domain ? (language === 'vi' ? `Đọc trang web: ${domain}` : `Read web page: ${domain}`) : (language === 'vi' ? 'Đọc nội dung trang web' : 'Read web page');
  } else if (isPlan) {
    ItemIcon = Brain;
    iconColor = 'text-indigo-400';
    title = language === 'vi' ? 'Kế hoạch chiến lược & lộ trình' : 'Strategic plan & roadmap';
  } else if (isAudit) {
    ItemIcon = ShieldCheck;
    iconColor = 'text-emerald-400';
    title = language === 'vi' ? 'Thẩm định chất lượng & kiểm soát' : 'Quality audit & safety check';
  } else if (isCommand) {
    ItemIcon = Terminal;
    iconColor = 'text-amber-400';
    const cMatch = clean.match(/`([^`]+)`/) || clean.match(/command:?\s*["']?([^"'\n\r]{2,80})["']?/i);
    const cmd = cMatch ? cMatch[1].trim() : '';
    title = cmd ? (language === 'vi' ? `Thực thi lệnh: ${cmd}` : `Run command: ${cmd}`) : (language === 'vi' ? 'Thực thi lệnh hệ thống' : 'Run system command');
  } else if (isThought) {
    ItemIcon = Brain;
    iconColor = 'text-sky-400';
    const dur = log.duration ? `${log.duration}s` : '';
    title = dur ? (language === 'vi' ? `Suy nghĩ trong ${dur}` : `Thought for ${dur}`) : (language === 'vi' ? 'Tư duy logic' : 'Reasoning');
  } else {
    ItemIcon = Zap;
    iconColor = 'text-white/40';
    title = clean.slice(0, 70);
  }

  const formattedContent = formatReasoningContent(clean, language);

  return (
    <div className="flex flex-col text-[11.5px] font-sans">
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 py-1 px-1.5 rounded-lg hover:bg-white/[0.04] text-white/60 hover:text-white/90 transition-all cursor-pointer group select-none"
      >
        <ItemIcon className={`w-3.5 h-3.5 ${iconColor} shrink-0 opacity-80 group-hover:opacity-100`} />
        <span className="flex-1 truncate tracking-tight text-white/70 group-hover:text-white/95">
          {title}
        </span>
        <div className="text-white/20 group-hover:text-white/50 transition-colors shrink-0">
          {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </div>
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden pl-5 pr-2 py-2 text-[11px] font-mono text-white/50 bg-black/30 rounded-lg mt-0.5 border border-white/5"
          >
            <div className="max-h-48 overflow-y-auto custom-scroll leading-relaxed select-text">
              <MarkdownRenderer content={formattedContent || clean || raw} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

export const AntigravityProcessTree = memo(({ 
  items, 
  isRunning = false,
  startTs,
  finishTs
}: { 
  items: AgentLog[];
  isRunning?: boolean;
  startTs?: number;
  finishTs?: number;
}) => {
  // 🌟 [ANTIGRAVITY-AUTO-COLLAPSE]: 
  // - Khi đang chạy: Tự động mở rộng (true) để Master theo dõi các bước
  // - Khi đã chạy xong: Mặc định TỰ ĐỘNG THU GỌN LẠI (false) giống hệt Antigravity!
  const [isExpanded, setIsExpanded] = useState(isRunning);
  const userInteractedRef = useRef(false);
  const prevRunningRef = useRef(isRunning);

  useEffect(() => {
    // Nếu vừa chuyển từ trạng thái đang chạy sang hoàn tất (finished)
    if (prevRunningRef.current && !isRunning) {
      // Tự động thu gọn lại nếu người dùng chưa can thiệp cưỡng chế
      if (!userInteractedRef.current) {
        setIsExpanded(false);
      }
    } else if (!prevRunningRef.current && isRunning) {
      // Khi bắt đầu chạy lượt mới: tự động mở rộng để Master theo dõi
      setIsExpanded(true);
      userInteractedRef.current = false;
    }
    prevRunningRef.current = isRunning;
  }, [isRunning]);

  const handleToggle = () => {
    userInteractedRef.current = true;
    setIsExpanded(prev => !prev);
  };

  const language = useZenithStore(s => s.language);

  if (!items || items.length === 0) return null;

  // ⏱️ [ACTIVE-EXECUTION-TIMER]: Tính toán thời lượng thực thi thực tế (Active Working Duration)
  // Loại trừ hoàn toàn khoảng thời gian treo (idle/pause), thời gian chờ người dùng hoặc ngắt quãng phiên
  let durationStr = '';
  if (!isRunning && items.length > 0) {
    let activeSec = 0;

    // 1. Nếu các items có duration thực tế từ backend
    let hasExplicitDurations = false;
    let explicitDurSum = 0;
    items.forEach(it => {
      if (it.duration && typeof it.duration === 'number' && it.duration > 0) {
        hasExplicitDurations = true;
        explicitDurSum += it.duration;
      }
    });

    if (hasExplicitDurations && explicitDurSum > 0) {
      activeSec = explicitDurSum;
    } else {
      // 2. Tính theo chuỗi bước thực thi liên tục (Consecutive Step Deltas)
      // Mỗi bước thực thi (tool call, search, LLM reasoning) kéo dài tối đa 25s.
      // Nếu khoảng cách giữa 2 log liên tiếp > 25s thì đó là idle gap / tạm dừng phiên, không tính vào thời gian chạy!
      for (let i = 0; i < items.length - 1; i++) {
        const curTs = items[i].ts || 0;
        const nextTs = items[i + 1].ts || 0;
        const delta = nextTs - curTs;
        if (delta > 0 && delta <= 25) {
          activeSec += delta;
        } else {
          // Bước gián đoạn / idle gap: chỉ cộng thời lượng danh định của 1 bước xử lý (~2.5s)
          activeSec += 2.5;
        }
      }

      // Cộng thêm bước tổng hợp cuối cùng từ item cuối tới finishTs
      if (finishTs && items[items.length - 1].ts) {
        const lastDelta = finishTs - (items[items.length - 1].ts || 0);
        if (lastDelta > 0 && lastDelta <= 15) {
          activeSec += lastDelta;
        } else {
          activeSec += 2; // thời gian hoàn thiện câu trả lời
        }
      } else {
        activeSec += 2;
      }
    }

    // Làm tròn thời lượng hợp lý
    const s = Math.max(1, Math.round(activeSec));
    if (s < 60) {
      durationStr = `${s}s`;
    } else {
      const m = Math.floor(s / 60);
      const remS = s % 60;
      durationStr = remS > 0 ? `${m}m ${remS}s` : `${m}m`;
    }
  }

  // Header Title giống hệt Antigravity:
  // - Khi đang chạy: hiển thị tên bước đang thực thi (ví dụ "Đang tìm kiếm web...") kèm chevron v mở rộng
  // - Khi đã chạy xong: TỰ ĐỘNG THU GỌN thành "Đã xử lý trong {durationStr} >"
  let activeTitle = language === 'vi' ? 'Đang xử lý...' : 'Working...';
  if (isRunning && items.length > 0) {
    const last = items[items.length - 1];
    const lastClean = stripLogMetadata(last.msg || '');
    if (lastClean && !lastClean.startsWith('{')) {
      activeTitle = lastClean.slice(0, 45);
    }
  }

  const headerTitle = isRunning
    ? activeTitle
    : (language === 'vi'
        ? (durationStr ? `Đã xử lý trong ${durationStr}` : `Quá trình thực thi (${items.length} bước)`)
        : (durationStr ? `Worked for ${durationStr}` : `Executed ${items.length} steps`));

  return (
    <div className="my-2 ml-14 font-sans max-w-[85%]">
      {/* 🌟 Top Header: chuẩn Antigravity (Tiêu đề + Chevron ở cuối) */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-1.5 text-[12px] font-medium text-white/50 hover:text-white/80 transition-colors cursor-pointer select-none py-1 group"
      >
        {isRunning && (
          <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin mr-1 shrink-0" />
        )}
        <span className={`tracking-tight ${isRunning ? 'text-cyan-300/90 font-medium' : 'text-white/50 group-hover:text-white/80'}`}>
          {headerTitle}
        </span>
        <span className="text-white/30 group-hover:text-white/60 transition-colors">
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </span>
      </button>

      {/* 🌟 Indented Nested Tree: giống hệt cấu trúc của Antigravity */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden ml-2 pl-3 border-l border-white/10 space-y-0.5 mt-1"
          >
            {items.map((it, idx) => (
              <ProcessTreeItem key={it.id || idx} log={it} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});
