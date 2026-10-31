import React, { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDown, ChevronRight, FileCheck, ExternalLink, 
  Eye, FileText, Code2, Sparkles, CheckCircle2 
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useZenithStore } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';

export interface ChangedFileItem {
  path: string;
  name?: string;
  dir?: string;
  added?: number;
  removed?: number;
  type?: string;
}

export interface FileChangesCardProps {
  files?: ChangedFileItem[] | string[];
  totalFiles?: number;
  addedLines?: number;
  removedLines?: number;
  title?: string;
  onReview?: () => void;
}

const getFileBadge = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (ext === 'py') {
    return { symbol: '🐍', label: 'PY', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
  }
  if (['tsx', 'jsx'].includes(ext)) {
    return { symbol: '⚛', label: 'REACT', bg: 'bg-sky-500/10 text-sky-400 border-sky-500/30' };
  }
  if (['ts', 'js'].includes(ext)) {
    return { symbol: 'TS', label: 'TS', bg: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
  }
  if (['md', 'markdown'].includes(ext)) {
    return { symbol: 'M↓', label: 'MD', bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' };
  }
  if (['json', 'yaml', 'yml'].includes(ext)) {
    return { symbol: '{ }', label: 'CONFIG', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30' };
  }
  if (['png', 'jpg', 'jpeg', 'webp', 'svg', 'gif'].includes(ext)) {
    return { symbol: '🖼', label: 'IMG', bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30' };
  }
  if (['sh', 'bash', 'zsh'].includes(ext)) {
    return { symbol: '>_', label: 'SH', bg: 'bg-slate-500/10 text-slate-300 border-slate-500/30' };
  }
  return { symbol: '📄', label: ext.toUpperCase() || 'FILE', bg: 'bg-white/5 text-white/60 border-white/10' };
};

export const FileChangesCard: React.FC<FileChangesCardProps> = memo(({
  files = [],
  totalFiles,
  addedLines = 0,
  removedLines = 0,
  title,
  onReview
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const setTab = useZenithStore(s => s.setTab);
  const language = useZenithStore(s => s.language);

  // Normalize files list
  const normalizedFiles: ChangedFileItem[] = files.map(item => {
    if (typeof item === 'string') {
      const parts = item.replace(/\\/g, '/').split('/');
      const name = parts.pop() || item;
      const dir = parts.length > 0 ? parts.join('/') : '';
      return { path: item, name, dir };
    }
    const cleanPath = (item.path || '').replace(/\\/g, '/');
    const parts = cleanPath.split('/');
    const name = item.name || parts.pop() || cleanPath;
    const dir = item.dir || (parts.length > 0 ? parts.join('/') : '');
    return { ...item, path: cleanPath, name, dir };
  });

  const fileCount = totalFiles ?? normalizedFiles.length;

  const handleOpenFile = async (filePath: string, fileName: string) => {
    try {
      toast.loading(`Đang mở: ${fileName}...`, { id: 'OPEN_FILE', duration: 1500 });
      const r = await ZenithService.readFile(filePath);
      if (r?.ok || r?.content != null) {
        setInspectedFile({
          path: filePath,
          content: r.content || '',
          type: r.type,
          raw_url: r.raw_url,
          connId: 'local'
        });
        setTab('explorer');
        toast.success(`Đã mở ${fileName}`, { id: 'OPEN_FILE' });
      } else {
        toast.error(`Không thể đọc file: ${fileName}`, { id: 'OPEN_FILE' });
      }
    } catch (err: any) {
      toast.error(`Lỗi mở file: ${err?.message || 'Không xác định'}`, { id: 'OPEN_FILE' });
    }
  };

  if (normalizedFiles.length === 0 && fileCount === 0) return null;

  return (
    <div className="my-3 w-full max-w-2xl rounded-2xl border border-white/[0.08] bg-[#070a12]/90 backdrop-blur-xl shadow-2xl overflow-hidden text-white font-sans select-none">
      {/* Header bar */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-3 flex items-center justify-between bg-white/[0.02] hover:bg-white/[0.04] cursor-pointer transition-colors border-b border-white/[0.04]"
      >
        <div className="flex items-center gap-2.5">
          <button 
            type="button" 
            className="p-1 rounded-md text-white/50 hover:text-white transition-colors"
          >
            {isOpen ? <ChevronDown className="w-4 h-4 text-cyan-400" /> : <ChevronRight className="w-4 h-4 text-white/40" />}
          </button>
          
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-bold text-white/90">
              {title || `${fileCount} ${language === 'vi' ? 'tệp đã thay đổi' : 'files changed'}`}
            </span>
            {(addedLines > 0 || removedLines > 0) && (
              <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold ml-1">
                {addedLines > 0 && <span className="text-emerald-400">+{addedLines}</span>}
                {removedLines > 0 && <span className="text-rose-400">-{removedLines}</span>}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onReview ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onReview();
              }}
              className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-semibold text-white/80 hover:text-white flex items-center gap-1.5 transition-all shadow-sm"
            >
              <FileCheck className="w-3.5 h-3.5 text-cyan-400" />
              <span>Review</span>
            </button>
          ) : (
            <span className="text-[10px] uppercase tracking-wider font-mono text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded-md">
              Antigravity Ready
            </span>
          )}
        </div>
      </div>

      {/* Files list */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="divide-y divide-white/[0.03] overflow-hidden"
          >
            {normalizedFiles.map((f, idx) => {
              const badge = getFileBadge(f.name || f.path);
              const displayDir = f.dir ? (f.dir.startsWith('/') ? f.dir : `/${f.dir}`) : '';

              return (
                <div
                  key={`${f.path}-${idx}`}
                  onClick={() => handleOpenFile(f.path, f.name || f.path)}
                  className="px-4 py-2.5 flex items-center justify-between hover:bg-cyan-500/[0.06] cursor-pointer group transition-all duration-200"
                  title={`Click để mở xem tệp: ${f.path}`}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    {/* Badge */}
                    <div className={`w-7 h-7 rounded-lg border flex items-center justify-center text-[12px] font-mono shrink-0 shadow-sm ${badge.bg}`}>
                      <span>{badge.symbol}</span>
                    </div>

                    {/* File Name & Path */}
                    <div className="flex items-baseline gap-2 min-w-0 truncate">
                      <span className="text-[13px] font-semibold text-white/95 group-hover:text-cyan-300 transition-colors shrink-0">
                        {f.name}
                      </span>
                      {displayDir && (
                        <span className="text-[11px] font-mono text-white/35 group-hover:text-white/55 truncate transition-colors">
                          {displayDir}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions / indicators */}
                  <div className="flex items-center gap-2 shrink-0 ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    {(f.added != null || f.removed != null) && (
                      <span className="text-[10px] font-mono font-bold">
                        {f.added ? <span className="text-emerald-400">+{f.added} </span> : null}
                        {f.removed ? <span className="text-rose-400">-{f.removed}</span> : null}
                      </span>
                    )}
                    <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider flex items-center gap-1 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                      <Eye className="w-3 h-3" />
                      Mở
                    </span>
                  </div>
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});
