import React, { memo, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Brain, Zap, ShieldCheck, MessageSquare, Target, Activity, Bot, Settings, Hexagon, Radar, RotateCcw, FileCode2, AlertTriangle, Plus, Search, Globe } from 'lucide-react';
import toast from 'react-hot-toast';
import { useZenithStore, AgentLog } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';
import { useAgentController } from '../../hooks/useAgentController';
import { MarkdownRenderer } from './MarkdownRenderer';
import { NuclearApprovalPad } from './NuclearApprovalPad';
import { ToolBlock, ActionBadge, ReasoningBlock, MicroscopeIcon } from './LogElements';

export const LogItem = memo(({ l, forceReasoning }: { l: AgentLog, forceReasoning?: boolean }) => {
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const { runAgent } = useAgentController();
  const language = useZenithStore(s => s.language);

  if (!l) return null;
  const tag = l.tag?.toUpperCase() || 'SYS';
  const rawMsg = l.msg || '';
  // 🛡️ [CHAT-PURGE]: Loại bỏ chỉ số độ trễ [⏱️ ...s] khỏi nội dung chat
  const msg = rawMsg.replace(/\[⏱️\s*[\d.]+\s*s\]/g, '').trim();
  const isUser = tag.startsWith('MASTER') || l.type === 'user';

  const isReasoning = (
    tag.includes('THOUGHT') || 
    tag === 'PLANNING' || 
    tag === 'CRITIC' || 
    tag === 'ADVERSARIAL' || 
    tag === 'MANIFEST' || 
    tag.includes('TƯ DUY') ||
    tag === 'GATEWAY' ||
    tag === 'DISPATCHER' ||
    tag === 'DISPATCHER_LLM' ||
    tag === 'RECEPTIONIST' ||
    tag === 'DEBUG' ||
    (tag === 'SYSTEM' && (msg.includes('[') || msg.includes('📡')))
  ) && !forceReasoning && !isUser;
  const isError = tag === 'ERROR';
  const isAI = !isUser && !isError && tag !== 'SYSTEM' && tag !== 'SYS_LOG' && tag !== 'BAN KỸ THUẬT';
  const isSystem = tag === 'SYSTEM' || tag === 'SYS_LOG' || tag === 'BAN KỸ THUẬT' || tag === 'LATENCY' || tag === 'PROGRESS';
  const isTool = l.type === 'tool' || tag === 'TOOL';

  const handleInspect = useCallback(async (path: string) => {
    try {
      const data = await ZenithService.readFile(path);
      if (data.content) setInspectedFile({ path, content: data.content });
      else toast.error(language === 'vi' ? `Không tìm thấy tệp tin: ${path}` : `File ${path} not found`);
    } catch {
      toast.error(language === 'vi' ? 'Lỗi truy xuất tệp tin hệ thống.' : 'File retrieval failed');
    }
  }, [setInspectedFile, language]);

  const footprints = useMemo(() => {
    if (isUser || isReasoning) return [];
    const fps = [];
    const m = msg.toLowerCase();
    const fileRegex = /([a-zA-Z0-9_\-\.\/]+\.[a-z0-9]+)/i;

    if (m.includes('analyzed') || m.includes('viewed') || m.includes('đã phân tích') || m.includes('reading')) {
      const path = msg.match(fileRegex)?.[0].replace(/[`"']/g, '') || '';
      if (path) fps.push({ label: language === 'vi' ? `Truy xuất: ${path.split('/').pop()}` : `Inspecting: ${path.split('/').pop()}`, icon: MicroscopeIcon, onClick: () => handleInspect(path) });
    }

    if (m.includes('edited') || m.includes('patched') || m.includes('đã sửa') || m.includes('writing')) {
      const path = msg.match(fileRegex)?.[0].replace(/[`"']/g, '') || '';
      if (path) fps.push({ label: language === 'vi' ? `Đã cập nhật: ${path.split('/').pop()}` : `Updated: ${path.split('/').pop()}`, icon: FileCode2, onClick: () => handleInspect(path) });
    }
    return fps;
  }, [msg, isUser, isReasoning, language, handleInspect]);

  if (tag === 'LATENCY') {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="my-2 ml-14 flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-fuchsia-500/10 border border-fuchsia-500/20">
          <Activity className="w-3 h-3 text-fuchsia-400" />
          <span className="text-[9px] font-black text-fuchsia-400 uppercase tracking-tighter">{msg}</span>
        </div>
        <div className="h-px flex-1 bg-gradient-to-r from-fuchsia-500/20 to-transparent" />
      </motion.div>
    );
  }

  if (tag === 'PROGRESS') {
    const pct = l.pct || 0;
    return (
      <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="my-4 ml-14 max-w-[80%]">
        <div className="flex justify-between items-end mb-2 px-1">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[11px] font-semibold tracking-wide text-cyan-400/90">{msg}</span>
          </div>
          <span className="text-[14px] font-mono font-black text-cyan-400">{pct}%</span>
        </div>
        <div className="h-2.5 w-full bg-black/40 rounded-full overflow-hidden border border-white/5 relative">
          <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400" />
        </div>
      </motion.div>
    );
  }

  if (isReasoning) return <ReasoningBlock tag={tag} msg={msg} />;

  // 🏛️ [ANTIGRAVITY-AESTHETIC-REFORM]: Chế độ hiển thị Hành động Rút gọn
  const isAction = (tag === 'EXECUTOR' || tag === 'SEARCH' || tag === 'RESEARCH' || tag === 'FILE' || tag === 'TOOL') && !l.is_result;

  if (isAction) {
    return (
      <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="my-1 ml-14">
        <ActionBadge label={l.action || msg} onClick={footprints[0]?.onClick} />
      </motion.div>
    );
  }

  // 💎 [EXECUTIVE-OFFICE-PROTOCOL]: Định danh Chuyên nghiệp
  const renderIdentity = () => {
    if (isUser) {
      const label = tag === 'MASTER_WEB' ? 'MASTER (WEB)' : tag === 'MASTER_TELE' ? 'MASTER (TELE)' : 'MASTER';
      return (
        <div className="flex items-center gap-2">
          {/* 👑 [IMPERIAL-CROWN]: Biểu tượng vương miện tinh xảo */}
          <div className="p-1 rounded-lg bg-amber-500/20 border border-amber-500/40 shadow-[0_0_10px_rgba(251,191,36,0.2)]">
            <svg viewBox="0 0 24 24" className="w-4 h-4 text-amber-400 fill-amber-400/20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 4l3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14" />
            </svg>
          </div>
          <span className="glow-text-master text-amber-400 font-black tracking-[0.2em] uppercase text-[11px]">{label}</span>
        </div>
      );
    }

    // 👑 [SOVEREIGN-VOICE]: Chỉ JKAI duy nhất đại diện cho Nhật ký điều hành
    if (tag === 'JKAI') {
      return (
        <div className="flex items-center gap-2">
          {/* 🧠 [NEURAL-CORE]: Biểu tượng Lõi Trí tuệ tinh xảo */}
          <div className="p-1 rounded-lg bg-cyan-500/20 border border-cyan-500/40 shadow-[0_0_10px_rgba(34,211,238,0.2)]">
            <Brain className="w-4 h-4 text-cyan-400" />
          </div>
          <span className="glow-text-jkai text-cyan-400 font-black tracking-[0.2em] uppercase text-[11px]">JKAI</span>
        </div>
      );
    }

    // 🔬 [GRANULAR-ELITE-DISPLAY]: Định danh ban ngành
    const source = (l as any).source;
    
    // Chọn Icon phù hợp
    let DeptIcon = Hexagon;
    let deptColor = "text-cyan-400";
    
    if (tag.includes('GATEWAY')) { DeptIcon = Radar; deptColor = "text-emerald-400"; }
    else if (tag.includes('RECEPTIONIST')) { DeptIcon = Bot; deptColor = "text-sky-400"; }
    else if (tag.includes('DISPATCHER')) { DeptIcon = Zap; deptColor = "text-amber-400"; }
    else if (tag.includes('PLANNER')) { DeptIcon = Brain; deptColor = "text-indigo-400"; }
    else if (tag.includes('AUDIT')) { DeptIcon = ShieldCheck; deptColor = "text-rose-400"; }
    else if (tag.includes('FORGE')) { DeptIcon = Settings; deptColor = "text-purple-400"; }
    else if (tag === 'WEB_SEARCH' || tag === 'BRAIN_QUERY' || tag === 'GREP' || tag === 'SMART_INDEX') { DeptIcon = Search; deptColor = "text-violet-400"; }
    else if (tag.includes('BRAIN') || tag === 'SYSTEM') { DeptIcon = Brain; deptColor = "text-cyan-400"; }
    else if (tag === 'ENGINE' || tag === 'MISSION_RESULT') { DeptIcon = Target; deptColor = "text-blue-400"; }
    else if (tag === 'SUMMARIZER') { DeptIcon = FileCode2; deptColor = "text-fuchsia-400"; }
    else if (isError) { DeptIcon = AlertTriangle; deptColor = "text-rose-500"; }

    let displayTag = tag;
    if (language === 'vi') {
      if (tag.includes('GATEWAY') || tag.includes('RECEPTIONIST')) displayTag = 'Ban Lễ Tân';
      else if (tag.includes('DISPATCHER')) displayTag = 'Ban Điều Phối';
      else if (tag.includes('PLANNER')) displayTag = 'Ban Kế Hoạch';
      else if (tag.includes('EXECUTOR')) displayTag = 'Ban Thực Thi';
      else if (tag.includes('SUMMARIZER')) displayTag = 'Ban Thư Ký';
      else if (tag.includes('CRITIC') || tag.includes('AUDIT')) displayTag = 'Ban Kiểm Soát';
      else if (tag === 'WEB_SEARCH' || tag === 'BRAIN_QUERY' || tag === 'GREP' || tag === 'SMART_INDEX') displayTag = 'Ban Hành Chính';
      else if (tag.includes('DATA_SCOUT') || tag.includes('RESEARCH') || tag.includes('SEARCH')) displayTag = 'Ban Thông Tin';
      else if (tag === 'SYSTEM' || tag === 'SYS_LOG') displayTag = 'Ban Kỹ Thuật';
      else if (tag === 'ENGINE') displayTag = 'Trung tâm Điều hành';
    } else {
      if (tag.includes('GATEWAY') || tag.includes('RECEPTIONIST')) displayTag = 'Reception Desk';
      else if (tag.includes('DISPATCHER')) displayTag = 'Coordination Dept';
      else if (tag.includes('PLANNER')) displayTag = 'Planning Dept';
      else if (tag.includes('EXECUTOR')) displayTag = 'Execution Dept';
      else if (tag.includes('SUMMARIZER')) displayTag = 'Secretariat';
      else if (tag.includes('CRITIC') || tag.includes('AUDIT')) displayTag = 'Audit Dept';
      else if (tag === 'WEB_SEARCH' || tag === 'BRAIN_QUERY' || tag === 'GREP' || tag === 'SMART_INDEX') displayTag = 'Administrative Dept';
      else if (tag.includes('DATA_SCOUT') || tag.includes('RESEARCH') || tag.includes('SEARCH')) displayTag = 'Intelligence Dept';
      else if (tag === 'SYSTEM' || tag === 'SYS_LOG') displayTag = 'Tech Ops';
      else if (tag === 'ENGINE') displayTag = 'Operations Center';
    }

    return (
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-0`}>
        <div className="flex items-center gap-1.5 mb-0.5">
          <DeptIcon className={`w-3.5 h-3.5 ${deptColor} opacity-90`} />
          <span className={`${deptColor} font-bold tracking-tight text-[11.5px]`}>{displayTag}</span>
        </div>
        {source && (
          <span className={`text-[8px] font-mono font-medium text-white/30 italic ${isUser ? 'mr-3' : 'ml-3'}`}>
            {source.toLowerCase()}
          </span>
        )}
      </div>
    );
  };

  // 💎 [AESTHETIC-LOGIC]: Khôi phục Bong bóng Chat nhưng giữ Typography tinh giản
  const isPremium = tag === 'JKAI' || isUser;
  const containerStyle = isPremium ? "mb-8" : "mb-2";
  
  // 🌈 [SERVICE-COLOR-MAPPING]: Bản đồ sắc màu ban ngành
  let colorClass = "cyan";
  if (tag.includes('GATEWAY')) colorClass = "emerald";
  else if (tag.includes('RECEPTIONIST')) colorClass = "sky";
  else if (tag.includes('DISPATCHER')) colorClass = "amber";
  else if (tag.includes('PLANNER')) colorClass = "indigo";
  else if (tag.includes('AUDIT')) colorClass = "rose";
  else if (tag.includes('FORGE')) colorClass = "purple";
  else if (tag === 'ENGINE' || tag === 'MISSION_RESULT') colorClass = "blue";
  else if (tag === 'SUMMARIZER') colorClass = "fuchsia";
  else if (isUser) colorClass = "amber";
  else if (isError) colorClass = "rose";

  const bubbleMaxWidth = "max-w-[98%]";
  const bubbleStyle = isPremium 
    ? "px-5 py-3 rounded-[1.5rem]" 
    : "px-3 py-1.5 rounded-xl font-medium tracking-tight";
  
  const textColor = isUser ? 'text-amber-50' : isPremium ? 'text-white/95' : `text-${colorClass}-50/90`;
  
  const bgStyle = isUser 
    ? 'message-master bg-amber-500/[0.2] backdrop-blur-md border-[3px] border-amber-400 shadow-[0_0_40px_rgba(251,191,36,0.25)] ring-1 ring-amber-400/50' 
    : tag === 'JKAI'
    ? 'message-jkai bg-cyan-500/[0.15] backdrop-blur-md border-[3px] border-cyan-400 shadow-[0_0_35px_rgba(34,211,238,0.25)] ring-1 ring-cyan-400/50'
    : isError ? 'bg-rose-500/10 border border-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.04)]' 
    : `bg-${colorClass}-500/[0.04] border border-${colorClass}-500/20 shadow-[0_0_10px_rgba(var(--${colorClass}-rgb),0.02)]`;

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`animate-slide-up group/log ${containerStyle}`}>
      <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} items-start gap-3`}>
        {/* 💎 [IDENTITY-TAG]: Định danh nằm ngang hàng với bong bóng */}
        {!isUser && (
          <div className="mt-1.5 shrink-0">
            {renderIdentity()}
          </div>
        )}

        <div className={`relative group flex-1 flex flex-col ${isUser ? 'items-end' : 'items-start'} min-w-0`}>
          <div className={`relative transition-all duration-500 w-full ${bubbleStyle} ${bgStyle}`}>
            <div className={`relative z-10 prose prose-invert max-w-none !max-w-full leading-relaxed text-[14px] ${textColor}`}>
              {isTool ? <ToolBlock msg={msg} /> : !msg.trim() ? <Radar className="animate-spin text-cyan-400" /> : <MarkdownRenderer content={msg} />}
            </div>
            {(!isUser && !isError && (l.is_core === true || l.type === 'CODE')) && <NuclearApprovalPad language={language} task_id={(l as any).task_id} />}
            
            {/* ⏱️ [TIMESTAMP]: Chỉ hiện khi hover */}
            <div className={`absolute -bottom-6 ${isUser ? 'right-0' : 'left-0'} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}>
              <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest">
                {l.timeStr?.split(':').slice(0, 2).join(':')}
              </span>
            </div>

            {isUser && (
              <div className="absolute -left-20 top-1/2 -translate-y-1/2 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-300 z-30 pointer-events-auto bg-[#07090f]/90 px-2.5 py-1.5 rounded-xl border border-white/5 backdrop-blur-md shadow-2xl">
                <button 
                  onClick={() => {
                    useZenithStore.getState().setGoal(msg);
                    toast.success(language === 'vi' ? 'Đã nạp lệnh vào ô nhập!' : 'Task loaded to input!', { id: 'ZENITH_COPY' });
                  }} 
                  className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-sky-400 transition-colors"
                  title={language === 'vi' ? 'Dùng lại lệnh này (Nạp vào ô gõ)' : 'Reuse this task (Load to input)'}
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
                <button 
                  onClick={() => runAgent(msg)} 
                  className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-emerald-400 transition-colors"
                  title={language === 'vi' ? 'Chạy lại lệnh ngay lập tức' : 'Run task again immediately'}
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
          
          {footprints.length > 0 && !isAction && (
            <div className={`flex flex-col mt-4 pl-2 border-l border-white/10 ${isUser ? 'items-end' : 'items-start'}`}>
              {footprints.map((fp, i) => <ActionBadge key={i} label={fp.label} onClick={fp.onClick} />)}
            </div>
          )}
        </div>

        {isUser && (
          <div className="mt-1 shrink-0">
            {renderIdentity()}
          </div>
        )}
      </div>
    </motion.div>
  );
});
