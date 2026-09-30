/**
 * LabelPad — Inline grading widget for JKAI log bubbles.
 *
 * Renders 3 small buttons below each JKAI message so Master can rate quality:
 *   ✅  Đúng hoàn toàn  → score 1.0 / CORRECT
 *   ⚠️  Chưa chuẩn      → score 0.5 / PARTIALLY_CORRECT
 *   ❌  Sai hoàn toàn   → score 0.0 / COMPLETELY_WRONG
 *
 * On click → POST /api/label_log → shows toast confirmation.
 * State is local (no store needed): once submitted the chosen button
 * stays highlighted so Master knows it was recorded.
 */

import React, { useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, XCircle, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { ZenithService } from '../../services/ZenithService';

type Verdict = 'CORRECT' | 'PARTIALLY_CORRECT' | 'COMPLETELY_WRONG';
type Score = 0 | 0.5 | 1;

interface LabelOption {
  verdict: Verdict;
  score: Score;
  label: string;
  labelEn: string;
  Icon: React.FC<{ className?: string }>;
  activeClass: string;
  idleClass: string;
}

const OPTIONS: LabelOption[] = [
  {
    verdict: 'CORRECT',
    score: 1,
    label: 'Đúng',
    labelEn: 'Correct',
    Icon: CheckCircle2,
    activeClass: 'bg-emerald-500/20 border-emerald-400/60 text-emerald-400',
    idleClass: 'hover:bg-emerald-500/10 hover:border-emerald-400/30 hover:text-emerald-400',
  },
  {
    verdict: 'PARTIALLY_CORRECT',
    score: 0.5,
    label: 'Chưa chuẩn',
    labelEn: 'Partial',
    Icon: AlertCircle,
    activeClass: 'bg-amber-500/20 border-amber-400/60 text-amber-400',
    idleClass: 'hover:bg-amber-500/10 hover:border-amber-400/30 hover:text-amber-400',
  },
  {
    verdict: 'COMPLETELY_WRONG',
    score: 0,
    label: 'Sai',
    labelEn: 'Wrong',
    Icon: XCircle,
    activeClass: 'bg-rose-500/20 border-rose-400/60 text-rose-400',
    idleClass: 'hover:bg-rose-500/10 hover:border-rose-400/30 hover:text-rose-400',
  },
];

interface LabelPadProps {
  logId: string;
  taskId?: string;
  msgPreview?: string;
  language?: 'vi' | 'en';
}

export const LabelPad: React.FC<LabelPadProps> = ({
  logId,
  taskId,
  msgPreview,
  language = 'vi',
}) => {
  const [selected, setSelected] = useState<Verdict | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLabel = useCallback(
    async (opt: LabelOption) => {
      if (loading || selected !== null) return;
      setLoading(true);
      try {
        const res = await ZenithService.labelLog({
          log_id: logId,
          task_id: taskId,
          score: opt.score,
          verdict: opt.verdict,
          msg_preview: msgPreview,
        });
        if (res.ok) {
          setSelected(opt.verdict);
          const msg =
            language === 'vi'
              ? `✅ Đã ghi nhận: ${opt.label}`
              : `✅ Labeled: ${opt.labelEn}`;
          toast.success(msg, { id: `label_${logId}`, duration: 2000 });
        } else {
          toast.error(res.error || 'Lỗi ghi nhãn', { id: `label_err_${logId}` });
        }
      } catch {
        toast.error('Không thể ghi nhãn — kiểm tra backend.', { id: `label_net_${logId}` });
      } finally {
        setLoading(false);
      }
    },
    [loading, selected, logId, taskId, msgPreview, language]
  );

  return (
    <div className="flex items-center gap-1 mt-2 pt-2 border-t border-white/[0.06]">
      <span className="text-[9px] font-mono text-white/20 uppercase tracking-widest mr-1 select-none">
        {language === 'vi' ? 'chấm' : 'rate'}
      </span>

      {loading ? (
        <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
      ) : (
        OPTIONS.map((opt) => {
          const isActive = selected === opt.verdict;
          const isDisabled = selected !== null && !isActive;
          return (
            <button
              key={opt.verdict}
              onClick={() => handleLabel(opt)}
              disabled={isDisabled || loading}
              title={language === 'vi' ? opt.label : opt.labelEn}
              className={`
                flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold
                transition-all duration-200 select-none
                ${isActive ? opt.activeClass : `border-white/10 text-white/25 ${!isDisabled ? opt.idleClass : 'opacity-30 cursor-not-allowed'}`}
              `}
            >
              <opt.Icon className="w-3 h-3" />
              <span>{language === 'vi' ? opt.label : opt.labelEn}</span>
            </button>
          );
        })
      )}
    </div>
  );
};
