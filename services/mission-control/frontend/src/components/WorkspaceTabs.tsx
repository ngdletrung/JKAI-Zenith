import React, { memo, useState, useEffect, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { Database, RefreshCw, Loader2, FolderOpen, Folder, FileCode2, ChevronRight, Terminal, Radio, ScrollText, FileText, Code2, Maximize2, GitBranch, CircuitBoard, X } from 'lucide-react';
import { useZenithStore, Dictionary } from '../store/zenithStore';
import { ZenithService } from '../services/ZenithService';
import { MarkdownRenderer } from './zenith/MarkdownRenderer';
import { SovereignFileLab } from './SovereignFileLab';
import { MissionHistory } from './zenith/MissionHistory';

// ─── NEURAL EXPLORER ─────────────────────────────────────────────────────────

const FileItem = ({ item, depth, onInspect }: { item: any; depth: number; onInspect: (p: string) => void }) => {
  const isDir = item.type === 'directory';
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div>
      <div className="group flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 cursor-pointer transition-all" style={{ paddingLeft: `${depth * 1.2 + 1}rem` }} onClick={() => isDir ? setIsOpen(!isOpen) : onInspect(item.path)}>
        <div className={isDir ? 'text-amber-400' : 'text-sky-400'}>{isDir ? (isOpen ? <FolderOpen className="w-4 h-4" /> : <Folder className="w-4 h-4" />) : <FileCode2 className="w-4 h-4" />}</div>
        <div className="flex-1 min-w-0"><p className="text-[12px] font-bold text-white/80 truncate">{item.name}</p></div>
      </div>
      {isDir && isOpen && item.children && item.children.map((child: any) => <FileItem key={child.path} item={child} depth={depth + 1} onInspect={onInspect} />)}
    </div>
  );
};

export const NeuralExplorer = memo(() => {
  const [tree, setTree] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const language = useZenithStore(s => s.language);

  const loadDir = () => { setLoading(true); ZenithService.listDir().then(setTree).finally(() => setLoading(false)); };
  useEffect(() => { loadDir(); }, []);

  return (
    <div className="flex-1 flex flex-col bg-[#020408]">
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3"><Database className="w-4 h-4 text-sky-400" /><h3 className="text-[11px] font-black uppercase tracking-widest text-white/90">Neural Vault</h3></div>
        <button onClick={loadDir} className="p-2 text-white/20 hover:text-white"><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>
      <div className="flex-1 overflow-y-auto custom-scroll">{tree.map(node => <FileItem key={node.path} item={node} depth={0} onInspect={(p) => ZenithService.readFile(p).then(r => r.ok && setInspectedFile({ path: p, content: r.content }))} />)}</div>
    </div>
  );
});

// ─── ARTIFACT GALLERY ────────────────────────────────────────────────────────

