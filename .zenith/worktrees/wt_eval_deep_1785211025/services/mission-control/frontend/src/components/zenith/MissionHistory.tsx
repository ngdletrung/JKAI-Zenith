import React, { memo, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ScrollText, Clock, ChevronRight, Search, Trash2, RefreshCw, CheckCircle2, XCircle, AlertTriangle, Ban } from 'lucide-react';
import { ZenithService } from '../../services/ZenithService';
import { useZenithStore } from '../../store/zenithStore';
import toast from 'react-hot-toast';

const TRANSLATIONS = {
  vi: {
    annals: "Biên niên sử Zenith",
    purge: "Thanh tẩy toàn bộ",
    confirm: "Xác nhận",
    cancel: "Huỷ",
    search: "Truy lục sứ mệnh...",
    scanning: "Đang rà soát Biên niên sử...",
    no_records: "Không tìm thấy hồ sơ",
    confirm_delete: "Master có chắc chắn muốn xoá sứ mệnh này khỏi biên niên sử?",
    deleted: "Đã xoá sứ mệnh.",
    purged: "Biên niên sử đã được thanh tẩy.",
    report: "Báo cáo Sứ mệnh",
    goal: "Mục tiêu",
    status: "Trạng thái",
    time: "Thời gian",
    details: "Chi tiết Thực thi",
    no_logs: "Không tìm thấy nhật ký thực thi.",
    success: "Thành công",
    failed: "Thất bại",
    running: "Đang chạy",
    pending_status: "Chờ",
    logs_count: "nhật ký",
    duration: "Thời lượng",
    summary: "Tổng quan",
    execution: "Quá trình thực thi"
  },
  en: {
    annals: "Zenith Chronicles",
    purge: "Purge All Records",
    confirm: "Confirm",
    cancel: "Cancel",
    search: "Chronicle Search...",
    scanning: "Scanning Vault...",
    no_records: "No Records Found",
    confirm_delete: "Are you sure you want to remove this mission from the chronicles, Master?",
    deleted: "Mission record deleted.",
    purged: "Annals have been purged.",
    report: "Mission Report",
    goal: "Goal",
    status: "Status",
    time: "Time",
    details: "Execution Details",
    no_logs: "No logs found.",
    success: "Success",
    failed: "Failed",
    running: "Running",
    pending_status: "Pending",
    logs_count: "logs",
    duration: "Duration",
    summary: "Summary",
    execution: "Execution Timeline"
  }
};

const TAG_COLORS: Record<string, string> = {
  JKAI: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  MASTER: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  DONE: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  RESULT: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  MISSION_RESULT: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  ERROR: 'text-rose-500 bg-rose-500/10 border-rose-500/30',
  WARN: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  SYSTEM: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
  EXECUTOR: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  PLANNER: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
  THOUGHT: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
  SEARCH: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
  FILE: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  TOOL: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  ZENITH: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
};

const formatVnTime = (ts: number): string => {
  try {
    const d = new Date(ts < 1e12 ? ts * 1000 : ts);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const mo = String(d.getMonth() + 1).padStart(2, '0');
    return `${hh}:${mm}:${ss} ${dd}/${mo}`;
  } catch { return 'N/A'; }
};

const formatDuration = (start: number, end?: number): string => {
  const diff = ((end || Date.now()) - (start < 1e12 ? start * 1000 : start)) / 1000;
  if (diff < 60) return `${Math.round(diff)}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${Math.round(diff % 60)}s`;
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
};

