import React, { memo, useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ─── 💬 ELITE STRATEGIC MESSAGE FLOW (v66.0 - Full Action-Purpose Dictionary) ───────────
// Tới phiên Ban nào thao tác gì thì tóm lược ngắn gọn, rõ ràng mục đích của thao tác đó.
// Không lấy từng mảnh chữ từ log stream để triệt tiêu hoàn toàn hiện tượng nhảy chữ & nặng GPU.
const getStrategicMessage = (message: any, role: string, status: string, tagStr: string = ''): string | null => {
  const s = String(status || '').toUpperCase();

  // 🛡️ Ẩn hoàn toàn khi nhàn rỗi hoặc đã xong
  if (s === 'IDLE' || s === 'DONE') return null;

  let raw = '';
  if (message && typeof message === 'object') {
    raw = String(message.msg || message.message || message.text || '');
  } else {
    raw = String(message || '');
  }

  const lowerMsg = raw.toLowerCase();
  const upperTag = String(tagStr || '').toUpperCase();

  // 1. Trường hợp có lỗi cảnh báo hoặc tranh luận gay gắt
  if (s === 'ERROR' || s === 'ARGUING') {
    return "Kiểm tra sự cố phát sinh, phân tích nguyên nhân và điều chỉnh phương án xử lý.";
  }

  // 2. BAN THỰC THI (Alpha & Beta): Nhận diện chi tiết 12 nhóm thao tác công cụ kỹ thuật
  if (role.startsWith('executor')) {
    // 2.1. Tra cứu & tìm kiếm thông tin Web
    if (
      lowerMsg.includes('search') || lowerMsg.includes('tavily') || lowerMsg.includes('searx') ||
      lowerMsg.includes('google') || lowerMsg.includes('tìm kiếm') || lowerMsg.includes('tra cứu')
    ) {
      return "Tra cứu và thu thập thông tin dữ liệu từ nguồn bên ngoài phục vụ nhiệm vụ.";
    }
    // 2.2. Truy cập URL & trích xuất trang mạng
    if (
      lowerMsg.includes('http') || lowerMsg.includes('fetch') || lowerMsg.includes('scrape') ||
      lowerMsg.includes('crawl') || lowerMsg.includes('browser') || lowerMsg.includes('playwright') ||
      lowerMsg.includes('trích xuất trang') || lowerMsg.includes('url')
    ) {
      return "Truy cập liên kết mạng và trích xuất nội dung chi tiết từ trang đích.";
    }
    // 2.3. Truy vấn kho tri thức nội bộ / RAG / Vector DB
    if (
      lowerMsg.includes('qdrant') || lowerMsg.includes('rag') || lowerMsg.includes('vector') ||
      lowerMsg.includes('embed') || lowerMsg.includes('neural cache') || lowerMsg.includes('knowledge') ||
      lowerMsg.includes('kho tri thức') || lowerMsg.includes('ngữ nghĩa')
    ) {
      return "Truy vấn kho tri thức nội bộ và đối chiếu dữ liệu ngữ nghĩa trong hệ thống.";
    }
    // 2.4. Quét thư mục & định vị mã nguồn
    if (
      lowerMsg.includes('list_dir') || lowerMsg.includes('glob') || lowerMsg.includes('grep') ||
      lowerMsg.includes('find_by_name') || lowerMsg.includes('thư mục') || lowerMsg.includes('danh sách tệp')
    ) {
      return "Rà soát cấu trúc thư mục và định vị các tệp tin liên quan trong dự án.";
    }
    // 2.5. Đọc & phân tích tệp tài liệu / mã nguồn
    if (
      lowerMsg.includes('read') || lowerMsg.includes('view_file') || lowerMsg.includes('cat ') ||
      lowerMsg.includes('inspect') || lowerMsg.includes('parse') || lowerMsg.includes('đọc') ||
      lowerMsg.includes('xem tệp')
    ) {
      return "Đọc và phân tích nội dung chi tiết của tài liệu, mã nguồn trong hệ thống.";
    }
    // 2.6. Soạn thảo, tạo mới & chỉnh sửa tệp tin
    if (
      lowerMsg.includes('write') || lowerMsg.includes('edit') || lowerMsg.includes('replace') ||
      lowerMsg.includes('patch') || lowerMsg.includes('create_file') || lowerMsg.includes('ghi') ||
      lowerMsg.includes('cập nhật tệp') || lowerMsg.includes('chỉnh sửa') || lowerMsg.includes('đã sửa')
    ) {
      return "Soạn thảo, chỉnh sửa và cập nhật nội dung vào tệp tin hệ thống.";
    }
    // 2.7. Chạy kiểm thử, biên dịch & xác thực
    if (
      lowerMsg.includes('test') || lowerMsg.includes('pytest') || lowerMsg.includes('vitest') ||
      lowerMsg.includes('build') || lowerMsg.includes('compile') || lowerMsg.includes('lint') ||
      lowerMsg.includes('verify') || lowerMsg.includes('kiểm thử') || lowerMsg.includes('biên dịch')
    ) {
      return "Chạy kiểm thử tự động, biên dịch và xác thực tính ổn định của hệ thống.";
    }
    // 2.8. Kiểm tra dịch vụ hạ tầng, Docker, Database & API
    if (
      lowerMsg.includes('docker') || lowerMsg.includes('container') || lowerMsg.includes('redis') ||
      lowerMsg.includes('postgres') || lowerMsg.includes('sql') || lowerMsg.includes('health') ||
      lowerMsg.includes('port') || lowerMsg.includes('endpoint') || lowerMsg.includes('hạ tầng')
    ) {
      return "Kiểm tra trạng thái dịch vụ hạ tầng, cơ sở dữ liệu và kết nối hệ thống.";
    }
    // 2.9. Thực thi kịch bản lệnh hệ thống (Shell / Python / Script)
    if (
      lowerMsg.includes('bash') || lowerMsg.includes('shell') || lowerMsg.includes('command') ||
      lowerMsg.includes('exec') || lowerMsg.includes('python') || lowerMsg.includes('script') ||
      lowerMsg.includes('lệnh')
    ) {
      return "Thực thi kịch bản lệnh hệ thống và xử lý tác vụ kỹ thuật chuyên sâu.";
    }
    // 2.10. Phân tích số liệu & tính toán dữ liệu
    if (
      lowerMsg.includes('calculate') || lowerMsg.includes('dataset') || lowerMsg.includes('json') ||
      lowerMsg.includes('csv') || lowerMsg.includes('thống kê') || lowerMsg.includes('tính toán') ||
      lowerMsg.includes('phân tích dữ liệu')
    ) {
      return "Xử lý, phân tích số liệu và chuẩn hóa cấu trúc dữ liệu đầu ra.";
    }
    // 2.11. Hoàn tất bước thực thi và bàn giao
    if (
      lowerMsg.includes('hoàn tất') || lowerMsg.includes('thành công') || lowerMsg.includes('completed') ||
      lowerMsg.includes('finished') || lowerMsg.includes('bàn giao')
    ) {
      return "Hoàn tất bước thực thi kỹ thuật và bàn giao dữ liệu cho bộ phận kiểm soát.";
    }
    // 2.12. Mặc định theo vai trò Alpha / Beta
    if (role === 'executor-beta') {
      return "Phối hợp xử lý song song tác vụ nhánh và đối chiếu dữ liệu thực thi.";
    }
    return "Triển khai xử lý các bước công việc chính theo kế hoạch đã đề ra.";
  }

  // 3. MASTER (Chủ tọa điều hành tối cao)
  if (role === 'master') {
    if (
      lowerMsg.includes('delphi') || lowerMsg.includes('council') || lowerMsg.includes('hội đồng') ||
      lowerMsg.includes('debate') || lowerMsg.includes('consensus') || lowerMsg.includes('đồng thuận')
    ) {
      return "Chủ trì phiên họp Hội đồng AI phân tích đa chiều và thống nhất phương án.";
    }
    if (
      lowerMsg.includes('hitl') || lowerMsg.includes('approve') || lowerMsg.includes('approval') ||
      lowerMsg.includes('phê duyệt') || lowerMsg.includes('xác nhận quyền')
    ) {
      return "Xem xét và phê duyệt quyền thực thi cho thao tác quan trọng.";
    }
    if (
      lowerMsg.includes('hoàn tất') || lowerMsg.includes('nghiệm thu') || lowerMsg.includes('kết thúc') ||
      upperTag === 'DONE' || upperTag === 'MISSION_RESULT'
    ) {
      return "Nghiệm thu kết quả cuối cùng từ các bộ phận và hoàn tất phiên họp.";
    }
    if (lowerMsg.includes('giám sát') || lowerMsg.includes('điều phối') || lowerMsg.includes('tiến độ')) {
      return "Giám sát tiến độ tổng thể và điều phối nhịp độ giữa các bộ phận.";
    }
    return "Giao nhiệm vụ và chỉ đạo các Phòng Ban phối hợp thực thi.";
  }

  // 4. BAN TRỢ LÝ (Cổng tiếp nhận, phân loại ý định & tình báo)
  if (role === 'receptionist') {
    if (
      upperTag.includes('MEMORY') || upperTag.includes('QUAN_GIA') ||
      lowerMsg.includes('memory') || lowerMsg.includes('ngữ cảnh') || lowerMsg.includes('lịch sử') ||
      lowerMsg.includes('truy xuất')
    ) {
      return "Truy xuất lịch sử hội thoại và đồng bộ ngữ cảnh dữ liệu liên quan.";
    }
    if (
      upperTag.includes('SCOUT') || upperTag.includes('RESEARCH') || upperTag.includes('TINHBAO') ||
      upperTag.includes('TÌNH BÁO') || upperTag.includes('SEARCH') ||
      lowerMsg.includes('tình báo') || lowerMsg.includes('trinh sát') || lowerMsg.includes('thu thập')
    ) {
      return "Thu thập nhanh thông tin tình báo và dữ liệu nền tảng phục vụ cuộc họp.";
    }
    if (
      upperTag.includes('FORGE') || upperTag.includes('KIENTAO') || upperTag.includes('KIẾN TẠO') ||
      upperTag.includes('CREATOR') || upperTag.includes('ANTIGRAVITY') ||
      lowerMsg.includes('kiến tạo') || lowerMsg.includes('khởi tạo công cụ')
    ) {
      return "Khởi tạo công cụ chuyên biệt và chuẩn bị tài nguyên hỗ trợ thực thi.";
    }
    if (
      upperTag === 'RESULT' || upperTag === 'DONE' || upperTag === 'MISSION_RESULT' || upperTag === 'JKAI' ||
      lowerMsg.includes('báo cáo') || lowerMsg.includes('kết quả') || lowerMsg.includes('phản hồi')
    ) {
      return "Chuẩn hóa nội dung phản hồi và báo cáo trực tiếp kết quả tới Master.";
    }
    return "Tiếp nhận yêu cầu từ Master, phân tích ý định và điều phối bộ phận phụ trách.";
  }

  // 5. BAN KẾ HOẠCH (Kiến trúc sư chiến lược & lập lộ trình DAG)
  if (role === 'planner') {
    if (
      lowerMsg.includes('replan') || lowerMsg.includes('retry') || lowerMsg.includes('revise') ||
      lowerMsg.includes('hiệu chỉnh') || lowerMsg.includes('điều chỉnh') || lowerMsg.includes('lập lại')
    ) {
      return "Hiệu chỉnh lại kế hoạch và tối ưu hóa phương án theo phản biện kỹ thuật.";
    }
    if (
      lowerMsg.includes('dag') || lowerMsg.includes('graph') || lowerMsg.includes('lộ trình') ||
      lowerMsg.includes('step') || lowerMsg.includes('bước') || lowerMsg.includes('분rã') ||
      lowerMsg.includes('phân rã')
    ) {
      return "Thiết kế sơ đồ lộ trình thực thi đa bước và phân bổ thứ tự ưu tiên.";
    }
    if (
      upperTag === 'MANIFEST' || lowerMsg.includes('agent:') || lowerMsg.includes('tool') ||
      lowerMsg.includes('model') || lowerMsg.includes('phân công') || lowerMsg.includes('lựa chọn')
    ) {
      return "Lựa chọn công cụ chuyên dụng và phân công nhân sự phù hợp cho từng tác vụ.";
    }
    if (
      upperTag === 'THOUGHT' || upperTag === 'TƯ DUY' ||
      lowerMsg.includes('suy luận') || lowerMsg.includes('tư duy') || lowerMsg.includes('đánh giá')
    ) {
      return "Phân tích chuyên sâu yêu cầu, đánh giá dữ kiện và suy luận hướng giải quyết.";
    }
    return "Phân tích yêu cầu và lập kế hoạch triển khai chi tiết.";
  }

  // 6. BAN KIỂM SOÁT (Thẩm định độc lập, phản biện & an ninh)
  if (role === 'critic') {
    if (
      upperTag.includes('GUARDRAIL') || lowerMsg.includes('guardrail') || lowerMsg.includes('security') ||
      lowerMsg.includes('safety') || lowerMsg.includes('bảo mật') || lowerMsg.includes('an toàn') ||
      lowerMsg.includes('rủi ro')
    ) {
      return "Kiểm duyệt tiêu chuẩn an toàn bảo mật và rà soát rủi ro hệ thống.";
    }
    if (
      upperTag.includes('ADVERSARIAL') || upperTag.includes('PHAN_BIEN') || upperTag === 'PHẢN BIỆN' ||
      lowerMsg.includes('phản biện') || lowerMsg.includes('đối chiếu') || lowerMsg.includes('mâu thuẫn')
    ) {
      return "Phản biện chéo phương án, đối chiếu tính xác thực và phát hiện lỗ hổng logic.";
    }
    if (
      lowerMsg.includes('reject') || lowerMsg.includes('fail') || lowerMsg.includes('chưa đạt') ||
      lowerMsg.includes('yêu cầu sửa') || lowerMsg.includes('bổ sung') || lowerMsg.includes('sai sót')
    ) {
      return "Chỉ ra các điểm chưa đạt chuẩn và yêu cầu bộ phận thực thi hiệu chỉnh lại.";
    }
    if (
      lowerMsg.includes('approve') || lowerMsg.includes('pass') || lowerMsg.includes('valid') ||
      lowerMsg.includes('đạt chuẩn') || lowerMsg.includes('chấp thuận') || lowerMsg.includes('hợp lệ')
    ) {
      return "Xác nhận kết quả đạt tiêu chuẩn chất lượng và chuyển giao tổng hợp báo cáo.";
    }
    if (
      upperTag.includes('AUDIT') || upperTag.includes('REVIEW') ||
      lowerMsg.includes('audit') || lowerMsg.includes('review') || lowerMsg.includes('thẩm định')
    ) {
      return "Thẩm định chất lượng kỹ thuật và kiểm tra độ chuẩn xác của kết quả thực thi.";
    }
    return "Kiểm tra chéo chất lượng kết quả và rà soát độ chính xác.";
  }

  // 7. BAN THƯ KÝ (Tổng hợp báo cáo, hành chính & lưu trữ biên niên sử)
  if (role === 'summarizer') {
    if (
      lowerMsg.includes('lưu trữ') || lowerMsg.includes('archive') || lowerMsg.includes('nhật ký') ||
      lowerMsg.includes('hồ sơ') || lowerMsg.includes('memory') || lowerMsg.includes('ghi nhận')
    ) {
      return "Ghi nhận nhật ký nhiệm vụ và lưu trữ hồ sơ vào kho dữ liệu dài hạn.";
    }
    if (
      lowerMsg.includes('format') || lowerMsg.includes('markdown') || lowerMsg.includes('walkthrough') ||
      lowerMsg.includes('trình bày') || lowerMsg.includes('biên soạn') || lowerMsg.includes('chuẩn hóa')
    ) {
      return "Biên soạn, chuẩn hóa định dạng văn bản và hoàn thiện báo cáo trình Master.";
    }
    if (
      upperTag.includes('SYSTEM') || upperTag.includes('ADMIN') || upperTag.includes('HANH_CHINH') ||
      lowerMsg.includes('hành chính') || lowerMsg.includes('đồng bộ') || lowerMsg.includes('khởi tạo')
    ) {
      return "Thực hiện thủ tục hành chính hệ thống và đồng bộ trạng thái giữa các phòng ban.";
    }
    if (
      upperTag.includes('SYNTHESIS') || lowerMsg.includes('chắt lọc') || lowerMsg.includes('thu thập') ||
      lowerMsg.includes('đúc kết')
    ) {
      return "Thu thập dữ liệu từ các bộ phận và chắt lọc những kết quả trọng tâm.";
    }
    return "Tổng hợp kết quả từ các ban và đúc kết báo cáo hoàn chỉnh.";
  }

  return "Phối hợp xử lý nhiệm vụ theo kế hoạch điều hành.";
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

// ─── 🏛️ MEMOIZED AGENT AVATAR (v64.0 - Zero Re-render on Log Stream) ─────────
// Bọc React.memo chặt chẽ: Khi nội dung chữ trong bong bóng thay đổi, 28 ảnh PNG nhân vật
// và bộ lọc drop-shadow GPU hoàn toàn KHÔNG bị render lại!
const AgentAvatar = memo(({ seat, status, opacity, activeState, isSpeaker }: any) => {
  const { label, posMatrix, role, side } = seat;
  const visuals = useMemo(() => getAgentVisualStates(role), [role]);

  const agentTransform = (role === 'master' || side === 'right')
    ? 'translate(0%, -100%)'
    : 'translate(-100%, -100%)';

  const currentStatus = String(status || 'IDLE').toUpperCase();
  const isSpeaking = !!isSpeaker;

  // 🏛️ [BOARDROOM DISCIPLINE]: Duy nhất chỉ người đang phát biểu (isSpeaking) mới đứng lên (RUNNING)!
  let effectiveVisualState: 'IDLE' | 'RUNNING' | 'STRESSED' | 'ARGUING' = 'IDLE';

  if (isSpeaking) {
    effectiveVisualState = (activeState === 'ARGUING' || currentStatus === 'ERROR') ? 'ARGUING' : 'RUNNING';
  } else {
    effectiveVisualState = (activeState === 'STRESSED') ? 'STRESSED' : 'IDLE';
  }

  const currentPos = posMatrix[effectiveVisualState] || posMatrix.IDLE;

  // Chỉ bật drop-shadow cho duy nhất người đang đứng phát biểu để nhẹ tải GPU tối đa
  const shadowFilter = isSpeaking
    ? (role === 'critic' 
       ? 'drop-shadow(0 0 14px rgba(244,63,94,0.75))'
       : role === 'planner'
       ? 'drop-shadow(0 0 14px rgba(99,102,241,0.75))'
       : role === 'master'
       ? 'drop-shadow(0 0 16px rgba(245,158,11,0.8))'
       : role === 'summarizer'
       ? 'drop-shadow(0 0 14px rgba(217,70,239,0.75))'
       : 'drop-shadow(0 0 14px rgba(6,182,212,0.75))')
    : 'none';

  return (
    <div
      className="absolute transition-all duration-300 ease-out"
      style={{
        left: currentPos.x,
        top: currentPos.y,
        width: currentPos.size,
        zIndex: isSpeaking ? (currentPos.z + 5) : currentPos.z || 5,
        opacity: opacity,
        transform: agentTransform,
        transformOrigin: (role === 'master' || side === 'right') ? 'bottom left' : 'bottom right',
        filter: shadowFilter
      }}
    >
      <div className={`relative w-full h-full ${isSpeaking ? 'animate-breathing' : ''}`}>
        {(Object.keys(visuals) as Array<keyof typeof visuals>).map((stateKey) => {
          const isCurrent = stateKey === effectiveVisualState;
          return (
            <img
              key={stateKey}
              src={visuals[stateKey]}
              alt={`${label}-${stateKey}`}
              decoding="async"
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
}, (prev, next) => (
  prev.seat.id === next.seat.id &&
  prev.isSpeaker === next.isSpeaker &&
  prev.activeState === next.activeState &&
  prev.status === next.status &&
  prev.opacity === next.opacity
));

// ─── 💬 TABLE-CENTERED SPEECH BUBBLE (Fixed Top on Table & Downward Expandable) ───
const FloatingSpeechBubble = memo(({ seat, message, isSpeaker }: any) => {
  const { id, label, role } = seat;
  const displayMsg = message;

  if (!isSpeaker || !displayMsg) return null;

  // Gán màu viền & màu chữ tương ứng với ban ngành
  let accentColor = 'rgba(6, 182, 212, 0.45)'; // mặc định cyan
  let titleColor = 'text-cyan-400';
  let glowShadow = 'rgba(6, 182, 212, 0.15)';

  if (role === 'master') {
    accentColor = 'rgba(245, 158, 11, 0.45)';
    titleColor = 'text-amber-400';
    glowShadow = 'rgba(245, 158, 11, 0.2)';
  } else if (role === 'critic') {
    accentColor = 'rgba(244, 63, 94, 0.45)';
    titleColor = 'text-rose-400';
    glowShadow = 'rgba(244, 63, 94, 0.2)';
  } else if (role === 'planner') {
    accentColor = 'rgba(99, 102, 241, 0.45)';
    titleColor = 'text-indigo-400';
    glowShadow = 'rgba(99, 102, 241, 0.2)';
  } else if (role === 'receptionist') {
    accentColor = 'rgba(14, 165, 233, 0.45)';
    titleColor = 'text-sky-400';
    glowShadow = 'rgba(14, 165, 233, 0.2)';
  } else if (role === 'summarizer') {
    accentColor = 'rgba(217, 70, 239, 0.45)';
    titleColor = 'text-fuchsia-400';
    glowShadow = 'rgba(217, 70, 239, 0.2)';
  }

  // 🏛️ Neo cố định đỉnh bong bóng tại vị trí trung tâm phía trên mặt bàn (top: 40%)
  // giống hệt vị trí chuẩn trên mặt bàn của Master. Khi nội dung dài, bong bóng tự động
  // mở rộng chiều cao dài xuống dọc theo thân bàn mà không bị nhảy vị trí!
  const topPos = 40;

  return (
    <div
      className="absolute pointer-events-none flex flex-col items-center"
      style={{
        top: `${topPos}%`,
        width: '100%',
        zIndex: 120
      }}
    >
      <div className="w-[18%] max-w-[22%] min-w-[162px] pointer-events-auto">
        <motion.div
          key={`speech-bubble-${id}`}
          initial={{ opacity: 0, scale: 0.9, y: 6 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 6 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="relative bg-black/92 rounded-xl p-2.5 border border-white/10 transition-all duration-200"
          style={{ 
            borderColor: accentColor,
            boxShadow: `0 8px 28px rgba(0,0,0,0.75), 0 0 14px ${glowShadow}`
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-1.5 mb-1.5 border-b border-white/5 pb-1 select-none">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: accentColor.replace('0.45', '1') }} />
            <span className={`text-[9px] font-black tracking-[0.15em] uppercase ${titleColor}`}>
              {label}
            </span>
          </div>
          
          {/* Content: Tự động mở rộng xuống dưới dọc theo mặt bàn khi nội dung dài (lên tới 280px) */}
          <p className="leading-relaxed font-semibold text-[10.5px] text-white/90 break-words text-left px-0.5 max-h-[260px] overflow-y-auto custom-scroll-tiny m-0">
            {displayMsg}
            {id === 'receptionist' && (
              <span className="inline-flex ml-1">
                <span className="animate-bounce mx-0.5">.</span>
                <span className="animate-bounce delay-100 mx-0.5">.</span>
                <span className="animate-bounce delay-200 mx-0.5">.</span>
              </span>
            )}
          </p>
        </motion.div>
      </div>
    </div>
  );
});

export const Zenith3DMission = memo(({ nodes = [] }: any) => {
  const safeNodes = nodes || [];
  const DEBUG_CALIBRATION = false;
  const DEBUG_POSTURE = 'AUTO';

  const isMeeting = safeNodes.length > 0 || DEBUG_CALIBRATION;

  // 🚀 [FAST-INDEXING-MAP]: Tạo bản đồ chỉ mục tìm kiếm O(1)
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
      'master': ['master', 'brain'],
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

  const getActiveState = useCallback((statusStr: string): 'IDLE' | 'RUNNING' | 'STRESSED' | 'ARGUING' => {
    const currentStatus = statusStr.toUpperCase();
    if (currentStatus === 'RUNNING' || currentStatus === 'EXECUTING') return 'RUNNING';
    if (currentStatus === 'STRESSED') return 'STRESSED';
    if (currentStatus === 'ERROR' || currentStatus === 'ARGUING') return 'ARGUING';
    return 'IDLE';
  }, []);

  // ─── 🎙️ EXECUTIVE SPEAKER CONTROLLER (Debounced & 3.0s Hold Time) ────────────
  interface SpeakerInfo {
    seatId: string;
    role: string;
    label: string;
    message: string;
    ts: number;
  }

  const [speaker, setSpeaker] = useState<SpeakerInfo | null>(null);
  const speakerRef = useRef<SpeakerInfo | null>(speaker);
  speakerRef.current = speaker;
  const lastSpeakerSwitchRef = useRef<number>(0);
  const holdTimerRef = useRef<any>(null);

  useEffect(() => {
    const candidates: Array<{ seat: typeof SEATS[0]; status: string; message: string; ts: number }> = [];

    SEATS.forEach(seat => {
      const status = getAgentStatus(seat.id);
      if (status === 'IDLE' || status === 'DONE') return;
      const node = resolveNode(seat.id);
      const rawMsg = getAgentMessage(seat.id);
      const rawTag = String(node?.data?.tag || '');
      const strategicMsg = getStrategicMessage(rawMsg, seat.role, status, rawTag);
      if (!strategicMsg) return;

      const logs = node?.data?.logs || [];
      const lastTs = Math.max(
        logs.length > 0 ? logs[logs.length - 1].ts : 0,
        node?.data?.ts || 0
      );

      candidates.push({
        seat,
        status,
        message: strategicMsg,
        ts: lastTs
      });
    });

    if (candidates.length === 0) {
      if (speakerRef.current) {
        if (!holdTimerRef.current) {
          holdTimerRef.current = setTimeout(() => {
            setSpeaker(null);
            holdTimerRef.current = null;
          }, 2500);
        }
      }
      return;
    }

    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }

    candidates.sort((a, b) => b.ts - a.ts);

    const topCandidate = candidates[0];
    const now = Date.now();
    const current = speakerRef.current;

    // Cùng một Ban đang phát biểu -> Cập nhật nội dung ngay lập tức (nhưng không re-render ảnh nhân vật)
    if (current && current.seatId === topCandidate.seat.id) {
      if (current.message !== topCandidate.message) {
        setSpeaker({
          seatId: topCandidate.seat.id,
          role: topCandidate.seat.role,
          label: topCandidate.seat.label,
          message: topCandidate.message,
          ts: topCandidate.ts
        });
      }
      return;
    }

    // Chuyển sang Ban khác -> Giữ tối thiểu 3.0 giây để tránh nhảy loạn
    const elapsed = now - lastSpeakerSwitchRef.current;
    const MIN_HOLD_TIME = 3000;

    if (!current || elapsed >= MIN_HOLD_TIME) {
      lastSpeakerSwitchRef.current = now;
      setSpeaker({
        seatId: topCandidate.seat.id,
        role: topCandidate.seat.role,
        label: topCandidate.seat.label,
        message: topCandidate.message,
        ts: topCandidate.ts
      });
    } else {
      const waitTime = MIN_HOLD_TIME - elapsed;
      const scheduledTimer = setTimeout(() => {
        lastSpeakerSwitchRef.current = Date.now();
        setSpeaker({
          seatId: topCandidate.seat.id,
          role: topCandidate.seat.role,
          label: topCandidate.seat.label,
          message: topCandidate.message,
          ts: topCandidate.ts
        });
      }, waitTime);
      return () => clearTimeout(scheduledTimer);
    }
  }, [safeNodes, resolveNode, getAgentStatus, getAgentMessage]);

  return (
    <div className="w-full h-full relative overflow-hidden bg-black flex items-center justify-center">
      <div className="relative w-full h-full overflow-hidden bg-black border-x border-white/5">
        
        {/* Background desk scene */}
        <div className="absolute inset-0 w-full h-full">
          <img
            src={encodeURI("/phong hop/Ban/desk-idle.png")}
            decoding="async"
            className={`absolute inset-0 w-full h-full object-fill ${isMeeting ? 'opacity-0' : 'opacity-100'}`}
          />
          <img
            src={encodeURI("/phong hop/Ban/desk-empty.png")}
            decoding="async"
            className={`absolute inset-0 w-full h-full object-fill ${isMeeting ? 'opacity-100' : 'opacity-0'}`}
          />
        </div>

        {/* Members Avatar Row (z-index 90, sits behind desk overlay, strictly memoized) */}
        <div className="absolute inset-0 w-full h-full pointer-events-none z-[90]" style={{ imageRendering: '-webkit-optimize-contrast' }}>
          {isMeeting && SEATS.map((seat) => {
            const status = getAgentStatus(seat.id);
            const isSpeaker = speaker?.seatId === seat.id;
            return (
              <AgentAvatar
                key={seat.id}
                seat={seat}
                status={status}
                opacity={1}
                activeState={getActiveState(status)}
                isSpeaker={isSpeaker}
              />
            );
          })}
        </div>

        {/* Desk Overlay (z-index 91) */}
        <div className={`absolute inset-0 w-full h-full pointer-events-none z-[91] ${isMeeting ? 'opacity-100' : 'opacity-0'}`}>
          <img
            src={encodeURI("/phong hop/Ban/mat_ban.png")}
            decoding="async"
            className="w-full h-full object-fill"
          />
        </div>

        {/* Speech Bubble Overlay (z-index 120, fixed at topPos 40% on table center, expands downwards) */}
        <div className="absolute inset-0 w-full h-full pointer-events-none z-[120]">
          <AnimatePresence mode="wait">
            {isMeeting && speaker && (() => {
              const seat = SEATS.find(s => s.id === speaker.seatId);
              if (!seat) return null;
              return (
                <FloatingSpeechBubble
                  key={`bubble-${seat.id}`}
                  seat={seat}
                  status={getAgentStatus(seat.id)}
                  message={speaker.message}
                  isSpeaker={true}
                />
              );
            })()}
          </AnimatePresence>
        </div>

      </div>
    </div>
  );
});