export const ArtifactGallery = memo(({ content, type }: { content: string, type: string }) => {
  const { setInspectedFile } = useZenithStore();
  const artifacts = useMemo(() => {
    const blocks = content.split(/#\s+/).filter(Boolean);
    return blocks.map(b => ({ title: b.split('\n')[0].trim(), body: b.split('\n').slice(1).join('\n').trim(), isReport: type === 'walkthrough' }));
  }, [content, type]);

  return (
    <div className="flex-1 overflow-y-auto custom-scroll p-6 space-y-6">
      {artifacts.length === 0 ? <div className="h-full flex items-center justify-center opacity-10"><ScrollText className="w-12 h-12" /></div> : 
        artifacts.map((art, i) => (
          <div key={i} onClick={() => setInspectedFile({ path: art.title, content: art.body })} className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-sky-500/40 cursor-pointer transition-all">
             <h4 className="text-[14px] font-bold text-white/90 mb-2">{art.title}</h4>
             <div className="opacity-40 line-clamp-3"><MarkdownRenderer content={art.body} /></div>
          </div>
        ))
      }
    </div>
  );
});

// ─── FILE PREVIEW (INSPECTOR) ────────────────────────────────────────────────

export const FilePreview = memo(() => {
  const inspectedFile = useZenithStore(s => s.inspectedFile);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const language = useZenithStore(s => s.language);
  if (!inspectedFile) return null;
  const dict = Dictionary[language as keyof typeof Dictionary] || Dictionary.en;

  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="absolute inset-0 z-50 bg-[#060910] flex flex-col">
      <div className="p-4 border-b border-white/5 flex items-center justify-between bg-black/40">
        <div className="flex items-center gap-3">
          <FileCode2 className="w-4 h-4 text-sky-400" />
          <span className="text-[11px] font-black uppercase tracking-widest text-white/90 truncate max-w-[200px]">{inspectedFile.path.split('/').pop()}</span>
        </div>
        <button onClick={() => setInspectedFile(null)} className="p-2 text-white/20 hover:text-rose-400 transition-colors"><X className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 overflow-auto custom-scroll p-4">
        <MarkdownRenderer content={`\`\`\`typescript\n${inspectedFile.content}\n\`\`\``} />
      </div>
    </motion.div>
  );
});

// ─── PROCESS LOG TAB (TIẾN TRÌNH) — CLI STREAM ─────────────────────────────

const getCliColor = (tag: string, msg: string = '') => {
  const t = tag.toUpperCase();
  const m = msg.toUpperCase();
  if (t === 'JKAI' || t === 'MISSION_RESULT' || t === 'ZENITH') return 'text-cyan-400';
  if (t === 'MASTER' || t.startsWith('MASTER')) return 'text-amber-400';
  if (t === 'ERROR' || t === 'WARN' || t === 'WARNING') return 'text-rose-500';
  if (m.includes('PHASE') || m.includes('STAGE')) return 'text-white/90';
  return 'text-gray-500'; // Mặc định là màu xám nền
};

const isImportantTag = (tag: string, msg: string = '') => {
  const t = tag.toUpperCase();
  const m = msg.toUpperCase();
  const isPhase = m.includes('STAGE') || m.includes('PHASE') || m.includes('ONLINE');
  // Chỉ Master, JKAI, Lỗi hoặc Dòng chuyển giai đoạn quan trọng mới nổi bật
  return ['JKAI', 'MISSION_RESULT', 'ERROR', 'WARN', 'WARNING', 'ZENITH'].includes(t) || t.startsWith('MASTER') || isPhase;
};

const toTitleCase = (str: string) => {
  if (!str) return '';
  const upper = str.toUpperCase();
  if (upper === 'JKAI') return 'JKAI';
  if (upper === 'SYSTEM') return 'System';
  if (upper === 'PROGRESS') return 'Progress';
  return str.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('_');
};

