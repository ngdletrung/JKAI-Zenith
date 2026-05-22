import React, { useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ─── 💬 ELITE STRATEGIC MESSAGE FLOW (v60.0 - Dual Executor Sync) ───────────
const getStrategicMessage = (message: string, role: string, status: string) => {
  const s = String(status || '').toUpperCase();

  let cleanMsg = message || '';
  
  // 🏛️ [ZENITH-SURGICAL-STRIPPER]: Phẫu thuật triệt để phần kỹ thuật
  // Loại bỏ toàn bộ từ đầu đến dấu hai chấm cuối cùng của tiền tố định danh
  if (cleanMsg.includes('🧠')) {
    const parts = cleanMsg.split(':');
    if (parts.length > 1) {
      // Lấy toàn bộ phần sau dấu hai chấm đầu tiên
      cleanMsg = parts.slice(1).join(':').trim();
    }
  }

  // 🛡️ [RECEPTIONIST-SPECIFIC]: Tránh để Trợ lý hiện các thông báo định tuyến
  if (role === 'receptionist') {
    if (cleanMsg.includes('📡 [ROUTING]') || cleanMsg.includes('🚀 Đang triệu tập')) {
      return "Đang điều phối nơ-ron...";
    }
  }

  cleanMsg = cleanMsg.replace(/\[.*?\]:?\s*/g, '');
  cleanMsg = cleanMsg.trim();

  if (role === 'receptionist' && !cleanMsg) {
    if (s === 'RUNNING' || s === 'EXECUTING' || s === 'IDLE') {
      return "Đang tiếp nhận yêu cầu...";
    }
  }

  if (!cleanMsg) {
    if (s === 'RUNNING' || s === 'EXECUTING') {
      if (role === 'master') return "Đang quan sát toàn cục JKAI...";
      return "Đang thực thi nhiệm vụ...";
    }
    return null;
  }
  return cleanMsg;
};

// ─── 🎭 ZENITH ASSET RESOLVER (v46.0 - Alpha/Beta Split) ────────────────────────
const getAgentVisualStates = (role: string) => {
  const roleMap: any = {
    'master': 'Master',
    'receptionist': '1. Tro ly',
    'summarizer': '2. Thu ky',
    'planner': '6. Planer',
    'critic': '7. Critic',
    'executor-alpha': '3. Executor Alpha',
    'executor-beta': '8. Executor Beta'
  };

  const folder = roleMap[role] || '6. Planer';
  const isExecutor = role.includes('executor');

  const files: any = {
    IDLE: isExecutor ? 'ngoi_langnghe.png' : 'ngoi_lang_nghe.png',
    RUNNING: role === 'critic' ? 'dung_noi_chuyen.png' : (isExecutor ? 'dung_vuive.png' : 'dung_trao_doi.png'),
    STRESSED: isExecutor ? 'ngoi_khochiu.png' : 'ngoi_kho_chiu.png',
    ARGUING: isExecutor ? 'dung_gaygat.png' : (role === 'planner' ? 'dung_gay_gat.png' : 'dung_tranh_cai.png')
  };

  return {
    IDLE: encodeURI(`/phong hop/${folder}/${files.IDLE}`),
    RUNNING: encodeURI(`/phong hop/${folder}/${files.RUNNING}`),
    STRESSED: encodeURI(`/phong hop/${folder}/${files.STRESSED}`),
    ARGUING: encodeURI(`/phong hop/${folder}/${files.ARGUING}`)
  };
};

// ─── 🏛️ STATIC SEATS CONFIGURATION ───────────────────────────────────────────
const SEATS = [
  {
    id: 'master', role: 'master', label: 'Chủ Tịch', side: 'center', order: 0,
    posMatrix: {
      IDLE: { x: '35%', y: '44%', size: '30%', z: 10 },
      RUNNING: { x: '20%', y: '45%', size: '47%', z: 10 },
      STRESSED: { x: '35%', y: '44%', size: '30%', z: 10 },
      ARGUING: { x: '20%', y: '45%', size: '47%', z: 10 }
    }
  },
  {
    id: 'receptionist', role: 'receptionist', label: 'Ban Lễ Tân', side: 'left', order: 1,
    posMatrix: {
      IDLE: { x: '54%', y: '52%', size: '52%', z: 20 },
      RUNNING: { x: '37%', y: '52%', size: '55%', z: 20 },
      STRESSED: { x: '54%', y: '52%', size: '52%', z: 20 },
      ARGUING: { x: '37%', y: '52%', size: '58%', z: 20 }
    }
  },
  {
    id: 'planner', role: 'planner', label: 'Ban Kế Hoạch', side: 'right', order: 2,
    posMatrix: {
      IDLE: { x: '52%', y: '52%', size: '42%', z: 25 },
      RUNNING: { x: '58%', y: '52%', size: '48%', z: 25 },
      STRESSED: { x: '52%', y: '52%', size: '42%', z: 25 },
      ARGUING: { x: '58%', y: '52%', size: '48%', z: 25 }
    }
  },
  {
    id: 'summarizer', role: 'summarizer', label: 'Ban Thư Ký', side: 'left', order: 3,
    posMatrix: {
      IDLE: { x: '45%', y: '62%', size: '47%', z: 30 },
      RUNNING: { x: '35%', y: '68%', size: '68%', z: 30 },
      STRESSED: { x: '45%', y: '62%', size: '47%', z: 30 },
      ARGUING: { x: '35%', y: '68%', size: '68%', z: 30 }
    }
  },
  {
    id: 'critic', role: 'critic', label: 'Ban Kiểm Soát', side: 'right', order: 4,
    posMatrix: {
      IDLE: { x: '50%', y: '62%', size: '47%', z: 35 },
      RUNNING: { x: '62%', y: '68%', size: '58%', z: 35 },
      STRESSED: { x: '50%', y: '62%', size: '47%', z: 35 },
      ARGUING: { x: '68%', y: '68%', size: '52%', z: 35 }
    }
  },
  {
    id: 'executor-alpha', role: 'executor-alpha', label: 'Ban Thực Thi Alpha', side: 'left', order: 5,
    posMatrix: {
      IDLE: { x: '62%', y: '80%', size: '75%', z: 40 },
      RUNNING: { x: '52%', y: '80%', size: '90%', z: 40 },
      STRESSED: { x: '62%', y: '80%', size: '75%', z: 40 },
      ARGUING: { x: '52%', y: '80%', size: '90%', z: 40 }
    }
  },
  {
    id: 'executor-beta', role: 'executor-beta', label: 'Ban Thực Thi Beta', side: 'right', order: 6,
    posMatrix: {
      IDLE: { x: '40%', y: '80%', size: '75%', z: 40 },
      RUNNING: { x: '58%', y: '80%', size: '90%', z: 40 },
      STRESSED: { x: '40%', y: '80%', size: '75%', z: 40 },
      ARGUING: { x: '58%', y: '80%', size: '90%', z: 40 }
    }
  }
];

// ─── 🏛️ CLEAN AGENT AVATAR WRAPPER (v61.0 - Performance Optimized) ────────────────
const AgentAvatar = ({ seat, status, opacity, activeState }: any) => {
  const { label, posMatrix, role, side } = seat;
  
  // 🚀 [ANTI-FLICKER-SPRITES]: Khởi tạo trước bộ tham chiếu ảnh cho 4 trạng thái để tránh tải lại
  const visuals = useMemo(() => getAgentVisualStates(role), [role]);

  const agentTransform = (role === 'master' || side === 'right')
    ? 'translate(0%, -100%)'
    : 'translate(-100%, -100%)';

  const currentStatus = status.toUpperCase();
  const currentPos = posMatrix[currentStatus] || posMatrix.IDLE;

  // Xác định bộ lọc phát sáng (drop-shadow filter) khi active
  const isActive = activeState === 'RUNNING' || activeState === 'ARGUING';
  const shadowFilter = isActive 
    ? (role === 'critic' 
       ? 'drop-shadow(0 0 12px rgba(244,63,94,0.65))'
       : role === 'planner'
       ? 'drop-shadow(0 0 12px rgba(99,102,241,0.65))'
       : role === 'master'
       ? 'drop-shadow(0 0 14px rgba(245,158,11,0.7))'
       : 'drop-shadow(0 0 12px rgba(6,182,212,0.65))')
    : 'none';

  return (
    <div
      className="absolute transition-all duration-300 ease-out"
      style={{
        left: currentPos.x,
        top: currentPos.y,
        width: currentPos.size,
        zIndex: currentPos.z || 5,
        opacity: opacity,
        transform: agentTransform,
        transformOrigin: (role === 'master' || side === 'right') ? 'bottom left' : 'bottom right',
        filter: shadowFilter,
        willChange: 'left, top, width, transform, filter'
      }}
    >
      {/* Áp dụng breathing animation lên wrapper trong để tránh ảnh hưởng đến layout transform ngoài */}
      <div className={`relative w-full h-full ${isActive ? 'animate-breathing' : ''}`}>
        {(Object.keys(visuals) as Array<keyof typeof visuals>).map((stateKey) => {
          const isCurrent = stateKey === activeState;
          return (
            <img
              key={stateKey}
              src={visuals[stateKey]}
              alt={`${label}-${stateKey}`}
              className={`w-full h-auto transition-opacity duration-300 ${
                isCurrent 
                  ? 'opacity-100 relative z-10' 
                  : 'opacity-0 absolute inset-0 pointer-events-none z-0'
              }`}
            />
          );
        })}
      </div>
    </div>
  );
};

// ─── 💬 HIGH-Z FLOATING SPEECH BUBBLE (Relocated above Agent Heads) ────────────
const FloatingSpeechBubble = ({ seat, status, message, showMsg, sortedByRecency }: any) => {
  const { id, label, posMatrix, role, side, order } = seat;
  const displayMsg = getStrategicMessage(message, role, status);

  if (!showMsg || !displayMsg) return null;

  const currentStatus = status.toUpperCase();
  const currentPos = posMatrix[currentStatus] || posMatrix.IDLE;

  const agentTransform = (role === 'master' || side === 'right')
    ? 'translate(0%, -100%)'
    : 'translate(-100%, -100%)';

  const layerRank = sortedByRecency.findIndex((x: any) => x.id === id);
  const dynamicZIndex = 110 + (layerRank !== -1 ? layerRank : order);

  // Gán màu viền & màu chữ tương ứng với ban ngành
  let accentColor = 'rgba(6, 182, 212, 0.4)'; // mặc định cyan
  let titleColor = 'text-cyan-400';
  let glowShadow = 'rgba(6, 182, 212, 0.15)';

  if (role === 'master') {
    accentColor = 'rgba(245, 158, 11, 0.4)';
    titleColor = 'text-amber-400';
    glowShadow = 'rgba(245, 158, 11, 0.2)';
  } else if (role === 'critic') {
    accentColor = 'rgba(244, 63, 94, 0.4)';
    titleColor = 'text-rose-400';
    glowShadow = 'rgba(244, 63, 94, 0.2)';
  } else if (role === 'planner') {
    accentColor = 'rgba(99, 102, 241, 0.4)';
    titleColor = 'text-indigo-400';
    glowShadow = 'rgba(99, 102, 241, 0.2)';
  } else if (role === 'receptionist') {
    accentColor = 'rgba(14, 165, 233, 0.4)';
    titleColor = 'text-sky-400';
    glowShadow = 'rgba(14, 165, 233, 0.2)';
  } else if (role === 'summarizer') {
    accentColor = 'rgba(217, 70, 239, 0.4)';
    titleColor = 'text-fuchsia-400';
    glowShadow = 'rgba(217, 70, 239, 0.2)';
  }

  return (
    <div
      className="absolute transition-all duration-300 ease-out pointer-events-none"
      style={{
        left: currentPos.x,
        top: currentPos.y,
        width: currentPos.size,
        zIndex: dynamicZIndex,
        transform: agentTransform,
        transformOrigin: (role === 'master' || side === 'right') ? 'bottom left' : 'bottom right',
        willChange: 'left, top, width, transform'
      }}
    >
      {/* Đặt bong bóng nổi hẳn lên trên đầu avatar của nhân vật */}
      <div className="absolute bottom-[104%] left-1/2 -translate-x-1/2 w-[220px] pointer-events-auto">
        <motion.div
          key={`${id}-${displayMsg.slice(0, 12)}`} // Kích hoạt transition mượt khi nội dung log thay đổi
          initial={{ opacity: 0, scale: 0.85, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.85, y: 8 }}
          transition={{ type: 'spring', damping: 22, stiffness: 380 }}
          className="relative bg-black/92 backdrop-blur-md rounded-xl p-2.5 border border-white/10"
          style={{ 
            borderColor: accentColor,
            boxShadow: `0 8px 32px rgba(0,0,0,0.7), 0 0 15px ${glowShadow}`
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-1.5 mb-1.5 border-b border-white/5 pb-1 select-none">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: accentColor.replace('0.4', '1') }} />
            <span className={`text-[9px] font-black tracking-[0.15em] uppercase ${titleColor}`}>
              {label}
            </span>
          </div>
          
          {/* Content */}
          <p className="leading-relaxed font-semibold text-[10.5px] text-white/90 break-words text-left px-0.5 max-h-[85px] overflow-y-auto custom-scroll-tiny">
            {displayMsg}
            {id === 'receptionist' && (
              <span className="inline-flex ml-1">
                <span className="animate-bounce mx-0.5">.</span>
                <span className="animate-bounce delay-100 mx-0.5">.</span>
                <span className="animate-bounce delay-200 mx-0.5">.</span>
              </span>
            )}
          </p>

          {/* Mũi tên chỉ xuống nhân vật */}
          <div 
            className="absolute bottom-[-5px] left-1/2 -translate-x-1/2 w-2.5 h-2.5 rotate-45 border-r border-b"
            style={{ 
              backgroundColor: 'rgba(10,13,20,0.96)',
              borderColor: accentColor
            }}
          />
        </motion.div>
      </div>
    </div>
  );
};

export const Zenith3DMission = ({ nodes = [] }: any) => {
  const safeNodes = nodes || [];
  const DEBUG_CALIBRATION = false;
  const DEBUG_POSTURE = 'AUTO';
  const DEBUG_SHOW_MSG = true;

  const isMeeting = safeNodes.length > 0 || DEBUG_CALIBRATION;

  // 🚀 [FAST-INDEXING-MAP]: Tạo bản đồ chỉ mục tìm kiếm O(1) tránh lặp mảng safeNodes O(N) liên tục
  const nodeLookupMap = useMemo(() => {
    const map: Record<string, any> = {};
    safeNodes.forEach((n: any) => {
      const nodeId = String(n.id || '').toLowerCase();
      const nodeTag = String(n.data?.tag || '').toLowerCase();
      const nodeLabel = String(n.data?.label || '').toLowerCase();
      
      map[nodeId] = n;
      if (nodeTag) map[nodeTag] = n;
      
      const mappingKeywords = [
        'master', 'receptionist', 'receptionist_agent', 
        'summarizer', 'planner', 'critic', 'reviewer', 
        'executor-1', 'ai-executor-1', 'executor-2', 'ai-executor-2'
      ];
      
      mappingKeywords.forEach(keyword => {
        if (nodeId === keyword || nodeTag === keyword || nodeLabel.includes(keyword)) {
          map[keyword] = n;
        }
      });
    });
    return map;
  }, [safeNodes]);

  const resolveNode = useCallback((id: string) => {
    const mapping: Record<string, string[]> = {
      'master': ['master'],
      'receptionist': ['receptionist', 'receptionist_agent'],
      'summarizer': ['summarizer'],
      'planner': ['planner'],
      'critic': ['critic', 'reviewer'],
      'executor-alpha': ['executor-1', 'ai-executor-1'],
      'executor-beta': ['executor-2', 'ai-executor-2']
    };
    
    const searchTerms = mapping[id] || [id.toLowerCase()];
    for (const term of searchTerms) {
      if (nodeLookupMap[term]) {
        return nodeLookupMap[term];
      }
    }
    return null;
  }, [nodeLookupMap]);

  const getAgentStatus = useCallback((id: string) => {
    if (DEBUG_POSTURE !== 'AUTO') return DEBUG_POSTURE;
    const node = resolveNode(id);
    if (!node) return 'IDLE';
    return String(node?.data?.status || 'IDLE').toUpperCase();
  }, [resolveNode, DEBUG_POSTURE]);

  const getAgentMessage = useCallback((id: string) => {
    const node = resolveNode(id);
    if (!node) return null;
    const logs = node?.data?.logs || [];
    const latestLog = logs.length > 0 ? logs[logs.length - 1] : null;
    return latestLog || node?.data?.msg || node?.data?.message || null;
  }, [resolveNode]);

  const getAgentOpacity = useCallback((id: string) => {
    if (DEBUG_CALIBRATION) return 1;
    const node = resolveNode(id);
    return node ? 1 : 0.98;
  }, [resolveNode, DEBUG_CALIBRATION]);

  // 💎 [RECENCY-SORTING]: Tính toán độ ưu tiên Recency để xác định Z-index
  const sortedByRecency = useMemo(() => {
    return SEATS
      .map(s => {
        const node = resolveNode(s.id);
        const logs = node?.data?.logs || [];
        const lastTs = logs.length > 0 ? logs[logs.length - 1].ts : 0;
        return { id: s.id, ts: lastTs };
      })
      .sort((a, b) => a.ts - b.ts);
  }, [resolveNode]);

  // Xác định trạng thái activeState thực tế cho từng agent
  const getActiveState = useCallback((statusStr: string): 'IDLE' | 'RUNNING' | 'STRESSED' | 'ARGUING' => {
    const currentStatus = statusStr.toUpperCase();
    if (currentStatus === 'RUNNING' || currentStatus === 'EXECUTING') return 'RUNNING';
    if (currentStatus === 'STRESSED') return 'STRESSED';
    if (currentStatus === 'ERROR' || currentStatus === 'ARGUING') return 'ARGUING';
    return 'IDLE';
  }, []);

  return (
    <div className="w-full h-full relative overflow-hidden bg-black flex items-center justify-center">
      <div className="relative w-full h-full overflow-hidden bg-black border-x border-white/5">
        
        {/* Background desk scene */}
        <div className="absolute inset-0 w-full h-full">
          <img
            src={encodeURI("/phong hop/Ban/desk-idle.png")}
            className={`absolute inset-0 w-full h-full object-fill ${isMeeting ? 'opacity-0' : 'opacity-100'}`}
          />
          <img
            src={encodeURI("/phong hop/Ban/desk-empty.png")}
            className={`absolute inset-0 w-full h-full object-fill ${isMeeting ? 'opacity-100' : 'opacity-0'}`}
          />
        </div>

        {/* Members Avatar Row (z-index 90, sits behind desk overlay) */}
        <div className="absolute inset-0 w-full h-full pointer-events-none z-[90]" style={{ imageRendering: '-webkit-optimize-contrast' }}>
          {isMeeting && SEATS.map((seat) => {
            const status = getAgentStatus(seat.id);
            return (
              <AgentAvatar
                key={seat.id}
                seat={seat}
                status={status}
                opacity={getAgentOpacity(seat.id)}
                activeState={getActiveState(status)}
              />
            );
          })}
        </div>

        {/* Desk Overlay (z-index 91) */}
        <div className={`absolute inset-0 w-full h-full pointer-events-none z-[91] ${isMeeting ? 'opacity-100' : 'opacity-0'}`}>
          <img
            src={encodeURI("/phong hop/Ban/mat_ban.png")}
            className="w-full h-full object-fill"
          />
        </div>

        {/* Speech Bubbles Overlay (z-index 110+, floats above table & avatars) */}
        <div className="absolute inset-0 w-full h-full pointer-events-none z-[110]">
          <AnimatePresence mode="popLayout">
            {isMeeting && SEATS.map((seat) => (
              <FloatingSpeechBubble
                key={`bubble-${seat.id}`}
                seat={seat}
                status={getAgentStatus(seat.id)}
                message={getAgentMessage(seat.id)}
                showMsg={DEBUG_SHOW_MSG}
                sortedByRecency={sortedByRecency}
              />
            ))}
          </AnimatePresence>
        </div>

      </div>
    </div>
  );
};

