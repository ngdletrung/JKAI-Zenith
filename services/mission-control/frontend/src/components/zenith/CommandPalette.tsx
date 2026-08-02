import React, { memo, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Zap, Layers, Sparkles, Terminal, FileCode2, RotateCcw, X, ShieldAlert, Cpu } from 'lucide-react';
import { useZenithStore, CognitiveMode, RightTab } from '../../store/zenithStore';
import { playSound } from '../../utils/soundEffects';

interface CommandItem {
  id: string;
  category: 'MODE' | 'TAB' | 'ACTION';
  label: string;
  sublabel: string;
  icon: React.ReactNode;
  action: () => void;
}

export const CommandPalette = memo(({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const setMode = useZenithStore(s => s.setMode);
  const setTab = useZenithStore(s => s.setTab);
  const reset = useZenithStore(s => s.reset);
  const clearTrace = useZenithStore(s => s.clearTrace);
  const setGoal = useZenithStore(s => s.setGoal);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const items: CommandItem[] = [
    // 🧠 Modes
    {
      id: 'mode-auto',
      category: 'MODE',
      label: 'Chế độ AUTO (Nhất thể)',
      sublabel: 'Tự động phân bổ tư duy & thực thi theo nhiệm vụ',
      icon: <Zap className="w-4 h-4 text-cyan-400" />,
      action: () => { setMode('auto'); playSound('click'); onClose(); }
    },
    {
      id: 'mode-fast',
      category: 'MODE',
      label: 'Chế độ FAST (Phản xạ)',
      sublabel: 'Tối ưu tốc độ phản hồi cho tác vụ ngắn',
      icon: <Zap className="w-4 h-4 text-emerald-400" />,
      action: () => { setMode('fast'); playSound('click'); onClose(); }
    },
    {
      id: 'mode-deep',
      category: 'MODE',
      label: 'Chế độ DEEP (Tư duy sâu)',
      sublabel: 'Kích hoạt lập kế hoạch nhiều bước & phản biện',
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      action: () => { setMode('deep'); playSound('click'); onClose(); }
    },

    // 📌 Tabs
    {
      id: 'tab-progress',
      category: 'TAB',
      label: 'Tab Tiến Trình (Progress)',
      sublabel: 'Nhật ký thực thi & dấu vết nơ-ron realtime',
      icon: <Layers className="w-4 h-4 text-sky-400" />,
      action: () => { setTab('progress'); playSound('tab'); onClose(); }
    },
    {
      id: 'tab-plan',
      category: 'TAB',
      label: 'Tab Kế Hoạch (Plan)',
      sublabel: 'Xem sơ đồ chiến lược & đề xuất hệ thống',
      icon: <Sparkles className="w-4 h-4 text-fuchsia-400" />,
      action: () => { setTab('plan'); playSound('tab'); onClose(); }
    },
    {
      id: 'tab-tasks',
      category: 'TAB',
      label: 'Tab Nhiệm Vụ (Tasks)',
      sublabel: 'Xem danh sách tác vụ chi tiết (task.md)',
      icon: <Layers className="w-4 h-4 text-amber-400" />,
      action: () => { setTab('tasks'); playSound('tab'); onClose(); }
    },
    {
      id: 'tab-walkthrough',
      category: 'TAB',
      label: 'Tab Giải Pháp (Walkthrough)',
      sublabel: 'Hồ sơ kết quả nhiệm vụ chính thức',
      icon: <Layers className="w-4 h-4 text-cyan-400" />,
      action: () => { setTab('walkthrough'); playSound('tab'); onClose(); }
    },
    {
      id: 'tab-explorer',
      category: 'TAB',
      label: 'Tab Khám Phá Nơ-ron (Neural Explorer)',
      sublabel: 'Xem cấu trúc nhân sự & mạng lưới tác vụ',
      icon: <Cpu className="w-4 h-4 text-indigo-400" />,
      action: () => { setTab('explorer'); playSound('tab'); onClose(); }
    },
    {
      id: 'tab-filelab',
      category: 'TAB',
      label: 'Tab Phòng Thí Nghiệm Tệp (Sovereign File Lab)',
      sublabel: 'Duyệt & sửa trực tiếp mã nguồn ứng dụng',
      icon: <FileCode2 className="w-4 h-4 text-emerald-400" />,
      action: () => { setTab('filelab'); playSound('tab'); onClose(); }
    },

    // ⚡ Actions
    {
      id: 'action-reset',
      category: 'ACTION',
      label: 'Khởi Tạo Môi Trường Mới (New Mission)',
      sublabel: 'Xóa bộ nhớ tạm & làm sạch môi trường tư duy',
      icon: <RotateCcw className="w-4 h-4 text-rose-400" />,
      action: () => {
        reset();
        clearTrace();
        setGoal('');
        playSound('warning');
        onClose();
      }
    }
  ];

  const filtered = items.filter(item =>
    item.label.toLowerCase().includes(query.toLowerCase()) ||
    item.sublabel.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % (filtered.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filtered.length) % (filtered.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/70 backdrop-blur-md">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.15 }}
            className="w-full max-w-xl bg-[#080c14] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Input Header */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/5 bg-white/[0.02]">
              <Search className="w-5 h-5 text-sky-400 shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => { setQuery(e.target.value); setSelectedIndex(0); }}
                onKeyDown={handleKeyDown}
                placeholder="Nhập lệnh hoặc tìm kiếm tính năng (Ctrl + K)..."
                className="flex-1 bg-transparent border-none outline-none ring-0 text-sm text-white/90 placeholder:text-white/30 font-medium"
              />
              <span className="text-[10px] font-mono text-white/20 px-2 py-0.5 rounded bg-white/5 border border-white/10">ESC</span>
            </div>

            {/* Results List */}
            <div className="max-h-96 overflow-y-auto custom-scroll p-2 space-y-1">
              {filtered.length === 0 ? (
                <div className="py-8 text-center text-xs text-white/30">
                  Không tìm thấy lệnh phù hợp
                </div>
              ) : (
                filtered.map((item, idx) => {
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={item.id}
                      onClick={item.action}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`w-full text-left flex items-center gap-3.5 p-3 rounded-xl transition-all ${
                        isSelected
                          ? 'bg-sky-500/15 border border-sky-500/30 text-white'
                          : 'bg-transparent border border-transparent text-white/70 hover:bg-white/[0.03]'
                      }`}
                    >
                      <div className={`p-2 rounded-lg ${isSelected ? 'bg-sky-500/20' : 'bg-white/5'}`}>
                        {item.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-white/90 truncate">{item.label}</div>
                        <div className="text-[10px] text-white/40 truncate">{item.sublabel}</div>
                      </div>
                      <span className="text-[9px] font-bold text-white/20 uppercase tracking-wider px-2 py-0.5 rounded bg-white/5">
                        {item.category}
                      </span>
                    </button>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-t border-white/5 text-[10px] text-white/30">
              <div className="flex items-center gap-2">
                <span>↑↓ Điều hướng</span>
                <span>•</span>
                <span>Enter Chọn</span>
              </div>
              <span className="font-mono text-cyan-400/60">JKAI COMMAND PALETTE</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
});