const ProcessLogTab = memo(() => {
  const progressLogs = useZenithStore(s => s.progressLogs);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sortedLogs = useMemo(() => {
    return [...progressLogs].sort((a, b) => (a.ts || 0) - (b.ts || 0));
  }, [progressLogs]);

  // 🛡️ [SCROLL-GUARD]: Khi Master lăn chuột lên → tạm dừng auto-scroll 2 phút
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;

    if (isAtBottom) {
      userScrolledRef.current = false;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    } else {
      userScrolledRef.current = true;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
      resumeTimerRef.current = setTimeout(() => {
        userScrolledRef.current = false;
      }, 120_000); // 2 phút
    }
  };

  useEffect(() => {
    if (!userScrolledRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [sortedLogs]);

  useEffect(() => {
    return () => { if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current); };
  }, []);

  return (
    <div ref={scrollRef} onScroll={handleScroll} className="absolute inset-0 pt-4 px-4 pb-16 overflow-y-auto custom-scroll bg-[#060910]/60">
      <div className="flex flex-col font-sans font-[300] tracking-wide text-[13px] leading-relaxed">
        {sortedLogs.length === 0 && (
          <span className="text-gray-500 italic">Chờ tín hiệu nơ-ron...</span>
        )}
        {sortedLogs.map((l: any, i: number) => {
          const tag = (l.tag || 'SYS').toUpperCase();
          const msg = (l.msg || '').replace(/\[⏱️\s*[\d.]+\s*s\]/g, '').trim();
          if (!msg) return null;
          
          const color = getCliColor(tag, msg);
          const important = isImportantTag(tag, msg);
          const isErrorOrWarn = tag === 'ERROR' || tag === 'WARN' || tag === 'WARNING';
          const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER');
          
          // 💎 Dùng Markdown cho các log Tư duy và Log quan trọng để hiển thị đầy đủ định dạng
          if (important || isThought) {
            // 🧠 Hiển thị tên service: [Thought:Receptionist] thay vì chỉ [Thought]
            const displayTag = (isThought && l.source) 
              ? `${toTitleCase(tag)}:${toTitleCase(l.source)}`
              : toTitleCase(tag);
            return (
              <div key={l.id || i} id={`log-${l.id}`} className={`my-2 flex items-start gap-2.5 ${important ? '' : 'opacity-70'}`}>
                <span className={`${color} font-bold shrink-0 text-[11.5px] mt-[2px] w-[85px] whitespace-nowrap overflow-hidden text-ellipsis`}>[{displayTag}]</span>
                <div className={`prose prose-invert max-w-none prose-sm flex-1 min-w-0 ${isErrorOrWarn ? 'text-rose-500' : 'text-white/85'}`}>
                  <MarkdownRenderer content={msg} />
                </div>
              </div>
            );
          }
          
          return (
            <div key={l.id || i} id={`log-${l.id}`} className="flex items-start gap-2.5 py-0.5 opacity-50">
              <span className={`${color} font-normal shrink-0 text-[11.5px] w-[85px] whitespace-nowrap overflow-hidden text-ellipsis`}>[{toTitleCase(tag)}]</span>
              <span className="text-gray-400 flex-1 min-w-0 break-words">{msg}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
});

// ─── TAB CONTENT MANAGER ─────────────────────────────────────────────────────

export const TabContent = memo(() => {
  const rightTab = useZenithStore(s => s.rightTab);
  const currentArtifacts = useZenithStore(s => s.currentArtifacts);
  const language = useZenithStore(s => s.language);
  const modifiedFiles = useZenithStore(s => s.modifiedFiles);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const dict = Dictionary[language as keyof typeof Dictionary] || Dictionary.en;
  const artifactContent = currentArtifacts[rightTab as keyof typeof currentArtifacts] || '';

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden">
      <div className="flex-1 flex flex-col">
        {rightTab === 'explorer' && <NeuralExplorer />}
        {rightTab === 'filelab' && <SovereignFileLab />}
        {rightTab === 'progress' && <ProcessLogTab />}
        {['plan', 'tasks', 'walkthrough'].includes(rightTab) && <ArtifactGallery content={artifactContent} type={rightTab} />}
        {rightTab === 'changes' && (
          <div className="flex-1 flex flex-col bg-black/20 p-4 space-y-3 overflow-y-auto custom-scroll">
            {modifiedFiles.length === 0 ? <div className="h-full flex items-center justify-center opacity-10"><CircuitBoard /></div> :
              modifiedFiles.map(path => (
                <button key={path} onClick={() => ZenithService.readFile(path).then(r => r.ok && setInspectedFile({ path, content: r.content }))} className="w-full p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-sky-500/10 text-left truncate">
                  <span className="text-[12px] font-bold text-white/80">{path.split('/').pop()}</span>
                </button>
              ))
            }
          </div>
        )}
        {rightTab === 'logs' && <MissionHistory />}
      </div>
      <FilePreview />
    </div>
  );
});
