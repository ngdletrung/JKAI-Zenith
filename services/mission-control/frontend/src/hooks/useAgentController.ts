import { useCallback, useRef } from 'react';
import toast from 'react-hot-toast';
import { useZenithStore, Dictionary } from '../store/zenithStore';
import { ZenithService } from '../services/ZenithService';

/**
 * 🛡️ [UTILITY]: Chuyển đổi file sang Base64
 */
const readFileAsBase64 = (file: File): Promise<{ name: string, content: string }> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ name: file.name, content: reader.result as string });
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

export const useAgentController = () => {
  const setGoal = useZenithStore(s => s.setGoal);
  const setStatus = useZenithStore(s => s.setStatus);
  const setPaused = useZenithStore(s => s.setPaused);
  const setFiles = useZenithStore(s => s.setFiles);
  const addLog = useZenithStore(s => s.addLog);
  const setStopping = useZenithStore(s => s.setStopping);
  const resetDebate = useZenithStore(s => s.resetDebate);
  const language = useZenithStore(s => s.language);

  const lastGoal = useRef<string>('');

  const runAgent = useCallback(async (overridenGoal?: string) => {
    const state = useZenithStore.getState();
    // 🛡️ [SOVEREIGN-LOGIC]: Chỉ dùng lastGoal nếu là lệnh re-run chủ động
    const currentGoal = overridenGoal || state.goal.trim();
    if (!currentGoal && !overridenGoal) return; 

    // Dự phòng cho trường hợp retry
    const finalGoal = currentGoal || lastGoal.current;
    if (!finalGoal) return;

    const isRunning = state.status === 'running';
    const isAppend = true; // Luôn giữ bối cảnh chat

    // 🛡️ [SMART-RESUME]: Chỉ reset DAG nếu là phiên mới hoàn toàn
    if (!isRunning && state.operationalLogs.length <= 1) {
      state.socketActions?.resetDAG?.();
      resetDebate();
    }

    lastGoal.current = finalGoal;
    state.addToInputHistory(finalGoal);
    setGoal('');
    
    // 👑 [MASTER-ECHO]: Backend tự publish MASTER log qua Redis (engine.publish_mission_log)
    // KHÔNG cần addLog ở Frontend — tránh lặp đôi

    try {
      if (!isRunning) {
        setStatus('running');
        toast.loading(language === 'vi' ? '🧬 Đang truyền tải dữ liệu & Khởi động...' : 'Initializing...', { id: 'ZENITH_PULSE' });
      } else {
        toast.success(Dictionary[state.language].t_queued, { id: 'ZENITH_PULSE', icon: '📝' });
      }

      // 📎 [FILE-PREPARATION]
      console.log('📎 [JKAI] Preparing files...');
      const uploadedFiles = await Promise.all(state.attachedFiles.map(readFileAsBase64));
      setFiles([]);

      // 🔱 [HITL-SHORTCUT]
      console.log('🔱 [JKAI] Checking HITL...');
      if (currentGoal.startsWith('/') || currentGoal.length > 50) {
        const pendingData = await ZenithService.getPendingHitl();
        const firstTaskId = Object.keys(pendingData)[0];

        if (firstTaskId) {
          await ZenithService.approveHitl(firstTaskId);
          toast.success('Giao thức đã được Master phê duyệt nhanh.', { icon: '🔑', id: 'ZENITH_PULSE' });
          setStatus('running');
          return;
        }
      }

      if (!state.socketActions?.submitTask) {
        console.error('❌ [JKAI] Socket Actions not found!');
        throw new Error('Neural bridge (Socket) not initialized.');
      }

      console.log('📡 [JKAI] Dispatching task via Fetch...');
      toast.loading('📡 Đang phát hỏa mệnh lệnh...', { id: 'ZENITH_PULSE' });
      
      const res = await state.socketActions.submitTask(finalGoal, state.cognitiveMode, isAppend, { files: uploadedFiles });
      
      console.log('✅ [JKAI] Server Response:', res);
      if (!res?.ok) throw new Error(res?.error || 'Uplink failure.');
      
      toast.success('Mệnh lệnh đã được tiếp nhận.', { id: 'ZENITH_PULSE', icon: '🚀' });
    } catch (e: any) {
      console.error('[JKAI-FATAL]', e);
      toast.error(e.message || 'Lỗi hệ thống.', { id: 'ZENITH_PULSE' });
      setStatus('error');
    }
  }, [language, setGoal, setStatus, setFiles, resetDebate, addLog]);

  const stopAgent = useCallback(async () => {
    try {
      setStopping(true);
      toast.loading('Đang ngắt kết nối thần kinh...', { id: 'ZENITH_PULSE' });
      await ZenithService.stopAgent();

      setStatus('idle');

      addLog({
        id: `stop-${Date.now()}`,
        tag: 'SYSTEM',
        msg: '🚨 Giao thức dừng đã được kích hoạt. Toàn bộ Đặc vụ đang túc trực chờ lệnh tiếp theo của Master.',
        ts: Date.now() / 1000,
        type: 'ai'
      });
      toast.success('Hệ thống đã dừng và bảo toàn bối cảnh.', { icon: '🛑', id: 'ZENITH_PULSE' });
    } catch (e) {
      toast.error('Cưỡng chế dừng UI do lỗi Backend.');
      setStatus('idle');
    } finally {
      setStopping(false);
    }
  }, [setStatus, addLog, setStopping]);

  const handleSystemCmd = useCallback(async (cmd: 'poweroff' | 'pause' | 'restart') => {
    try {
      const res = await ZenithService.sendSystemCmd(cmd);
      if (res.ok && cmd === 'pause') {
        const data = await res.json();
        setPaused(data.paused);
        toast.success(data.paused ? 'Hệ thống tạm dừng' : 'Hệ thống đã tiếp tục', { id: 'system-pause' });
      } else if (res.ok) {
        toast.success(`Nhiệm vụ ${cmd} đã được gửi`);
      }
    } catch {
      toast.error('Gửi lệnh thất bại');
    }
  }, [setPaused]);

  return { runAgent, stopAgent, handleSystemCmd };
};
