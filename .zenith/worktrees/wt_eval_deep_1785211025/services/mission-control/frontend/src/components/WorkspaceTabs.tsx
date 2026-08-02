import React, { memo, useState, useEffect, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { Database, RefreshCw, Loader2, FolderOpen, Folder, FileCode2, ChevronRight, Terminal, Radio, ScrollText, FileText, Code2, Maximize2, GitBranch, CircuitBoard, X, Brain, ShieldCheck, Zap, Settings, AlertTriangle, Radar, Sparkles, Activity, ClipboardList } from 'lucide-react';
import { useZenithStore, Dictionary } from '../store/zenithStore';
import { ZenithService } from '../services/ZenithService';
import { MarkdownRenderer } from './zenith/MarkdownRenderer';
import { SurgicalDiff } from './zenith/LogElements';
import { SovereignFileLab } from './SovereignFileLab';
import { MissionHistory } from './zenith/MissionHistory';
import { ProposalPlanTab } from './zenith/ProposalPlanTab';

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
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const language = useZenithStore(s => s.language);

  const loadDir = () => {
    setLoading(true);
    setLoadError(null);
    ZenithService.listDir()
      .then(({ nodes, error }) => {
        setTree(nodes);
        setLoadError(error || (nodes.length === 0 ? 'Workspace trống hoặc chưa mount /workspace.' : null));
      })
      .finally(() => setLoading(false));
  };
  useEffect(() => { loadDir(); }, []);

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]">
      <div className="shrink-0 p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3"><Database className="w-4 h-4 text-sky-400" /><h3 className="text-[11px] font-black uppercase tracking-widest text-white/90">Neural Vault</h3></div>
        <button onClick={loadDir} className="p-2 text-white/20 hover:text-white"><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll">
        {loading ? (
          <div className="h-full flex items-center justify-center opacity-20"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : loadError ? (
          <div className="p-6 text-center text-[11px] text-amber-400/80 leading-relaxed">{loadError}</div>
        ) : tree.length === 0 ? (
          <div className="p-6 text-center text-[11px] text-white/30">Không có mục nào trong Neural Vault.</div>
        ) : (
          tree.map(node => <FileItem key={node.path} item={node} depth={0} onInspect={(p) => ZenithService.readFile(p).then(r => r?.content != null && setInspectedFile({ path: p, content: r.content }))} />)
        )}
      </div>
    </div>
  );
});

// ─── ARTIFACT GALLERY ────────────────────────────────────────────────────────

const ARTIFACT_EMPTY_HINT: Record<string, { icon: React.ReactNode; text: string }> = {
  tasks: { icon: <FileText className="w-10 h-10 text-amber-400/40" />, text: 'Chưa có nhiệm vụ. Sau khi Planner ghi task.md, nội dung sẽ hiện tại đây.' },
  walkthrough: { icon: <ScrollText className="w-10 h-10 text-cyan-400/40" />, text: 'Chưa có giải pháp. Kết quả JKAI dài hoặc walkthrough.md sẽ hiện ở đây sau mission.' },
};

const ARTIFACT_TYPE_META: Record<string, { icon: React.ReactNode; gradient: string; border: string }> = {
  tasks: {
    icon: <ClipboardList className="w-4 h-4" />,
    gradient: 'from-amber-500/10 to-transparent',
    border: 'border-amber-500/20',
  },
  walkthrough: {
    icon: <ScrollText className="w-4 h-4" />,
    gradient: 'from-cyan-500/10 to-transparent',
    border: 'border-cyan-500/20',
  },
};

