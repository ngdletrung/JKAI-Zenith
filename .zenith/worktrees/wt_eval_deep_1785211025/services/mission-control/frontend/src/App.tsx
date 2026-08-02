import React, { useEffect, useRef, memo, useMemo, useCallback } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { 
  Hexagon, Activity, Globe, Mic, Wifi, WifiOff, 
  Command, GitBranch, CircuitBoard, Sparkles, 
  ClipboardList, ScrollText, FolderTree, Code2, 
  History, Terminal, RefreshCcw, Radar, Cpu, 
  Database, ShieldCheck
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

import { Zenith3DMission } from './components/Zenith3DMission';
import { useTaskWebSocket } from './hooks/useTaskWebSocket';
import { useZenithVoice } from './hooks/useZenithVoice';
import { useZenithStore, Dictionary } from './store/zenithStore';
import { useAgentController } from './hooks/useAgentController';
import { ZenithService } from './services/ZenithService';
import { NuclearApprovalPad } from './components/zenith/NuclearApprovalPad';

// Modular Components
import { IntelligenceStream } from './components/zenith/IntelligenceStream';
import { TabContent } from './components/WorkspaceTabs';

// ─── 1. CORE CONFIGURATIONS ───────────────────────────────────────────────────

const RIGHT_TABS = [
  { k: 'progress', l: 'Tiến trình', i: Activity },
  { k: 'plan', l: 'Kế hoạch', i: Sparkles },
  { k: 'tasks', l: 'Nhiệm vụ', i: ClipboardList },
  { k: 'walkthrough', l: 'Giải pháp', i: ScrollText },
  { k: 'changes', l: 'Thay đổi', i: GitBranch },
  { k: 'explorer', l: 'Hệ thống', i: FolderTree },
  { k: 'logs', l: 'Nhật ký', i: History }
] as const;

const TAB_TRANSLATIONS: Record<string, { en: string; vi: string }> = {
  progress: { en: 'Progress', vi: 'Tiến trình' },
  plan: { en: 'Plan', vi: 'Kế hoạch' },
  tasks: { en: 'Tasks', vi: 'Nhiệm vụ' },
  walkthrough: { en: 'Solution', vi: 'Giải pháp' },
  changes: { en: 'Changes', vi: 'Thay đổi' },
  explorer: { en: 'System', vi: 'Hệ thống' },
  logs: { en: 'Logs', vi: 'Nhật ký' }
};

// ─── 2. CORE UTILITIES ───────────────────────────────────────────────────────

const SectionLabel = memo(({ icon: Icon, label }: { icon: React.ComponentType<any>, label: string }) => (
  <div className="flex items-center gap-2 px-1 opacity-40">
    <div className="p-1 rounded bg-white/5">
      <Icon className="w-3 h-3 text-white/80" />
    </div>
    <span className="text-[9px] font-black uppercase tracking-[0.3em]">{label}</span>
  </div>
));

// ─── 3. RESOURCE MONITORING (HUD) ───────────────────────────────────────────

const ResourceGauge = memo(({ label, value, percent, icon: Icon, colorClass, glowColor }: any) => {
  const radius = 22;
  const strokeWidth = 3;
  const circumference = 2 * Math.PI * radius; // ~138.2
  // We make it a 3/4 gauge (from -225 deg to 45 deg)
  const activeCircumference = circumference * 0.75;
  const strokeDashoffset = activeCircumference - (percent / 100) * activeCircumference;

  return (
    <div className="flex flex-col items-center gap-1.5 group relative select-none">
      {/* Sleek Glassmorphic Outer Ring */}
      <div className="relative w-14 h-14 flex items-center justify-center rounded-full bg-black/40 border border-white/5 shadow-inner transition-all duration-500 group-hover:border-white/10 group-hover:scale-105">
        {/* Glow effect in background */}
        <div 
          className="absolute inset-0 rounded-full blur-xl opacity-0 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none" 
          style={{ backgroundColor: glowColor }} 
        />
        
        {/* SVG Gauge */}
        <svg className="w-14 h-14 transform rotate-[135deg] select-none pointer-events-none">
          {/* Base track */}
          <circle
            cx="28"
            cy="28"
            r={radius}
            fill="transparent"
            stroke="rgba(255,255,255,0.04)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${activeCircumference} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Active progress - Offloaded to CSS hardware transitions for silky smooth CPU rendering */}
          <circle
            cx="28"
            cy="28"
            r={radius}
            fill="transparent"
            stroke={glowColor}
            strokeWidth={strokeWidth}
            strokeDasharray={`${activeCircumference} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 650ms cubic-bezier(0.23, 1, 0.32, 1)',
            }}
            className="drop-shadow-[0_0_3px_rgba(255,255,255,0.15)] will-change-[stroke-dashoffset]"
          />
        </svg>

        {/* Center Content: Icon & Numeric Value */}
        <div className="absolute inset-0 flex flex-col items-center justify-center mt-0.5">
          <Icon className={`w-3.5 h-3.5 opacity-40 transition-all duration-300 group-hover:opacity-85 ${colorClass}`} />
          <span className="text-[9px] font-mono font-black tracking-tighter text-white/90 mt-0.5">{value}</span>
        </div>
      </div>

      {/* Label */}
      <span className="text-[7px] font-black uppercase tracking-[0.2em] opacity-40 group-hover:opacity-85 transition-all duration-300">
        {label}
      </span>
    </div>
  );
});

const ResourceHUD = memo(() => {
  // 🛡️ [PRIMITIVE-SELECTORS]: Subscribe to values individually to avoid object reference re-renders
  const cpu = useZenithStore(s => s.pulse.cpu);
  const ram = useZenithStore(s => s.pulse.ram);
  const gpu = useZenithStore(s => s.pulse.gpu);
  const status = useZenithStore(s => s.status);

  // 🛡️ [SOVEREIGN PERFORMANCE SHIELD]: Tự động gắn class khi quá tải để tối ưu hóa render cực hạn
  useEffect(() => {
    const isHigh = cpu > 80 || status === 'running';
    if (isHigh) {
      document.body.classList.add('high-cpu-mode');
    } else {
      document.body.classList.remove('high-cpu-mode');
    }
  }, [cpu, status]);
  
  // CPU Color calculations
  const cpuColor = cpu > 80 ? 'text-rose-400' : 'text-amber-400';
  const cpuGlow = cpu > 80 ? '#fb7185' : '#f59e0b';

  return (
    <div className="flex items-center gap-6 px-6 py-2.5 rounded-[20px] bg-white/[0.01] border border-white/[0.04] backdrop-blur-3xl shadow-2xl">
      <ResourceGauge label="CPU PULSE" value={`${cpu}%`} percent={cpu} icon={Activity} colorClass={cpuColor} glowColor={cpuGlow} />
      <div className="w-px h-8 bg-white/5" />
      <ResourceGauge label="RAM FLOW" value={`${ram}%`} percent={ram} icon={Database} colorClass="text-emerald-400" glowColor="#34d399" />
      <div className="w-px h-8 bg-white/5" />
      <ResourceGauge label="VGA FLOW" value={`${gpu || 0}%`} percent={gpu || 0} icon={Cpu} colorClass="text-cyan-400" glowColor="#22d3ee" />
      <div className="w-px h-8 bg-white/5" />
      <div className="flex flex-col gap-1 min-w-[100px] pl-1">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[8px] font-black uppercase tracking-tighter text-white/40">Status: <span className="text-white/80">OPTIMAL</span></span>
        </div>
        <div className="flex items-center gap-1.5">
          <Radar className="w-3 h-3 text-sky-400/40 animate-spin-slow" />
          <span className="text-[8px] font-black uppercase tracking-widest text-white/20">Uplink: <span className="text-sky-400/60">ACTIVE</span></span>
        </div>
      </div>
    </div>
  );
});

// ─── 3. TOP NAVIGATION & DECOUPLED CONNECTION ───────────────────────────────

const ConnectionIndicator = memo(({ dict }: { dict: any }) => {
  const isConnected = useZenithStore(s => s.isConnected);
  return (
    <div className={`px-4 py-2 rounded-xl border flex items-center gap-3 transition-all ${isConnected ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'}`}>
      <Wifi className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
      <span className={`text-[9px] font-black uppercase tracking-widest ${isConnected ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
        {isConnected ? (dict.uplink_stable || 'Uplink Stable') : (dict.uplink_lost || 'Uplink Lost')}
      </span>
    </div>
  );
});

const TopHeader = memo(({ dict, voice }: any) => {
  const language = useZenithStore(s => s.language);
  const setLanguage = useZenithStore(s => s.setLanguage);
  const status = useZenithStore(s => s.status);
  const isRunning = status === 'running';

  return (
    <header className="shrink-0 h-20 border-b border-white/[0.04] bg-[#060910]/80 backdrop-blur-3xl relative z-[100] flex items-center justify-between px-8">
      <div className="flex items-center gap-6">
        <div className="relative group cursor-pointer">
          <div className={`absolute -inset-2 bg-amber-500 rounded-full blur-xl opacity-20 transition-all duration-700 ${isRunning ? 'scale-150 opacity-40' : ''}`} />
          <div className="relative h-11 w-11 rounded-xl bg-black/40 border border-white/10 flex items-center justify-center backdrop-blur-xl group-hover:border-amber-500/50">
            <Hexagon className={`w-6 h-6 ${isRunning ? 'text-amber-400 animate-[spin_4s_linear_infinite]' : 'text-white/40'}`} strokeWidth={1.5} />
            <span className="absolute text-[9px] font-black text-white">JK</span>
          </div>
        </div>
        <div>
          <h1 className="text-base font-black tracking-widest uppercase text-white/95">
            {language === 'vi' ? 'Trung tâm Điều hành' : 'Command Center'} <span className="text-amber-400">JKAI ZENITH</span>
          </h1>
          <div className="flex items-center gap-4 mt-1 opacity-40">
             <span className="text-[9px] font-bold tracking-[0.3em] uppercase">THE OMNIPRESENCE</span>
             <div className="w-[1px] h-3 bg-white/10" />
             <span className="text-[9px] font-black text-sky-400 uppercase">v1.0 Sovereign</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-8">
        <ResourceHUD />
        <div className="flex items-center gap-3">
          <button onClick={voice.toggleListening} className={`p-2.5 rounded-full transition-all ${voice.isListening ? 'bg-sky-500/20 border border-sky-500 shadow-lg shadow-sky-500/20' : 'bg-white/5 border border-white/5 hover:bg-white/10'}`}>
            <Mic className={`w-4 h-4 ${voice.isListening ? 'text-sky-400 animate-pulse' : 'text-white/40'}`} />
          </button>
          <button onClick={() => setLanguage(language === 'en' ? 'vi' : 'en')} className="px-4 py-2 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-all flex items-center gap-2">
            <Globe className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-[10px] font-black text-white/60">{language.toUpperCase()}</span>
          </button>
          <ConnectionIndicator dict={dict} />
        </div>
      </div>
    </header>
  );
});

class PrecisionLocator {
  private lastPosition: any = null;

  async getPreciseLocation(options: any = {}) {
    const config = {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 0,
      ...options
    };

    if (!navigator.geolocation) {
      throw new Error("Geolocation khong duoc ho tro");
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const result = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            heading: position.coords.heading,
            speed: position.coords.speed,
            timestamp: position.timestamp
          };
          this.lastPosition = result;
          resolve({
            success: true,
            data: result
          });
        },
        (error) => {
          reject({
            success: false,
            code: error.code,
            message: this.translateError(error.code)
          });
        },
        config
      );
    });
  }

  watchLocation(callback: (pos: any) => void, options: any = {}) {
    const config = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
      ...options
    };

    return navigator.geolocation.watchPosition(
      (position) => {
        callback({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          altitude: position.coords.altitude,
          heading: position.coords.heading,
          speed: position.coords.speed,
          timestamp: position.timestamp
        });
      },
      (error) => {
        console.error(error);
      },
      config
    );
  }

  translateError(code: number) {
    switch (code) {
      case 1:
        return "User tu choi quyen truy cap vi tri";
      case 2:
        return "Khong the xac dinh vi tri";
      case 3:
        return "Timeout khi lay vi tri";
      default:
        return "Loi khong xac dinh";
    }
  }
}

// ─── 4. MAIN APPLICATION ─────────────────────────────────────────────────────

// ─── 4. SOVEREIGN RENDERING ISOLATION (HUD CONTAINER) ─────────────────────────

const SovereignGraphHUD = memo(({ dict, onNewLog }: { dict: any, onNewLog?: (log: any) => void }) => {
  const { dagNodes, submitTask, resetDAG } = useTaskWebSocket(onNewLog);
  const setSocketActions = useZenithStore(s => s.setSocketActions);

  // 🛰️ [BRIDGE-REGISTRY]: Đăng ký Cầu nối thần kinh vào Lõi Store để gọi toàn cục
  useEffect(() => {
    setSocketActions({ submitTask, resetDAG });
  }, [submitTask, resetDAG, setSocketActions]);

  return (
    <div className="w-[420px] shrink-0 flex flex-col gap-3 h-full">
      <SectionLabel icon={GitBranch} label={dict.exec_graph} />
      <div className="flex-1 rounded-2xl border border-white/[0.06] bg-black/40 overflow-hidden shadow-2xl relative">
        <Zenith3DMission nodes={dagNodes} />
      </div>
    </div>
  );
});

// ─── 5. MAIN APPLICATION ─────────────────────────────────────────────────────

function App() {
  const language = useZenithStore(s => s.language);
  const dict = useMemo(() => Dictionary[language as keyof typeof Dictionary] || Dictionary.en, [language]);
  
  // 🛡️ [ANTI-FLICKER-SELECTOR]: Discrete selectors to isolate App from log streams
  const isBooting = useZenithStore(s => s.isBooting);
  const setBooting = useZenithStore(s => s.setBooting);
  const rightTab = useZenithStore(s => s.rightTab);
  const setTab = useZenithStore(s => s.setTab);
  const unreadTabs = useZenithStore(s => s.unreadTabs);
  const setUnreadTab = useZenithStore(s => s.setUnreadTab);
  const backgroundProposals = useZenithStore(s => s.backgroundProposals);
  const pendingHitlId = useZenithStore(s => s.pendingHitlId);
  const setPendingHitlId = useZenithStore(s => s.setPendingHitlId);

  const { runAgent } = useAgentController();

  // 🛡️ [HITL-SYNC]: Sync một lần lúc khởi động, sau đó nhường quyền cho WebSocket PubSub
  useEffect(() => {
    ZenithService.getPendingHitl().then(pending => {
      // 🛡️ [CORE-ONLY]: Chỉ tự động hiện Popup cho các yêu cầu HẠT NHÂN (Auth hoặc Core mutation)
      // Các đề xuất ZIM/Strategy sẽ chỉ hiện trong IntelligenceStream để Master duyệt khi cần.
      const entries = Object.entries(pending || {});
      const coreHitl = entries.find(([_, val]) => {
        const v = typeof val === 'string' ? JSON.parse(val) : val;
        return v.is_core === true || v.type === 'AUTH_REQUIRED';
      });

      if (coreHitl) setPendingHitlId(coreHitl[0]);
      else setPendingHitlId(null);
    }).catch(() => {});
  }, [setPendingHitlId]);

  // 📄 Tải artifact plan / tasks / walkthrough khi mở Mission Control
  useEffect(() => {
    ZenithService.prefetchArtifacts().then((arts) => {
      const { currentArtifacts, updateArtifact } = useZenithStore.getState();
      (['plan', 'tasks', 'walkthrough'] as const).forEach((k) => {
        const c = arts[k];
        if (c && c.trim() && !(currentArtifacts[k] || '').trim()) {
          updateArtifact(k, c);
        }
      });
    }).catch(() => {});
  }, []);

  // 🚀 [BOOT-PROTOCOL]: Khởi động hệ thống
  useEffect(() => {
    const timer = setTimeout(() => {
      setBooting(false);
      try {
        sessionStorage.setItem('zenith_booted', 'true');
      } catch (e) {}
    }, 1500);
    return () => clearTimeout(timer);
  }, [setBooting]);

  // [PRECISE-GEOLOCATION]: Sync precise browser coordinates with backend Redis state
  useEffect(() => {
    const locator = new PrecisionLocator();
    locator.getPreciseLocation()
      .then(async (response: any) => {
        if (response.success && response.data) {
          const { latitude, longitude, accuracy, altitude, heading, speed, timestamp } = response.data;
          try {
            await fetch('/api/geolocation', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                latitude,
                longitude,
                accuracy,
                altitude,
                heading,
                speed,
                timestamp
              })
            });
            console.log(`Precise browser location synced: ${latitude}, ${longitude} (accuracy: ${accuracy}m)`);
          } catch (err) {
            console.error('Failed to sync location with backend:', err);
          }
        }
      })
      .catch((err: any) => {
        console.warn('Browser geolocation precision query failed:', err.message);
      });
  }, []);

  // 🎙️ [VOICE-REF-BRIDGE]: Sử dụng Ref để phá vỡ vòng lặp phụ thuộc thưa Master
  const voiceRef = useRef<any>(null);

  // 🎙️ [DECOUPLED-VOICE]: Kích hoạt trợ lý giọng nói thông qua Global Store Action
  const handleVoiceCommand = useCallback(async (text: string) => {
    const lowerText = text.toLowerCase();
    
    // 💎 [ELITE-COMMAND-INTERCEPTION]: Xử lý các lệnh đặc hiệu trước khi gửi tới Brain
    if (lowerText.includes('báo cáo') || lowerText.includes('tình trạng') || lowerText.includes('digest')) {
      toast.loading('Đang tổng hợp dữ liệu hệ thống...', { id: 'voice-digest' });
      const res = await ZenithService.getSystemDigest();
      toast.dismiss('voice-digest');
      
      if (res.status === 'ok' && res.digest) {
        voiceRef.current?.speak(res.digest);
        toast.success('Đã hoàn thành báo cáo hệ thống.', { icon: '📊' });
        return;
      }
    }

    const actions = useZenithStore.getState().socketActions;
    if (actions?.submitTask) {
      actions.submitTask(text, 'fast');
    }
  }, []);

  const voice = useZenithVoice(handleVoiceCommand);
  voiceRef.current = voice;

  // 🎙️ [NEURAL-VOICE-BRIDGE]: Kết nối luồng log với động cơ giọng nói Gemini-grade
  const handleNewLog = useCallback((log: any) => {
    const tag = (log.tag || '').toUpperCase();
    // Chỉ đọc các tin nhắn từ JKAI (phản hồi), kết quả nhiệm vụ hoặc tóm tắt
    if (['JKAI', 'RESULT', 'MISSION_RESULT', 'SUMMARIZER', 'DONE'].includes(tag)) {
      // Nếu là tag JKAI, chúng ta coi là stream chunk, các tag khác là thông báo cuối
      voice.speak(log.msg, tag !== 'JKAI');
    }
  }, [voice]);

  // 🎙️ [STABLE-VOICE-PROPS]: Đóng gói props để TopHeader không bị re-render vô ích
  const voiceActions = useMemo(() => ({
    toggleListening: voice.toggleListening,
    isListening: voice.isListening
  }), [voice.toggleListening, voice.isListening]);

  // ─── 5.5. DYNAMIC RIGHT COLUMN RESIZER ─────────────────────────────────────
  const [rightWidth, setRightWidth] = React.useState(() => {
    try {
      const saved = localStorage.getItem('zenith_right_width');
      return saved ? parseInt(saved, 10) : 480;
    } catch {
      return 480;
    }
  });

  const [isResizing, setIsResizing] = React.useState(false);

  const resizeRef = useRef({ rightWidth, isResizing });
  useEffect(() => {
    resizeRef.current = { rightWidth, isResizing };
  }, [rightWidth, isResizing]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const { isResizing } = resizeRef.current;
      if (!isResizing) return;

      const newWidth = Math.max(300, Math.min(window.innerWidth - e.clientX - 20, window.innerWidth * 0.5));
      setRightWidth(newWidth);
      try {
        localStorage.setItem('zenith_right_width', String(newWidth));
      } catch {}
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // ─── 6. LAYOUT ─────────────────────────────────────────────────────────────

  return (
    <div 
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
          useZenithStore.getState().setFiles([...useZenithStore.getState().attachedFiles, ...files]);
          toast.dismiss('ZENITH_PULSE');
          toast.success(`Đã tiếp nhận ${files.length} tệp toàn cục.`, { id: 'ZENITH_PULSE' });
        }
      }}
      className="fixed inset-0 w-full h-full bg-[#060910] text-white font-sans selection:bg-sky-500/30 overflow-hidden flex flex-col [transform:translateZ(0)] [backface-visibility:hidden] [will-change:transform]"
    >
      <div className="nebula-bg" />
      <TopHeader dict={dict} voice={voiceActions} />

      <main className="flex-1 w-full px-5 py-4 flex gap-0 overflow-hidden relative z-10 min-h-0">
        {/* Left: Isolated Neural Graph (Phòng họp giữ nguyên) */}
        <SovereignGraphHUD dict={dict} onNewLog={handleNewLog} />

        {/* Fixed Spacer between Left and Center */}
        <div className="w-4 shrink-0" />

        {/* Center: Intelligence Stream */}
        <div className="flex-1 flex flex-col min-w-0 gap-3">
          <SectionLabel icon={Activity} label={dict.intel_stream || "Nhật ký Điều hành"} />
          <div className="flex-1 flex flex-col min-h-0">
            <IntelligenceStream />
          </div>
        </div>

        {/* Premium Draggable Middle-Right Divider */}
        <div
          className="w-4 shrink-0 relative cursor-col-resize group select-none self-stretch flex items-center justify-center z-50"
          onMouseDown={(e) => {
            e.preventDefault();
            setIsResizing(true);
          }}
        >
          {/* Beautiful glowing vertical indicator line */}
          <div className="w-[1.5px] h-[30%] bg-white/10 group-hover:h-full group-hover:bg-cyan-400/60 group-hover:shadow-[0_0_10px_rgba(34,211,238,0.6)] transition-all duration-300 rounded-full" />
        </div>

        {/* Right: Neural Workspace */}
        <div style={{ width: rightWidth }} className="shrink-0 flex flex-col gap-4 h-full min-h-0">
          <SectionLabel icon={CircuitBoard} label={dict.workspace_title} />
          <div className="p-1.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-md relative shrink-0">
            <div className="flex gap-1">
              {RIGHT_TABS.map(t => {
                const isActive = rightTab === t.k;
                return (
                  <button 
                    key={t.k} 
                    onClick={() => { setTab(t.k as any); if (unreadTabs[t.k]) setUnreadTab(t.k, 0); }} 
                    className={`relative flex-1 flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl transition-all duration-300 group border ${
                      isActive 
                        ? 'text-white bg-cyan-400/10 border-cyan-400/20' 
                        : 'text-white/20 hover:text-white/40 border-transparent hover:bg-white/[0.02]'
                    }`}
                  >
                    <div className="relative">
                      <t.i className={`w-4 h-4 relative ${isActive ? 'text-cyan-400' : ''}`} />
                      {(t.k === 'plan' ? backgroundProposals.length : (unreadTabs[t.k] || 0)) > 0 && (
                        <div className="absolute -top-2 -right-2.5 flex items-center justify-center min-w-[14px] h-[14px] rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)] px-1 z-10">
                          <span className="text-[9px] font-black text-white leading-none">
                            {t.k === 'plan' ? backgroundProposals.length : unreadTabs[t.k]}
                          </span>
                        </div>
                      )}
                    </div>
                    <span className="relative text-[8px] font-black uppercase tracking-widest leading-tight">{TAB_TRANSLATIONS[t.k]?.[language] || t.l}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="flex-1 min-h-0 rounded-2xl border border-white/[0.06] bg-white/[0.01] overflow-hidden flex flex-col relative">
            <TabContent />
          </div>
        </div>
      </main>

      {/* 🛡️ [CORE-AUTH OVERLAY] */}
      <AnimatePresence>
        {pendingHitlId && (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }} 
            className="fixed inset-0 z-[200] bg-black/80 backdrop-blur-md flex flex-col items-center justify-center p-4"
          >
            <div className="w-full max-w-lg">
              <NuclearApprovalPad language={language} task_id={pendingHitlId} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <Toaster 
        position="bottom-right" 
        containerStyle={{ bottom: 12, right: 12 }}
        gutter={8}
        toastOptions={{ 
          duration: 3000,
          id: 'ZENITH_PULSE', // 🛡️ [SINGLE-TOAST]: Luôn ghi đè để chỉ hiện 1 bong bóng duy nhất
          style: { 
            background: 'rgba(6, 9, 15, 0.9)', 
            color: '#34d399', 
            border: '1px solid rgba(52, 211, 153, 0.2)', 
            fontSize: '10px', 
            fontWeight: '600', 
            textTransform: 'none', 
            letterSpacing: '0.02em',
            borderRadius: '12px',
            padding: '8px 14px',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
          } 
        }} 
      />
      
      {/* 🚀 [CSS-BOOT-SCREEN]: Opacity-based boot overlay to eliminate unmount GPU flash glitches */}
      <div 
        className={`fixed inset-0 z-[100] bg-[#060910] flex flex-col items-center justify-center gap-8 transition-all duration-700 ease-out [transform:translateZ(0)] [will-change:opacity,transform] ${
          isBooting 
            ? 'opacity-100 pointer-events-auto scale-100' 
            : 'opacity-0 pointer-events-none scale-105'
        }`}
      >
        <div className="relative">
          <div className="absolute -inset-8 bg-sky-500 rounded-full blur-2xl opacity-10 animate-pulse" />
          <div className="relative h-20 w-20 rounded-3xl bg-black/50 border border-white/10 flex items-center justify-center backdrop-blur-xl">
            <Hexagon className="w-10 h-10 text-sky-400 animate-[spin_4s_linear_infinite]" strokeWidth={1.5} />
            <span className="absolute text-sm font-black text-white">JK</span>
          </div>
        </div>
        <h1 className="text-lg font-black tracking-[0.4em] uppercase text-white/80">JKAI <span className="text-sky-400">ZENITH</span></h1>
      </div>
    </div>
  );
}

export default App;