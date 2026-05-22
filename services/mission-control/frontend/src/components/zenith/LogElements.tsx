import React, { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Zap, FileCode2, Terminal, ChevronRight } from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

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

export const ActionBadge = memo(({ label, onClick }: { label: string, onClick?: () => void }) => {
  const isEditing = label.toLowerCase().includes('edit') || label.toLowerCase().includes('patch');
  const isExploring = label.toLowerCase().includes('view') || label.toLowerCase().includes('analyz') || label.toLowerCase().includes('explor');
  const baseLabel = isEditing ? 'Refactoring file' : isExploring ? 'Analyzing file' : label;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 py-1.5 px-1 hover:bg-white/[0.02] rounded-lg transition-all group/badge w-fit"
    >
      <span className="text-[13px] font-medium text-white/50 group-hover/badge:text-white/80 transition-colors">{baseLabel}</span>
      <ChevronRight className="w-4 h-4 text-white/30 group-hover/badge:text-white/60 transition-colors" />
    </button>
  );
});

export const ReasoningBlock = memo(({ tag, msg }: { tag: string, msg: string }) => {
  const role = tag.includes(':') ? tag.split(':')[1] : tag;
  const isCritic = role === 'CRITIC' || role === 'ADVERSARIAL';
  
  // 💎 [CLI-AESTHETIC]: Các log không quan trọng (tiến trình nền) sẽ có màu xám
  const isImportant = role === 'MASTER' || role === 'DISPATCHER' || role === 'GATEWAY' || role === 'ERROR' || role === 'CRITIC' || tag === 'PROGRESS' || tag.includes('THOUGHT') || tag.includes('PLANNING') || tag.includes('TƯ DUY');
  
  let color = isImportant ? 'text-cyan-400' : 'text-gray-500';

  let displayRole = role;
  if (role.includes('GATEWAY') || role.includes('RECEPTIONIST')) { color = "text-emerald-400"; displayRole = 'Ban Lễ Tân'; }
  else if (role.includes('DISPATCHER')) { color = "text-amber-400"; displayRole = 'Ban Điều Phối'; }
  else if (role.includes('PLANNER') || role.includes('THOUGHT')) { color = "text-indigo-400"; displayRole = 'Ban Kế Hoạch'; }
  else if (role.includes('EXECUTOR')) { color = "text-blue-400"; displayRole = 'Ban Thực Thi'; }
  else if (role.includes('SUMMARIZER')) { color = "text-fuchsia-400"; displayRole = 'Ban Thư Ký'; }
  else if (role.includes('CRITIC') || role.includes('AUDIT')) { color = "text-rose-400"; displayRole = 'Ban Kiểm Soát'; }
  else if (role.includes('DATA_SCOUT') || role.includes('RESEARCH') || role.includes('SEARCH')) { color = "text-sky-400"; displayRole = 'Ban Tình Báo'; }
  else if (role.includes('FORGE')) { color = "text-purple-400"; displayRole = 'Ban Công Nghệ'; }
  else if (role === 'SYSTEM' || role === 'SYS_LOG') { displayRole = 'Ban Kỹ Thuật'; }
  else if (role === 'ENGINE') { displayRole = 'Trung tâm Điều hành'; }

  let cleanMsg = msg.replace(/^(?:[^\w\s]*)\s*\[.*?\]:\s*/g, '').trim();
  cleanMsg = cleanMsg.replace(/^Đang /i, 'Đang ').replace(/^Đã /i, 'Đã ');

  // Loại bỏ các hộp màu mè, hiển thị trực tiếp một dòng CLI
  return (
    <div className={`font-mono text-[12px] leading-relaxed my-1 flex gap-2 ${isImportant ? 'opacity-100' : 'opacity-70'}`}>
      <span className={`${color} font-semibold shrink-0`}>[{displayRole}]</span>
      <span className={isImportant ? 'text-white/90 italic' : 'text-gray-400 italic'}>
        <MarkdownRenderer content={cleanMsg || msg} />
      </span>
    </div>
  );
});