export const MissionHistory = memo(() => {
  const [missions, setMissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isConfirmingClear, setIsConfirmingClear] = useState(false);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const language = useZenithStore(s => s.language);
  const dict = TRANSLATIONS[language as keyof typeof TRANSLATIONS] || TRANSLATIONS.en;

  const loadMissions = async () => {
    setLoading(true);
    const data = await ZenithService.listMissions();
    setMissions(Array.isArray(data) ? data : []);
    setLoading(false);
  };

  useEffect(() => { loadMissions(); }, []);

  useEffect(() => {
    const handleReload = () => loadMissions();
    window.addEventListener('zenith:reload-missions', handleReload);
    return () => window.removeEventListener('zenith:reload-missions', handleReload);
  }, []);

  const filteredMissions = missions.filter(m =>
    (m.title || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (m.goal || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getMissionStatus = (m: any): { label: string; color: string; icon: React.ReactNode } => {
    const status = (m.status || '').toLowerCase();
    const logs = m.logs || [];
    const hasError = logs.some((l: any) => (l.tag || '').toUpperCase() === 'ERROR');
    const hasResult = logs.some((l: any) => (l.tag || '').toUpperCase() === 'DONE' || (l.tag || '').toUpperCase() === 'RESULT');
    if (status === 'success' || hasResult) return { label: dict.success, color: 'text-emerald-400', icon: <CheckCircle2 className="w-3.5 h-3.5" /> };
    if (status === 'failed' || hasError) return { label: dict.failed, color: 'text-rose-400', icon: <XCircle className="w-3.5 h-3.5" /> };
    if (status === 'running') return { label: dict.running, color: 'text-cyan-400', icon: <AlertTriangle className="w-3.5 h-3.5" /> };
    return { label: dict.pending_status, color: 'text-slate-400', icon: <Ban className="w-3.5 h-3.5" /> };
  };

  const renderReport = (data: any) => {
    const logs = data.logs || [];
    const status = getMissionStatus(data);
    const lines = [];
    lines.push(`# ${data.title}\n`);
    lines.push(`> **${dict.goal}:** ${data.goal || 'N/A'}\n`);
    const timeStr = formatVnTime(data.ts);
    lines.push(`> **${dict.status}:** ${status.label} | **${dict.time}:** ${timeStr} | **${logs.length} ${dict.logs_count}**\n`);
    lines.push(`---\n`);
    if (logs.length > 0) {
      lines.push(`## ${dict.execution}\n`);
      logs.forEach((l: any) => {
        const tag = (l.tag || 'SYS').toUpperCase();
        const ts = l.ts ? formatVnTime(l.ts) : '';
        const colorClass = TAG_COLORS[tag] || 'text-slate-400 bg-slate-500/10 border-slate-500/30';
        const displayTag = tag === 'JKAI' ? 'JKAI' : tag === 'MASTER' ? 'Master' : tag;
        lines.push(`- \`${ts}\` **<span style="color:var(--${tag === 'JKAI' || tag === 'DONE' ? 'cyan' : tag === 'MASTER' ? 'amber' : tag === 'ERROR' ? 'rose' : tag === 'WARN' ? 'orange' : tag === 'EXECUTOR' || tag === 'FILE' ? 'emerald' : tag === 'SEARCH' ? 'sky' : tag === 'TOOL' ? 'purple' : tag === 'PLANNER' || tag === 'THOUGHT' ? 'indigo' : 'slate'}-400)">[${displayTag}]</span>**: ${l.msg}`);
      });
    }
    return lines.join('\n');
  };

  const handleInspect = async (mid: string) => {
    const data = await ZenithService.getMission(mid);
    if (!data || data.error) return;
    const loadMissionData = useZenithStore.getState().loadMissionData;
    const setTab = useZenithStore.getState().setTab;
    await loadMissionData(data);
    const walk = data.artifacts?.walkthrough;
    if (walk && String(walk).trim().length > 20) {
      setTab('walkthrough');
    } else {
      const reportMd = renderReport(data);
      setInspectedFile({ path: `${dict.report}: ${data.title}`, content: reportMd });
    }
  };

  const handleDelete = async (e: React.MouseEvent, mid: string) => {
    e.stopPropagation();
    if (window.confirm(dict.confirm_delete)) {
      const res = await ZenithService.deleteMission(mid);
      if (res.ok) { toast.success(dict.deleted); loadMissions(); }
    }
  };

  const handleClearAll = async () => {
    const res = await ZenithService.clearMissions();
    if (res.ok) { toast.success(dict.purged); setIsConfirmingClear(false); loadMissions(); }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]">
      <div className="shrink-0 p-4 border-b border-white/5 flex flex-col gap-4 bg-black/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ScrollText className="w-4 h-4 text-amber-400" />
            <h3 className="text-[11px] font-black uppercase tracking-widest text-white/90">{dict.annals}</h3>
          </div>
          <div className="flex items-center gap-2">
            {!isConfirmingClear ? (
              <button onClick={() => setIsConfirmingClear(true)} className="p-2 text-white/10 hover:text-rose-400 transition-all" title={dict.purge}>
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            ) : (
              <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-2">
                <button onClick={handleClearAll} className="px-2 py-1 bg-rose-500/20 text-rose-400 text-[9px] font-black uppercase rounded border border-rose-500/30 hover:bg-rose-500/40">{dict.confirm}</button>
                <button onClick={() => setIsConfirmingClear(false)} className="text-[9px] text-white/40 uppercase font-black px-1">{dict.cancel}</button>
              </div>
            )}
            <button onClick={loadMissions} className="p-2 text-white/20 hover:text-white transition-all">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20" />
          <input type="text" placeholder={dict.search} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full bg-white/5 border border-white/5 rounded-xl py-2 pl-9 pr-4 text-[11px] text-white/60 focus:outline-none focus:border-amber-500/40 transition-all" />
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-2">
        {loading && missions.length === 0 ? (
          <div className="h-full flex items-center justify-center opacity-10 flex-col gap-4">
            <RefreshCw className="w-8 h-8 animate-spin" />
            <span className="text-[10px] font-black uppercase tracking-widest">{dict.scanning}</span>
          </div>
        ) : filteredMissions.length === 0 ? (
          <div className="h-full flex items-center justify-center opacity-10 flex-col gap-4">
            <Search className="w-8 h-8" />
            <span className="text-[10px] font-black uppercase tracking-widest">{dict.no_records}</span>
          </div>
        ) : (
          <div className="space-y-2 p-1">
            {filteredMissions.map((m) => {
              const st = getMissionStatus(m);
              const logs = m.logs || [];
              const ts = m.ts ? (m.ts < 1e12 ? m.ts * 1000 : m.ts) : Date.now();
              return (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={() => handleInspect(m.id)}
                  className="group relative flex flex-col gap-2.5 p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-amber-500/20 transition-all cursor-pointer"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <div className={`shrink-0 ${st.color}`}>{st.icon}</div>
                      <span className="text-[13px] font-bold text-white/90 truncate">{m.title}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`text-[10px] font-semibold ${st.color}`}>{st.label}</span>
                      <span className="text-[10px] text-white/25 font-mono tabular-nums">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {new Date(ts).toLocaleTimeString(language === 'vi' ? 'vi-VN' : 'en-US', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                  {m.goal && (
                    <p className="text-[11px] text-white/30 line-clamp-1 pl-7">{m.goal}</p>
                  )}
                  <div className="flex items-center gap-3 pl-7">
                    <span className="text-[9px] text-white/20 font-mono">{logs.length} {dict.logs_count}</span>
                    {m.ts && (
                      <>
                        <span className="text-[9px] text-white/10">|</span>
                        <span className="text-[9px] text-white/20 font-mono">{formatDuration(m.ts, m.completed_at)}</span>
                      </>
                    )}
                  </div>
                  <div className="absolute right-3 bottom-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                    <button onClick={(e) => handleDelete(e, m.id)} className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20">
                      <Trash2 className="w-3 h-3" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-amber-500" />
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
});
