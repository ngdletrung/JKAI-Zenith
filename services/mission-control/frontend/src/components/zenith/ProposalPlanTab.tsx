import React, { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, AlertTriangle, ShieldCheck, CheckCircle2, XCircle, ChevronDown, ChevronUp, Clock, Activity } from 'lucide-react';
import { useZenithStore, BackgroundProposal } from '../../store/zenithStore';
import { MarkdownRenderer } from './MarkdownRenderer';
import { NuclearApprovalPad } from './NuclearApprovalPad';

const TYPE_CONFIG: Record<string, { icon: React.ReactNode; accent: string; label: string }> = {
  KNOWLEDGE_DISTILL: {
    icon: <Sparkles className="w-5 h-5" />,
    accent: 'from-sky-500/20 to-transparent border-sky-500/30',
    label: 'Đúc kết tri thức',
  },
  SELF_SURGERY: {
    icon: <AlertTriangle className="w-5 h-5" />,
    accent: 'from-rose-500/20 to-transparent border-rose-500/30',
    label: 'Phẫu thuật hệ thống',
  },
  SYSTEM_IMPROVEMENT: {
    icon: <Activity className="w-5 h-5" />,
    accent: 'from-amber-500/20 to-transparent border-amber-500/30',
    label: 'Cải tiến hệ thống',
  },
  SYSTEM_AUDIT: {
    icon: <ShieldCheck className="w-5 h-5" />,
    accent: 'from-cyan-500/20 to-transparent border-cyan-500/30',
    label: 'Giám định hệ thống',
  },
};

const getConfig = (type: string) => {
  return TYPE_CONFIG[type] || { icon: <ShieldCheck className="w-5 h-5" />, accent: 'from-amber-500/20 to-transparent border-amber-500/30', label: 'Đề xuất' };
};

const formatTimeAgo = (ts: number): string => {
  const diff = Date.now() - (ts < 1e12 ? ts * 1000 : ts);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Vừa xong';
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return `${Math.floor(hours / 24)} ngày trước`;
};

export const ProposalPlanTab = memo(() => {
  const { backgroundProposals, removeBackgroundProposal, updateProposalStatus, language } = useZenithStore();
  const [authProposal, setAuthProposal] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const uniqueProposals = React.useMemo(() => {
    if (!backgroundProposals) return [];
    const map = new Map<string, BackgroundProposal>();
    backgroundProposals.forEach(p => { if (p && p.id) map.set(p.id, p); });
    return Array.from(map.values());
  }, [backgroundProposals]);

  if (!uniqueProposals || uniqueProposals.length === 0) return null;

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleApprove = async (proposal: BackgroundProposal, code?: string) => {
    if (proposal.is_red_zone && !code) { setAuthProposal(proposal.id); return; }
    try {
      updateProposalStatus(proposal.id, 'executing');
      const res = await fetch('/api/proposals/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposal.id, code: code || '' })
      });
      const responseData = await res.json();
      if (res.ok && (responseData?.ok === true || responseData?.status === 'approved')) {
        removeBackgroundProposal(proposal.id);
        setAuthProposal(null);
      } else {
        updateProposalStatus(proposal.id, 'pending');
      }
    } catch {
      updateProposalStatus(proposal.id, 'pending');
    }
  };

  const handleReject = async (id: string) => {
    try {
      const res = await fetch('/api/proposals/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: id })
      });
      if (res.ok) removeBackgroundProposal(id);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]/90 relative">
      <div className="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-white/5 bg-[#020408]/95 z-10">
        <Sparkles className="w-4 h-4 text-fuchsia-400" />
        <h3 className="text-[12px] font-black uppercase tracking-widest text-white/90">Đề xuất từ Hệ thống</h3>
        <div className="ml-auto bg-fuchsia-500/20 text-fuchsia-400 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-fuchsia-500/30">
          {uniqueProposals.length}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4 space-y-3">
        <AnimatePresence>
          {uniqueProposals.map((p) => {
            const cfg = getConfig(p.proposal_type);
            const isExpanded = expandedIds.has(p.id);
            const isLong = p.description && p.description.length > 500;
            const isExecuting = p.status === 'executing';

            return (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                className={`rounded-xl bg-white/[0.02] border border-white/[0.06] overflow-hidden transition-all hover:bg-white/[0.03] ${isExecuting ? 'ring-1 ring-emerald-500/30' : ''}`}
              >
                <div className={`bg-gradient-to-r ${cfg.accent} p-5 pb-4`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`shrink-0 ${p.is_red_zone ? 'text-rose-400' : p.proposal_type === 'KNOWLEDGE_DISTILL' ? 'text-sky-400' : p.proposal_type === 'SELF_SURGERY' ? 'text-rose-400' : p.proposal_type === 'SYSTEM_IMPROVEMENT' ? 'text-amber-400' : 'text-cyan-400'}`}>
                        {cfg.icon}
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-[14px] font-bold text-white/90 truncate">{p.title}</h4>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[9px] font-mono text-white/30 uppercase tracking-wider">{cfg.label}</span>
                          <span className="text-[9px] text-white/10">|</span>
                          <span className="text-[9px] font-mono text-white/30">{p.source_module}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {p.is_red_zone && (
                        <div className="bg-rose-500/15 text-rose-400 text-[9px] font-bold px-2 py-0.5 rounded-full border border-rose-500/30 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                          Vùng đỏ
                        </div>
                      )}
                      {isExecuting && (
                        <div className="bg-emerald-500/15 text-emerald-400 text-[9px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1">
                          <Activity className="w-3 h-3 animate-pulse" />
                          Đang thực thi
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-3 pl-8">
                    <div className={isLong && !isExpanded ? 'max-h-[200px] overflow-hidden relative' : ''}>
                      <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed text-white/70">
                        <MarkdownRenderer content={p.description} />
                      </div>
                      {isLong && !isExpanded && (
                        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-[#020408] to-transparent" />
                      )}
                    </div>
                    {isLong && (
                      <button onClick={() => toggleExpand(p.id)} className="mt-2 text-[10px] font-bold text-white/30 hover:text-white/60 transition-colors flex items-center gap-1">
                        {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        {isExpanded ? 'Thu gọn' : 'Xem thêm'}
                      </button>
                    )}
                  </div>

                  <div className="mt-3 pl-8 flex items-center gap-3 text-[10px] text-white/20 font-mono">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimeAgo(p.created_at)}</span>
                  </div>
                </div>

                {authProposal === p.id ? (
                  <div className="px-5 pb-4 animate-in fade-in slide-in-from-bottom-2">
                    <div className="pt-3 border-t border-white/5">
                      <NuclearApprovalPad
                        language={language || 'en'}
                        onApprove={(code) => handleApprove(p, code)}
                        onCancel={() => setAuthProposal(null)}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="px-5 pb-4">
                    <div className="flex items-center gap-3 pt-3 border-t border-white/5">
                      <button
                        onClick={() => handleApprove(p)}
                        disabled={isExecuting}
                        className="flex-1 py-2.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/25 text-emerald-400 text-[11px] font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        {isExecuting ? 'Đang thực thi...' : 'Phê duyệt'}
                      </button>
                      <button
                        onClick={() => handleReject(p.id)}
                        disabled={isExecuting}
                        className="px-5 py-2.5 rounded-lg bg-white/5 hover:bg-rose-500/15 border border-transparent hover:border-rose-500/25 text-white/40 hover:text-rose-400 text-[11px] font-bold uppercase tracking-wider transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                      >
                        <XCircle className="w-4 h-4" />
                        Bác bỏ
                      </button>
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
});