export const ArtifactGallery = memo(({ content, type }: { content: string, type: string }) => {
  const { setInspectedFile } = useZenithStore();
  const meta = ARTIFACT_TYPE_META[type] || ARTIFACT_TYPE_META.walkthrough;
  const emptyHint = ARTIFACT_EMPTY_HINT[type];

  const artifacts = useMemo(() => {
    const raw = (content || '').trim();
    if (!raw || raw.startsWith('# Chưa có') || raw.startsWith('# No ')) return [];
    if (type === 'walkthrough') return [{ title: 'Giải pháp', body: raw }];
    const blocks = raw.split(/#\s+/).filter(Boolean);
    if (blocks.length <= 1 && !raw.includes('\n#')) return [{ title: type === 'tasks' ? 'Nhiệm vụ' : type, body: raw }];
    return blocks.map(b => ({ title: b.split('\n')[0].trim(), body: b.split('\n').slice(1).join('\n').trim() }));
  }, [content, type]);

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]">
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4 space-y-3">
        {artifacts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-4 px-6 text-center">
            <div className="opacity-30">{emptyHint?.icon}</div>
            <p className="text-[11px] leading-relaxed max-w-xs text-white/30">{emptyHint?.text || 'Chưa có dữ liệu.'}</p>
          </div>
        ) : (
          artifacts.map((art, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => setInspectedFile({ path: art.title, content: art.body })}
              className={`group rounded-xl bg-white/[0.02] border border-white/[0.06] overflow-hidden cursor-pointer transition-all hover:bg-white/[0.04] ${type === 'tasks' ? 'hover:border-amber-500/30' : 'hover:border-cyan-500/30'}`}
            >
              <div className={`bg-gradient-to-r ${meta.gradient} p-4`}>
                <div className="flex items-center gap-2.5 mb-3">
                  <div className={`${type === 'tasks' ? 'text-amber-400' : 'text-cyan-400'}`}>{meta.icon}</div>
                  <h4 className="text-[13px] font-bold text-white/90">{art.title}</h4>
                </div>
                <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed text-white/50 line-clamp-4 group-hover:line-clamp-none transition-all">
                  <MarkdownRenderer content={art.body} />
                </div>
                <div className="mt-3 flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-white/20 group-hover:text-white/40 transition-colors">
                  <Maximize2 className="w-3 h-3" />
                  Xem chi tiết
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
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
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="absolute inset-0 z-50 bg-[#060910] flex flex-col min-h-0 overflow-hidden">
      <div className="shrink-0 p-4 border-b border-white/5 flex items-center justify-between bg-black/40">
        <div className="flex items-center gap-3">
          <FileCode2 className="w-4 h-4 text-sky-400" />
          <span className="text-[11px] font-black uppercase tracking-widest text-white/90 truncate max-w-[200px]">{inspectedFile.path.split('/').pop()}</span>
        </div>
        <button onClick={() => setInspectedFile(null)} className="p-2 text-white/20 hover:text-rose-400 transition-colors"><X className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4">
        <MarkdownRenderer content={`\`\`\`typescript\n${inspectedFile.content}\n\`\`\``} />
      </div>
    </motion.div>
  );
});

// ─── PROCESS LOG TAB (TIẾN TRÌNH) — CLI STREAM ─────────────────────────────

const getCliColor = (tag: string, msg: string = '') => {
  const t = tag.toUpperCase();
  const m = msg.toUpperCase();
  if (t === 'JKAI' || t === 'MISSION_RESULT' || t === 'RESULT' || t === 'DONE' || t === 'ZENITH') return 'text-cyan-400';
  if (t === 'CHAT_INTEL' || t.includes('SUMMARIZER') || t.includes('LEGAL') || t.includes('THU_KY')) return 'text-fuchsia-400';
  if (t === 'PROGRESS' || t.includes('EXECUTOR') || t.includes('ALPHA') || t.includes('BETA')) return 'text-blue-400';
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
  return ['MISSION_RESULT', 'RESULT', 'DONE', 'ERROR', 'WARN', 'WARNING', 'ZENITH'].includes(t) || t.startsWith('MASTER') || isPhase;
};

const toTitleCase = (str: string, lang: string = 'vi') => {
  if (!str) return '';
  const upper = str.toUpperCase();
  if (upper === 'JKAI') return 'JKAI';
  
  if (lang === 'vi') {
    if (
      upper.includes('GATEWAY') || upper.includes('RECEPTIONIST') || 
      upper.includes('LE_TAN')
    ) return 'Ban Trợ Lý';
    if (
      upper.includes('DATA_SCOUT') || upper.includes('RESEARCH') || upper.includes('SEARCH') || 
      upper.includes('ANTIGRAVITY') || upper.includes('FORGE') || 
      upper.includes('KIẾN TẠO') || upper.includes('KIENTAO') || 
      upper.includes('TÌNH BÁO') || upper.includes('TINHBAO') || upper.includes('CREATOR')
    ) return 'Ban Trợ Lý';
    if (
      upper.includes('SYSTEM') || upper.includes('ADMIN') || upper.includes('HANH_CHINH') ||
      upper.includes('SUMMARIZER') || upper.includes('SYNTHESIS') || 
      upper.includes('LEGAL') || upper.includes('THU_KY') || 
      upper === 'CHAT_INTEL'
    ) return 'Ban Thư Ký';
    if (upper.includes('PLANNER') || upper.includes('THOUGHT') || upper.includes('BAN_KE_HOACH') || upper.includes('TƯ DUY') || upper.includes('STEWARD') || upper.includes('MEMORY') || upper.includes('QUẢN GIA')) return 'Ban Kế Hoạch';
    if (upper.includes('EXECUTOR') || upper.includes('ALPHA') || upper.includes('BETA') || upper === 'PROGRESS' || upper === 'TIẾN TRÌNH' || upper === 'TIẾN_TRÌNH') return 'Ban Thực Thi';
    if (
      upper === 'JKAI' || upper.includes('MISSION_RESULT') || 
      upper.includes('RESULT') || upper.includes('DONE') || 
      upper === 'ZENITH'
    ) return 'JKAI';
    if (upper.includes('CRITIC') || upper.includes('AUDIT') || upper.includes('REVIEW') || upper.includes('GUARDRAIL') || upper.includes('PHAN_BIEN') || upper.includes('PHẢN BIỆN') || upper.includes('BAN_KIEM_SOAT')) return 'Ban Kiểm Soát';
    if (upper.includes('MASTER') || upper.includes('USER')) return 'Master';
    return 'Ban Trợ Lý';
  } else {
    if (
      upper.includes('GATEWAY') || upper.includes('RECEPTIONIST') || 
      upper.includes('LE_TAN')
    ) return 'Assistant Dept';
    if (upper.includes('PLANNER') || upper.includes('THOUGHT') || upper.includes('STEWARD') || upper.includes('MEMORY')) return 'Planning Dept';
    if (upper.includes('EXECUTOR') || upper.includes('ALPHA') || upper.includes('BETA') || upper === 'PROGRESS' || upper === 'TIẾN TRÌNH' || upper === 'TIẾN_TRÌNH') return 'Execution Dept';
    if (
      upper.includes('SUMMARIZER') || upper.includes('SYNTHESIS') || 
      upper.includes('LEGAL') || upper.includes('THU_KY') || 
      upper === 'CHAT_INTEL'
    ) return 'Secretariat';
    if (
      upper === 'JKAI' || upper.includes('MISSION_RESULT') || 
      upper.includes('RESULT') || upper.includes('DONE') || 
      upper === 'ZENITH'
    ) return 'JKAI';
    if (upper.includes('CRITIC') || upper.includes('AUDIT') || upper.includes('REVIEW') || upper.includes('GUARDRAIL')) return 'Audit Dept';
    if (
      upper.includes('DATA_SCOUT') || upper.includes('RESEARCH') || upper.includes('SEARCH') || 
      upper.includes('ANTIGRAVITY') || upper.includes('FORGE') || 
      upper.includes('KIẾN TẠO') || upper.includes('KIENTAO') || 
      upper.includes('TÌNH BÁO') || upper.includes('TINHBAO') ||
      upper.includes('SYSTEM') || upper.includes('ADMIN') || upper.includes('HANH_CHINH')
    ) return 'Administrative Dept';
    if (upper.includes('MASTER') || upper.includes('USER')) return 'Master';
    return 'Assistant Dept';
  }
  
  return str.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('_');
};

/** Map display label → node color class to keep left column consistent with DAG nodes */
const TAG_COLOR_MAP: Record<string, string> = {
  'Master':           'text-amber-400',
  'JKAI':             'text-cyan-400',
  'Ban Kế Hoạch':     'text-blue-300', // Professional blue
  'Ban Kiểm Soát':    'text-orange-400', // Professional amber/orange
  'Ban Thực Thi':     'text-emerald-400', // Professional green
  'Ban Trợ Lý':       'text-teal-300', // Subtle teal
  'Ban Thư Ký':       'text-fuchsia-400', // Kept fuchsia per request
  'Ban Hành Chính':   'text-slate-300', // Subtle corporate slate
};

/** Format timestamp → Vietnamese locale HH:mm:ss DD/MM */
const formatVnTime = (ts: number | undefined): string => {
  if (!ts) return '';
  const d = new Date(ts < 1e12 ? ts * 1000 : ts);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  return `${hh}:${mm}:${ss} ${dd}/${mo}`;
};

const ProcessLogTab = memo(() => {
  const progressLogs = useZenithStore(s => s.progressLogs);
  const language = useZenithStore(s => s.language);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sortedLogs = useMemo(() => {
    return [...progressLogs].sort((a, b) => (a.ts || 0) - (b.ts || 0));
  }, [progressLogs]);

  const maxTagWidth = useMemo(() => {
    let longestLength = 0;
    sortedLogs.forEach((l: any) => {
      const tag = (l.tag || 'SYS').toUpperCase();
      const msg = (l.msg || '').replace(/\[⏱️\s*[\d.]+\s*s\]/g, '').trim();
      if (!msg) return;

      const important = isImportantTag(tag, msg);
      const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER');

      let displayTag = '';
      if (important || isThought) {
        displayTag = (isThought && l.source && l.source.toUpperCase() !== tag)
          ? `${toTitleCase(tag, language)}:${toTitleCase(l.source, language)}`
          : toTitleCase(tag, language);
      } else {
        displayTag = toTitleCase(tag, language);
      }
      
      const fullLabel = `[${displayTag}]`;
      if (fullLabel.length > longestLength) {
        longestLength = fullLabel.length;
      }
    });

    if (longestLength === 0) return 85;
    // Estimate width based on character count: ~7.5px per character + 12px padding/bracket spacing
    return Math.max(85, longestLength * 7.5 + 12);
  }, [sortedLogs, language]);

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
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#060910]/60">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll pt-4 px-4 pb-16"
      >
      <div className="flex flex-col font-sans font-[300] tracking-wide text-[13px] leading-relaxed">
        {sortedLogs.length === 0 && (
          <span className="text-gray-500 italic">Chờ tín hiệu nơ-ron...</span>
        )}
        {sortedLogs.map((l: any, i: number) => {
          const tag = (l.tag || 'SYS').toUpperCase();
          const msg = (l.msg || '')
            .replace(/\[⏱️\s*[\d.]+\s*s\]/g, '')
            .replace(/📥\s*\[GATEWAY\]\s*/g, '')
            .replace(/💎🫡\s*\[ZENITH\]:\s*/g, '')
            .replace(/💎\s*\[ZENITH\]:\s*/g, '')
            .replace(/⚙️\s*/g, '')
            .replace(/⚔️\s*\[[^\]]+\]\s*/g, '') // e.g. ⚔️ [T4: SURGERY]
            .replace(/\[T\d+:\s*[^\]]+\]\s*/g, '') // e.g. [T4: SURGERY]
            .replace(/ZENITH_\d+_([0-9a-fA-F]{4,8})/g, (match: string, hex: string) => `Z-${hex.slice(0,4).toUpperCase()}`)
            .replace(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/g, '$3/$2/$1 $4:$5:$6') // ISO → VN
            .replace(/(\d{4})-(\d{2})-(\d{2})/g, '$3/$2/$1') // YYYY-MM-DD → DD/MM/YYYY
            .trim();
          if (!msg) return null;
          
          const isJkaiOrMaster = tag === 'JKAI' || tag === 'MISSION_RESULT' || tag === 'RESULT' || tag === 'DONE' || tag === 'ZENITH' || tag === 'MASTER' || tag.startsWith('MASTER');
          const isErrorOrWarn = tag === 'ERROR' || tag === 'WARN' || tag === 'WARNING';
          
          const baseTag = toTitleCase(tag, language);
          const displayTag = (tag.includes('THOUGHT') || tag.includes('PLANNER')) && l.source && l.source.toUpperCase() !== tag
            ? `${baseTag}:${toTitleCase(l.source, language)}`
            : baseTag;

          // Color: match display label to DAG node color
          let tagColor = TAG_COLOR_MAP[baseTag] ?? 'text-gray-400';
          let msgColor = 'text-gray-400';
          let isBold = false;

          if (isJkaiOrMaster && tag !== 'MASTER' && !tag.startsWith('MASTER')) {
            tagColor = 'text-cyan-400'; msgColor = 'text-white/85'; isBold = true;
          } else if (tag === 'MASTER' || tag.startsWith('MASTER')) {
            tagColor = 'text-amber-400'; msgColor = 'text-white/85'; isBold = true;
          } else if (isErrorOrWarn) {
            tagColor = 'text-rose-500'; msgColor = 'text-rose-400'; isBold = false;
          } else if (displayTag === 'JKAI') {
            tagColor = 'text-cyan-400'; msgColor = 'text-white/85'; isBold = true;
          }

          const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER');

          return (
            <div 
              key={l.id || i} 
              id={`log-${l.id}`} 
              className={`my-1 flex items-start gap-2.5 ${isJkaiOrMaster ? '' : 'opacity-70'}`}
            >
              {/* Timestamp column */}
              <span className="shrink-0 text-[10px] text-white/20 mt-[3px] w-[70px] tabular-nums leading-tight">
                {formatVnTime(l.ts)}
              </span>
              <span 
                style={{ width: `${maxTagWidth}px` }} 
                className={`${tagColor} ${isBold ? 'font-semibold' : 'font-normal'} shrink-0 text-[11.5px] mt-[2px] whitespace-nowrap overflow-hidden text-ellipsis`}
              >
                [{displayTag}]
              </span>
              <div className={`prose prose-invert compact-prose max-w-none prose-sm flex-1 min-w-0 ${msgColor} font-normal`}>
                <MarkdownRenderer content={msg} />
              </div>
            </div>
          );
        })}
      </div>
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
  const fileEdits = useZenithStore(s => s.fileEdits);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const dict = Dictionary[language as keyof typeof Dictionary] || Dictionary.en;
  const artifactContent = currentArtifacts[rightTab as keyof typeof currentArtifacts] || '';

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden min-h-0">
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {rightTab === 'explorer' && <NeuralExplorer />}
        {rightTab === 'filelab' && <SovereignFileLab />}
        {rightTab === 'progress' && <ProcessLogTab />}
        {rightTab === 'plan' && <ProposalPlanTab />}
        {['tasks', 'walkthrough'].includes(rightTab) && <ArtifactGallery content={artifactContent} type={rightTab} />}
        {rightTab === 'changes' && (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-black/20">
            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4 space-y-4">
            {fileEdits.length === 0 && modifiedFiles.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-3 px-6 text-center opacity-40">
                <CircuitBoard className="w-12 h-12" />
                <p className="text-[11px] leading-relaxed max-w-xs">
                  Chưa có thay đổi file. Khi JKAI sửa code (agent loop / patch), diff sẽ hiện tại đây qua sự kiện file_edit.
                </p>
              </div>
            ) : (
              <>
                {fileEdits.map((e, i) => (
                  <div key={`${e.path}-${e.ts}-${i}`} className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
                    <button
                      type="button"
                      onClick={() => ZenithService.readFile(e.path).then(r => r?.content && setInspectedFile({ path: e.path, content: r.content }))}
                      className="w-full px-4 py-3 flex items-center justify-between hover:bg-sky-500/10 text-left border-b border-white/5"
                    >
                      <span className="text-[12px] font-bold text-sky-300 truncate">{e.path}</span>
                      <span className="text-[9px] uppercase text-white/30 shrink-0 ml-2">Mở tab</span>
                    </button>
                    {e.diff ? <SurgicalDiff diff={e.diff} /> : null}
                  </div>
                ))}
                {modifiedFiles.filter(p => !fileEdits.some(e => e.path === p)).map(path => (
                  <button key={path} type="button" onClick={() => ZenithService.readFile(path).then(r => r?.content && setInspectedFile({ path, content: r.content }))} className="w-full p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-sky-500/10 text-left truncate">
                    <span className="text-[12px] font-bold text-white/80">{path.split('/').pop()}</span>
                  </button>
                ))}
              </>
            )}
            </div>
          </div>
        )}
        {rightTab === 'logs' && <MissionHistory />}
      </div>
      <FilePreview />
    </div>
  );
});
