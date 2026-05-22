import React, { memo, useState, useEffect } from 'react';
import { ScrollText, Clock, ChevronRight, Search, Trash2, RefreshCw } from 'lucide-react';
import { ZenithService } from '../../services/ZenithService';
import { useZenithStore } from '../../store/zenithStore';
import toast from 'react-hot-toast';

export const MissionHistory = memo(() => {
  const [missions, setMissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isConfirmingClear, setIsConfirmingClear] = useState(false);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);

  const formatDate = (ts: number) => {
    try {
      return new Intl.DateTimeFormat('vi-VN', { 
        day: '2-digit', 
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).format(new Date(ts * 1000));
    } catch { return 'N/A'; }
  };

  const loadMissions = async () => {
    setLoading(true);
    const data = await ZenithService.listMissions();
    setMissions(Array.isArray(data) ? data : []);
    setLoading(false);
  };

  useEffect(() => {
    loadMissions();
  }, []);

  const filteredMissions = missions.filter(m => 
    (m.title || '').toLowerCase().includes(searchTerm.toLowerCase()) || 
    (m.goal || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleInspect = async (mid: string) => {
    const data = await ZenithService.getMission(mid);
    if (data) {
      const timeStr = formatDate(data.ts);
      setInspectedFile({
        path: `Mission Report: ${data.title}`,
        content: `# ${data.title}\n\n**Goal:** ${data.goal}\n**Status:** ${data.status}\n**Time:** ${timeStr}\n\n---\n\n## Execution Details\n${data.logs?.map((l: any) => `- [${l.tag}] ${l.msg}`).join('\n') || 'No logs found.'}`
      });
    }
  };

  const handleDelete = async (e: React.MouseEvent, mid: string) => {
    e.stopPropagation();
    if (window.confirm("Master có chắc chắn muốn xoá sứ mệnh này khỏi biên niên sử?")) {
      const res = await ZenithService.deleteMission(mid);
      if (res.ok) {
        toast.success("Đã xoá sứ mệnh.");
        loadMissions();
      }
    }
  };

  const handleClearAll = async () => {
    const res = await ZenithService.clearMissions();
    if (res.ok) {
      toast.success("Biên niên sử đã được thanh tẩy.");
      setIsConfirmingClear(false);
      loadMissions();
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-[#020408] overflow-hidden">
      <div className="p-4 border-b border-white/5 flex flex-col gap-4 bg-black/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ScrollText className="w-4 h-4 text-amber-400" />
            <h3 className="text-[11px] font-black uppercase tracking-widest text-white/90">Biên niên sử Zenith</h3>
          </div>
          <div className="flex items-center gap-2">
            {!isConfirmingClear ? (
              <button 
                onClick={() => setIsConfirmingClear(true)}
                className="p-2 text-white/10 hover:text-rose-400 transition-all"
                title="Thanh tẩy toàn bộ"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            ) : (
              <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-2">
                <button onClick={handleClearAll} className="px-2 py-1 bg-rose-500/20 text-rose-400 text-[9px] font-black uppercase rounded border border-rose-500/30 hover:bg-rose-500/40">Xác nhận</button>
                <button onClick={() => setIsConfirmingClear(false)} className="text-[9px] text-white/40 uppercase font-black px-1">Huỷ</button>
              </div>
            )}
            <button onClick={loadMissions} className="p-2 text-white/20 hover:text-white transition-all">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20" />
          <input 
            type="text" 
            placeholder="Truy lục sứ mệnh..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/5 border border-white/5 rounded-xl py-2 pl-9 pr-4 text-[11px] text-white/60 focus:outline-none focus:border-amber-500/40 transition-all"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scroll p-2">
        {loading && missions.length === 0 ? (
          <div className="h-full flex items-center justify-center opacity-10 flex-col gap-4">
             <RefreshCw className="w-8 h-8 animate-spin" />
             <span className="text-[10px] font-black uppercase tracking-widest">Scanning Vault...</span>
          </div>
        ) : filteredMissions.length === 0 ? (
          <div className="h-full flex items-center justify-center opacity-10 flex-col gap-4">
             <Search className="w-8 h-8" />
             <span className="text-[10px] font-black uppercase tracking-widest">No Records Found</span>
          </div>
        ) : (
          <div className="space-y-1.5">
            {filteredMissions.map((m) => (
              <div 
                key={m.id} 
                onClick={() => handleInspect(m.id)}
                className="w-full group relative flex flex-col gap-1.5 p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-amber-500/20 transition-all text-left cursor-pointer"
              >
                <div className="flex items-center justify-between gap-4">
                  <span className="text-[12px] font-bold text-white/90 truncate flex-1">{m.title}</span>
                  <div className="flex items-center gap-1.5 opacity-30 text-[9px] font-black shrink-0">
                    <Clock className="w-3 h-3" />
                    <span>{m.ts ? formatDate(m.ts) : 'N/A'}</span>
                  </div>
                </div>
                <p className="text-[10px] text-white/30 line-clamp-1 italic">{m.goal}</p>
                <div className="absolute right-3 bottom-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                  <button 
                    onClick={(e) => handleDelete(e, m.id)}
                    className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                  <ChevronRight className="w-4 h-4 text-amber-500" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});
