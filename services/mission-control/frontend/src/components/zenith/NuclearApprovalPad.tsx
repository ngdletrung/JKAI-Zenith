import React, { useState, useRef, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, ShieldAlert, Target, AlertTriangle, Lock, XCircle, Swords, Loader2, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { ZenithService } from '../../services/ZenithService';

export const NuclearApprovalPad = memo(({ language, task_id }: { language: string, task_id?: string }) => {
  const [code, setCode] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleApprove = async () => {
    if (!code) return;
    setIsVerifying(true);
    setError(null);
    try {
      let targetId = task_id;
      if (!targetId) {
        const pending = await ZenithService.getPendingHitl();
        const taskIds = Object.keys(pending);
        targetId = taskIds[0];
      }

      const res = await ZenithService.approveHitl(targetId || 'broadcast', code);
      if (res.status === 'approved' || res.ok) {
        toast.success(language === 'vi' ? '🔱 SOVEREIGN SEAL ACCEPTED! ĐANG TRIỂN KHAI...' : '🔱 SOVEREIGN SEAL ACCEPTED! DEPLOYING...', { id: 'nuclear-success' });
        setIsApproved(true);
      } else {
        setError(language === 'vi' ? 'MẬT MÃ CHỦ QUYỀN KHÔNG KHỚP. TRUY CẬP BỊ TỪ CHỐI.' : 'SOVEREIGN KEY MISMATCH. ACCESS DENIED.');
        toast.error(language === 'vi' ? '❌ XÁC THỰC THẤT BẠI' : '❌ AUTHENTICATION FAILED', { id: 'nuclear-fail' });
        setCode('');
        setTimeout(() => setError(null), 2000);
      }
    } catch (e) {
      toast.error('Uplink failed');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleReject = async () => {
    setIsVerifying(true);
    try {
      let targetId = task_id;
      if (!targetId) {
        const pending = await ZenithService.getPendingHitl();
        const taskIds = Object.keys(pending);
        targetId = taskIds[0];
      }
      await ZenithService.rejectHitl(targetId || 'broadcast');
      toast.success(language === 'vi' ? '🚫 ĐỀ XUẤT ĐÃ BỊ BÁC BỎ THEO LỆNH MASTER.' : '🚫 PROPOSAL REJECTED BY MASTER COMMAND.', { id: 'nuclear-reject' });
      window.location.reload();
    } catch (e) {
      toast.error('Reject failed');
    } finally {
      setIsVerifying(false);
    }
  };

  if (isApproved) {
    return (
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="mt-4">
        <div className="p-4 rounded-2xl bg-emerald-500/[0.05] border border-emerald-500/30 backdrop-blur-3xl flex items-center justify-between shadow-[0_0_50px_rgba(16,185,129,0.1)]">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <span className="text-[9px] font-black uppercase tracking-[0.4em] text-emerald-400 block mb-0.5">SOVEREIGN AUTHENTICATED</span>
              <h3 className="text-base font-black text-white/90 leading-tight">MẬT MÃ TRÙNG KHỚP - ĐANG THỰC THI</h3>
              <p className="text-[9px] text-emerald-400/50 font-mono mt-0.5 opacity-60">Verified at: {new Date().toLocaleTimeString()} | Status: Deploying</p>
            </div>
          </div>
          <div className="flex flex-col items-center gap-1 opacity-50">
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={error ? { x: [-10, 10, -10, 10, 0], opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
      transition={error ? { duration: 0.4 } : {}}
      className="mt-4 relative group max-w-[420px]"
    >
      <div className={`absolute inset-[-10px] ${error ? 'bg-red-500/10' : 'bg-[#fbbf24]/5'} blur-[30px] rounded-full opacity-40 animate-pulse`} />

      <div className={`relative p-4 rounded-2xl bg-[#0a0f1d]/90 border ${error ? 'border-red-500/50' : 'border-[#fbbf24]/20'} backdrop-blur-3xl shadow-2xl overflow-hidden`}>
        <motion.div
          animate={{ top: ['0%', '100%', '0%'] }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          className={`absolute left-0 right-0 h-[1px] ${error ? 'bg-red-500/50' : 'bg-gradient-to-r from-transparent via-[#fbbf24]/50 to-transparent'} z-10`}
        />

        <div className="flex items-center gap-3 mb-4">
          <div className={`w-8 h-8 rounded-lg ${error ? 'bg-red-500/10 border-red-500/30' : 'bg-[#fbbf24]/10 border-[#fbbf24]/30'} border flex items-center justify-center shadow-[0_0_10px_rgba(251,191,36,0.1)]`}>
            {error ? <AlertTriangle className="w-4 h-4 text-red-500" /> : <Target className="w-4 h-4 text-[#fbbf24]" />}
          </div>
          <div>
            <span className={`text-[7px] font-black uppercase tracking-[0.4em] ${error ? 'text-red-500/60' : 'text-[#fbbf24]/60'} block mb-0.5`}>
              {error ? 'Security Breach' : 'Waiting for Master'}
            </span>
            <h3 className="text-sm font-black text-white/90 tracking-tight">XÁC THỰC QUYỀN CHỦ TỊCH</h3>
          </div>
        </div>

        <div className="flex gap-2.5 relative z-20">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="password"
              value={code}
              onChange={e => { setCode(e.target.value); if (error) setError(null); }}
              placeholder={error ? "WRONG KEY..." : "NHẬP MẬT MÃ CHỦ QUYỀN..."}
              className={`w-full bg-black/60 border ${error ? 'border-red-500/50 text-red-400' : 'border-white/10 text-[#fbbf24]'} rounded-xl px-4 py-2 text-[11px] font-mono placeholder:text-white/5 outline-none focus:border-[#fbbf24]/50 focus:shadow-[0_0_20px_rgba(251,191,36,0.1)] transition-all uppercase tracking-widest`}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleApprove(); } }}
            />
            <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-20">
              {error ? <ShieldAlert className="w-3.5 h-3.5 text-red-500" /> : <Lock className="w-3.5 h-3.5 text-white" />}
            </div>
          </div>

          <button
            onClick={handleReject}
            disabled={isVerifying}
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white/40 font-black uppercase tracking-[0.1em] text-[10px] hover:bg-rose-500/20 hover:text-rose-400 hover:border-rose-500/30 disabled:opacity-50 transition-all flex items-center gap-1.5"
          >
            <XCircle className="w-3.5 h-3.5" />
            {language === 'vi' ? 'BÁC BỎ' : 'REJECT'}
          </button>

          <button
            onClick={handleApprove}
            disabled={isVerifying}
            className={`px-4 py-2 rounded-xl ${error ? 'bg-red-600' : 'bg-[#fbbf24]'} text-black font-black uppercase tracking-[0.1em] text-[10px] hover:opacity-90 disabled:opacity-50 transition-all shadow-[0_4px_15_rgba(251,191,36,0.2)] flex items-center gap-1.5`}
          >
            {isVerifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : error ? <XCircle className="w-3.5 h-3.5" /> : <Swords className="w-3.5 h-3.5" />}
            {error ? 'THỬ LẠI' : 'PHÊ DUYỆT'}
          </button>
        </div>
      </div>
    </motion.div>
  );
});
