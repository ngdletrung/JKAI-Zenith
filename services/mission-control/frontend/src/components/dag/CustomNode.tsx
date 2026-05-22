import { memo, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Handle, Position } from 'reactflow';
import {
  Brain, Zap, Database, Shield, GitBranch,
  Code2, Search, FileText, CheckCircle2, XCircle, Clock, Loader2,
  Cpu, Terminal, Sparkles, Bot
} from 'lucide-react';
import { useZenithStore, Dictionary } from '../../store/zenithStore';

const ICONS: Record<string, any> = {
  brain: Brain,
  zap: Zap,
  database: Database,
  shield: Shield,
  git: GitBranch,
  code: Code2,
  search: Search,
  file: FileText,
  executor: Zap,
  planner: Brain,
  critic: Shield,
  memory: Database,
  bot: Bot,
  default: Sparkles,
};

export const CustomNode = memo(({ id, data }: any) => {
  const lang = useZenithStore(s => s.language);
  const dict = Dictionary[lang] || Dictionary.en;

  const isRunning = data.status === 'RUNNING';
  const isWaiting = data.status === 'WAITING';
  const isIdle = data.status === 'IDLE';

  const intensityMap: Record<string, { color: string, glow: string, dur: number }> = {
    fierce: { color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.4)', dur: 0.6 },
    strict: { color: '#ef4444', glow: 'rgba(239, 68, 68, 0.4)', dur: 0.8 },
    fast: { color: 'var(--accent-zenith)', glow: 'rgba(0, 242, 255, 0.5)', dur: 0.4 },
    calm: { color: 'var(--accent-zenith)', glow: 'rgba(0, 242, 255, 0.3)', dur: 2.0 }
  };
  const config = intensityMap[data.intensity] || intensityMap.calm;
  const scale = data.scale || 1.0;

  const getStatusLabel = (status: string) => {
    const s = status?.toUpperCase();
    if (s === 'AUDITING') return dict.st_auditing;
    if (s === 'DONE') return dict.st_stable;
    if (s === 'RUNNING') return dict.st_running;
    if (s === 'WAITING') return dict.st_waiting;
    if (s === 'ERROR') return dict.st_error;
    return dict.st_idle;
  };

  const Icon = ICONS[data.type] || ICONS[data.icon] || ICONS.default;
  const cycles = data.cycles || 0;

  // 🧠 Neural Filaments Paths (Organic veins)
  const filaments = useMemo(() => [
    "M 30 50 Q 50 30 70 50",
    "M 20 40 Q 50 60 80 40",
    "M 40 20 Q 60 50 40 80",
    "M 50 30 Q 30 50 50 70",
  ], []);

  return (
    <div className="relative flex flex-col items-center group">
      <motion.div
        initial={false}
        animate={{
          opacity: isIdle ? 0.4 : 1,
          scale: scale,
          borderColor: (isRunning || isWaiting) ? config.color : 'rgba(255,255,255,0.1)',
          boxShadow: (isRunning || isWaiting) ? `0 0 50px ${config.glow}` : '0 0 0px transparent'
        }}
        transition={{ duration: config.dur, repeat: (isRunning || isWaiting) ? Infinity : 0, repeatType: 'reverse' }}
        className={`relative w-28 h-28 rounded-full border transition-all duration-700 flex flex-col items-center justify-center overflow-hidden z-10 ${(isRunning || isWaiting) ? 'bg-[#07090f]/60 backdrop-blur-[8px]' : 'bg-transparent'}`}
      >
        {/* 🧬 Bio-Neural Filaments (Organic Layer) */}
        {(isRunning || isWaiting) && (
          <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40" viewBox="0 0 100 100">
            <defs>
              <filter id={`f-glow-${id}`}>
                <feGaussianBlur stdDeviation="1" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            <g filter={`url(#f-glow-${id})`}>
              {filaments.map((d, i) => (
                <path
                  key={i}
                  d={d}
                  fill="none"
                  stroke={config.color}
                  strokeWidth="0.8"
                  strokeDasharray="5, 15"
                  opacity="0.6"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    from="0"
                    to="40"
                    dur={`${2 + i}s`}
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0.2;0.8;0.2"
                    dur={`${1.5 + i}s`}
                    repeatCount="indefinite"
                  />
                </path>
              ))}
            </g>
          </svg>
        )}

        {/* 🏆 Bio-Pulse Core (Central Pulse) */}
        {(isRunning || isWaiting) && (
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              animate={{
                scale: [1, 1.4, 1],
                opacity: [0.1, 0.3, 0.1]
              }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="w-16 h-16 rounded-full bg-gradient-to-r from-transparent via-white/10 to-transparent"
              style={{ filter: `blur(10px) drop-shadow(0 0 15px ${config.color})` }}
            />
          </div>
        )}

        {/* Brainwaves / Heartbeat effects combined for premium feel */}
        {(isRunning || isWaiting) && (
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            {[1, 2].map((i) => (
              <motion.div
                key={i}
                initial={{ scale: 0.8, opacity: 0.6 }}
                animate={{ scale: 1.8, opacity: 0 }}
                transition={{ duration: 2.5, repeat: Infinity, delay: i * 1.2 }}
                className="absolute w-full h-full rounded-full border border-white/10"
                style={{ borderColor: `${config.color}22` }}
              />
            ))}
          </div>
        )}

        {/* Enhanced Radar Scan */}
        {(isRunning || isWaiting) && (
          <div className="absolute inset-0 pointer-events-none rounded-full overflow-hidden">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              className="absolute w-[200%] h-[200%] top-[-50%] left-[-50%]"
              style={{
                background: `conic-gradient(from 0deg, transparent 60%, ${config.color} 100%)`,
                opacity: 0.2
              }}
            />
          </div>
        )}

        {/* Content Container */}
        <div className="relative z-10 flex flex-col items-center gap-1.5">
          <div 
            className={`p-3 rounded-full transition-all duration-500 ${(isRunning || isWaiting) ? 'bg-white/5' : 'text-white/20'}`} 
            style={{ 
              color: (isRunning || isWaiting) ? config.color : undefined, 
              filter: (isRunning || isWaiting) ? `drop-shadow(0 0 12px ${config.color})` : 'none',
              transform: isRunning ? 'scale(1.1)' : 'scale(1)'
            }}
          >
            <Icon className={`w-7 h-7 ${(isRunning || isWaiting) ? 'animate-pulse' : ''}`} strokeWidth={1.2} />
          </div>

          <div className="flex flex-col items-center w-full px-2">
            <span
              className="font-black uppercase tracking-[0.15em] px-3 py-1 rounded-full bg-black/40 border border-white/5 whitespace-nowrap text-center overflow-hidden text-ellipsis max-w-full backdrop-blur-md"
              style={{
                color: (isRunning || isWaiting) ? config.color : 'rgba(255,255,255,0.2)',
                fontSize: data.label.length > 12 ? '7.5px' : data.label.length > 8 ? '8.5px' : '9.5px',
                textShadow: (isRunning || isWaiting) ? `0 0 10px ${config.color}44` : 'none'
              }}
            >
              {data.label}
            </span>
          </div>
        </div>

        <Handle type="target" position={Position.Top} className="!opacity-0" />
        <Handle type="source" position={Position.Bottom} className="!opacity-0" />
      </motion.div>

      {/* Sub-label & Status */}
      <div className="mt-2 text-center w-40 flex flex-col items-center pointer-events-none transition-opacity duration-500" style={{ opacity: isIdle ? 0.3 : 1 }}>
        <div className="text-[8px] font-black tracking-[0.4em] uppercase text-white/30 mb-1">
          {getStatusLabel(data.status)}
        </div>
        {cycles > 0 && (
          <div className="px-2 py-0.5 rounded-full bg-white/[0.03] border border-white/5">
            <span className="text-[7.5px] font-mono font-black text-white/20 tracking-widest uppercase">Cycle {cycles.toString().padStart(2, '0')}</span>
          </div>
        )}
      </div>
    </div>
  );
});

