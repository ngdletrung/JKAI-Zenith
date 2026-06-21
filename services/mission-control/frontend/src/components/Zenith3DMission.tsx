import React, { useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MarkdownRenderer } from './zenith/MarkdownRenderer';

// ─── 💬 ELITE STRATEGIC MESSAGE FLOW (v61.0 - Pure Action Mapping) ───────────
const getStrategicMessage = (message: any, role: string, status: string) => {
  const s = String(status || '').toUpperCase();

  // 🛡️ Ẩn bong bóng hoàn toàn khi nhàn rỗi hoặc đã hoàn thành tác vụ
  if (s === 'IDLE' || s === 'DONE') return null;

  let cleanMsg = '';
  if (message && typeof message === 'object') {
    cleanMsg = String(message.msg || message.message || message.text || '');
  } else {
    cleanMsg = String(message || '');
  }

  // 🏛️ [ZENITH-SURGICAL-STRIPPER]: Phẫu thuật triệt để phần kỹ thuật
  if (cleanMsg.includes('🧠')) {
    const parts = cleanMsg.split(':');
    if (parts.length > 1) {
      cleanMsg = parts.slice(1).join(':').trim();
    }
  }

  // Loại bỏ các thẻ kỹ thuật trong ngoặc vuông: [INFO], [RECEPTIONIST], [Task: ...], [Ngày 28/05/2026]
  cleanMsg = cleanMsg.replace(/\[.*?\]:?\s*/g, '').trim();
  // Loại bỏ ký tự đặc biệt ở đầu nếu có
  cleanMsg = cleanMsg.replace(/^[^a-zA-Z0-9\s\p{L}]+/gu, '').trim();

  const lowerMsg = cleanMsg.toLowerCase();

  // 🧠 [ZENITH-INTELLIGENT-TRANSLATOR]: Ánh xạ thông minh các hành động sang câu tiếng Việt tự nhiên, phù hợp tác vụ đang thực thi
  if (lowerMsg.includes('searching') || lowerMsg.includes('tavily') || lowerMsg.includes('search_web') || lowerMsg.includes('tìm kiếm')) {
    const match = cleanMsg.match(/(?:for|query|tìm kiếm)\s+['"“]?(.*?)['"”]?$/i);
    const query = match ? match[1].trim() : '';
    if (query) {
      return `Đang truy vấn thông tin toàn cầu về: "${query}"`;
    }
    return "Đang thực hiện truy vấn thông tin toàn cầu...";
  }

  if (lowerMsg.includes('writing file') || lowerMsg.includes('write_to_file') || lowerMsg.includes('cập nhật tệp')) {
    const fileMatch = cleanMsg.match(/(?:file|tệp|path)\s+['"“]?([a-zA-Z0-9_.\-/]+)['"”]?/i);
    const file = fileMatch ? fileMatch[1].split('/').pop() : '';
    if (file) {
      return `Đang tiến hành ghi tệp tin hệ thống: "${file}"`;
    }
    return "Đang lưu tệp tin hệ thống...";
  }

  if (lowerMsg.includes('reading file') || lowerMsg.includes('view_file') || lowerMsg.includes('đọc tệp')) {
    const fileMatch = cleanMsg.match(/(?:file|tệp|path)\s+['"“]?([a-zA-Z0-9_.\-/]+)['"”]?/i);
    const file = fileMatch ? fileMatch[1].split('/').pop() : '';
    if (file) {
      return `Đang phân tích dữ liệu từ tệp: "${file}"`;
    }
    return "Đang đọc dữ liệu tệp tin hệ thống...";
  }

  if (lowerMsg.includes('compiling') || lowerMsg.includes('building') || lowerMsg.includes('biên dịch')) {
    return "Đang biên dịch và kiểm duyệt chất lượng mã nguồn...";
  }

  if (lowerMsg.includes('hoàn tất trong') || lowerMsg.includes('completed in') || lowerMsg.includes('done')) {
    const timeMatch = cleanMsg.match(/(\d+(?:\.\d+)?\s*s)/i);
    if (timeMatch) {
      return `Đã hoàn tất xuất sắc tác vụ trong ${timeMatch[1]}!`;
    }
    return "Đã hoàn tất tiến trình xử lý tác vụ!";
  }

  if (lowerMsg.includes('error') || lowerMsg.includes('failed') || lowerMsg.includes('lỗi')) {
    return "Phát hiện sự cố hệ thống, đang cấu hình khắc phục...";
  }

  // Nếu thông điệp chứa nội dung thực thi thực tế hữu ích (như kết quả tìm kiếm, tóm tắt, phê duyệt...)
  if (cleanMsg.length > 0) {
    if (cleanMsg.length > 120) {
      return cleanMsg.slice(0, 117).trim() + '...';
    }
    return cleanMsg;
  }

  // 🎯 Các phương án mặc định tương ứng với từng Ban khi không có log text chi tiết
  if (role === 'receptionist') return "Đang tiếp nhận và điều hành hệ thống...";
  if (role === 'planner') return "Đang phân rã kế hoạch tác chiến tối ưu...";
  if (role === 'critic') return "Đang rà soát rủi ro và phê duyệt kết quả...";
  if (role === 'summarizer') return "Đang đúc rút tri thức và tổng hợp báo cáo...";
  if (role.startsWith('executor')) return "Đang triển khai thực thi tác vụ...";
  if (role === 'master') return "Đang giám sát và chỉ đạo vận hành hệ thống...";

  return "Đang xử lý...";
};;

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
    id: 'master', role: 'master', label: 'Master', side: 'center', order: 0,
    posMatrix: {
      IDLE: { x: '35%', y: '44%', size: '30%', z: 10 },
      RUNNING: { x: '20%', y: '45%', size: '47%', z: 10 },
      STRESSED: { x: '35%', y: '44%', size: '30%', z: 10 },
      ARGUING: { x: '20%', y: '45%', size: '47%', z: 10 }
    }
  },
  {
    id: 'receptionist', role: 'receptionist', label: 'Ban Trợ Lý', side: 'left', order: 1,
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
const FloatingSpeechBubble = React.forwardRef(({ seat, status, message, tag, showMsg, sortedByRecency }: any, ref: any) => {
  const { id, label, posMatrix, role, side, order } = seat;
  const displayMsg = getStrategicMessage(message, role, status);

  if (!showMsg || !displayMsg) return null;

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

  // 🏛️ Khôi phục vị trí hàng dọc
  const verticalStart = 30;
  const verticalSpacing = 10;
  const topPos = verticalStart + (order * verticalSpacing);

  return (
    <div
      ref={ref}
      className="absolute transition-all duration-300 ease-out pointer-events-none flex flex-col items-center"
      style={{
        top: `${topPos}%`,
        width: '100%',
        zIndex: dynamicZIndex
      }}
    >
      <div className="w-[18%] max-w-[22%] min-w-[160px] pointer-events-auto">
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
          <div className="leading-relaxed font-semibold text-[10.5px] text-white/90 break-words text-left px-0.5 max-h-[85px] overflow-y-auto custom-scroll-tiny">
            <MarkdownRenderer content={displayMsg} />
            {id === 'receptionist' && (
              <span className="inline-flex ml-1">
                <span className="animate-bounce mx-0.5">.</span>
                <span className="animate-bounce delay-100 mx-0.5">.</span>
                <span className="animate-bounce delay-200 mx-0.5">.</span>
              </span>
            )}
          </div>

        </motion.div>
      </div>
    </div>
  );
});

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
        'summarizer', 'planner', 
        'critic', 'critic-alpha', 'critic-beta', 'critic_alpha', 'critic_beta', 'reviewer', 
        'executor', 'executor-alpha', 'executor_alpha', 'executor-1', 'ai-executor-1', 'executor_1',
        'executor-2', 'ai-executor-2'
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
      'summarizer': ['summarizer', 'legal'],
      'planner': ['planner'],
      'critic': ['critic', 'critic-alpha', 'critic-beta', 'critic_alpha', 'critic_beta', 'reviewer'],
      'executor-alpha': ['executor', 'executor-alpha', 'executor_alpha', 'executor-1', 'ai-executor-1', 'executor_1'],
      'executor-beta': ['executor-2', 'ai-executor-2', 'executor-beta', 'executor_beta']
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

  const getAgentTag = useCallback((id: string) => {
    const node = resolveNode(id);
    if (!node) return null;
    return node?.data?.tag || null;
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

  // 💎 [LATEST-ACTIVE-SEAT]: Tìm kiếm seat ID hoạt động gần nhất để hiển thị bong bóng thoại duy nhất
  const latestActiveSeatId = useMemo(() => {
    const activeSeats = SEATS.filter(s => {
      const status = getAgentStatus(s.id);
      if (status === 'IDLE' || status === 'DONE') return false;
      const msg = getAgentMessage(s.id);
      return !!getStrategicMessage(msg, s.role, status);
    });

    if (activeSeats.length === 0) return null;

    let maxTs = -1;
    let latestId = null;

    activeSeats.forEach(s => {
      const node = resolveNode(s.id);
      const logs = node?.data?.logs || [];
      const lastTs = Math.max(
        logs.length > 0 ? logs[logs.length - 1].ts : 0,
        node?.data?.ts || 0
      );
      if (lastTs > maxTs) {
        maxTs = lastTs;
        latestId = s.id;
      }
    });

    return latestId || activeSeats[0]?.id || null;
  }, [resolveNode, getAgentStatus, getAgentMessage]);

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
            {isMeeting && SEATS.map((seat) => {
              const isSelected = seat.id === latestActiveSeatId;
              return isSelected ? (
                <FloatingSpeechBubble
                  key={`bubble-${seat.id}`}
                  seat={seat}
                  status={getAgentStatus(seat.id)}
                  message={getAgentMessage(seat.id)}
                  tag={getAgentTag(seat.id)}
                  showMsg={DEBUG_SHOW_MSG}
                  sortedByRecency={sortedByRecency}
                />
              ) : null;
            })}
          </AnimatePresence>
        </div>

      </div>
    </div>
  );
};

