import React, { memo, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { Database, RefreshCw, Loader2, FolderOpen, Folder, FolderPlus, Plus, Trash2, FileCode2, ChevronRight, Terminal, Radio, ScrollText, FileText, Code2, Maximize2, GitBranch, CircuitBoard, X, Brain, ShieldCheck, Zap, Settings, AlertTriangle, Radar, Sparkles, Activity, ClipboardList, HardDrive, Cloud, Globe, Link2, ExternalLink, Upload, Share2 } from 'lucide-react';
import { useZenithStore, Dictionary } from '../store/zenithStore';
import { ZenithService } from '../services/ZenithService';
import { MarkdownRenderer } from './zenith/MarkdownRenderer';
import { SurgicalDiff } from './zenith/LogElements';
import { SovereignFileLab } from './SovereignFileLab';
import { MissionHistory } from './zenith/MissionHistory';
import { ProposalPlanTab } from './zenith/ProposalPlanTab';
import { ConnectionsTab } from './connections/ConnectionsTab';

// ─── NEURAL EXPLORER ─────────────────────────────────────────────────────────

const DRIVE_ICONS: Record<string, React.ReactNode> = {
  local: <HardDrive className="w-3.5 h-3.5" />,
  onedrive: <Cloud className="w-3.5 h-3.5" />,
  gdrive: <Database className="w-3.5 h-3.5" />,
  sharepoint: <Link2 className="w-3.5 h-3.5" />,
  dropbox: <Folder className="w-3.5 h-3.5" />,
  rclone: <Globe className="w-3.5 h-3.5" />,
};

const formatSize = (bytes?: number) => {
  if (bytes == null || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const getFileIconAndColor = (name: string, isDir: boolean) => {
  if (isDir) {
    return { icon: <Folder className="w-4.5 h-4.5 fill-amber-400/10" />, color: 'text-amber-400' };
  }
  const ext = name.split('.').pop()?.toLowerCase() || '';
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'].includes(ext)) {
    return { icon: <FileText className="w-4.5 h-4.5" />, color: 'text-emerald-400' };
  }
  if (['mp3', 'wav', 'ogg', 'flac'].includes(ext)) {
    return { icon: <FileText className="w-4.5 h-4.5" />, color: 'text-violet-400' };
  }
  if (['mp4', 'mkv', 'avi', 'mov'].includes(ext)) {
    return { icon: <FileText className="w-4.5 h-4.5" />, color: 'text-pink-400' };
  }
  if (['zip', 'rar', 'tar', 'gz', '7z'].includes(ext)) {
    return { icon: <FileText className="w-4.5 h-4.5" />, color: 'text-amber-500' };
  }
  if (['json', 'yaml', 'yml', 'toml', 'xml'].includes(ext)) {
    return { icon: <FileCode2 className="w-4.5 h-4.5" />, color: 'text-yellow-400' };
  }
  if (['js', 'jsx', 'ts', 'tsx', 'py', 'go', 'rs', 'c', 'cpp', 'h', 'java', 'sh', 'bat', 'ps1', 'css', 'html'].includes(ext)) {
    return { icon: <FileCode2 className="w-4.5 h-4.5" />, color: 'text-sky-400' };
  }
  if (['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md'].includes(ext)) {
    return { icon: <FileText className="w-4.5 h-4.5" />, color: 'text-indigo-400' };
  }
  return { icon: <FileText className="w-4.5 h-4.5" />, color: 'text-white/40' };
};

export const NeuralExplorer = memo(() => {
  const [tree, setTree] = useState<any[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [drives, setDrives] = useState<any[]>([]);
  const [activeDrive, setActiveDrive] = useState<string>('local');
  const [driveName, setDriveName] = useState('Local Drive');
  const [activeDriveType, setActiveDriveType] = useState<string>('local');
  // Khi browse SharePoint Site cụ thể, lưu drive_id của site đó
  const [activeSiteDriveId, setActiveSiteDriveId] = useState<string>('');
  const [activeSiteName, setActiveSiteName] = useState<string>('');
  
  // Navigation states
  const [currentPath, setCurrentPath] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // Shared With Me
  const [showShared, setShowShared] = useState(false);
  const [sharedItems, setSharedItems] = useState<any[]>([]);
  const [sharedLoading, setSharedLoading] = useState(false);
  const [sharedError, setSharedError] = useState<string | null>(null);
  
  const [isDragging, setIsDragging] = useState(false);
  
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    
    setLoading(true);
    try {
      for (const file of files) {
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.readAsDataURL(file);
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = error => reject(error);
        });
        const base64Data = base64.split(',')[1];
        const targetPath = currentPath ? `${currentPath}/${file.name}` : file.name;
        
        const body: Record<string, any> = { path: targetPath, content: base64Data, is_base64: true };
        if (activeSiteDriveId) body['drive_id'] = activeSiteDriveId;
        
        const res = await fetch(`/api/connections/${activeDrive}/explorer/write`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        if (data.error) alert(`Lỗi khi tải lên ${file.name}: ${data.error}`);
      }
      loadDir();
    } catch (err) {
      alert('Lỗi tải tệp tin');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch('/api/connections').then(r => r.json()).then(data => {
      if (Array.isArray(data)) setDrives(data);
    }).catch(() => {});
  }, []);

  // Helper: tạo URL explorer với drive_id nếu cần
  const explorerUrl = (conn: string, suffix = '', params: Record<string,string> = {}) => {
    const p = new URLSearchParams(params);
    if (activeSiteDriveId) p.set('drive_id', activeSiteDriveId);
    const qs = p.toString();
    return `/api/connections/${conn}/explorer${suffix}${qs ? '?' + qs : ''}`;
  };

  const loadDir = useCallback((pathOverride?: string) => {
    setLoading(true);
    setLoadError(null);
    if (activeDrive === 'local') {
      ZenithService.listDir()
        .then(({ nodes, error }) => {
          setTree(nodes);
          setLoadError(error || (nodes.length === 0 ? 'Workspace trống hoặc chưa mount /workspace.' : null));
        })
        .finally(() => setLoading(false));
    } else {
      const params: Record<string,string> = {};
      if (activeSiteDriveId) {
        params['drive_id'] = activeSiteDriveId;
        // Truyền path hiện tại để backend list đúng thư mục
        const usePath = pathOverride !== undefined ? pathOverride : currentPath;
        if (usePath) params['path'] = usePath;
      }
      const qs = new URLSearchParams(params).toString();
      fetch(`/api/connections/${activeDrive}/explorer${qs ? '?' + qs : ''}`)
        .then(r => r.json())
        .then(data => {
          if (data.error) { setLoadError(data.error); setTree([]); }
          else { setTree(data.children || []); }
        })
        .catch(() => setLoadError('Không thể kết nối'))
        .finally(() => setLoading(false));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDrive, activeSiteDriveId]);

  useEffect(() => { 
    loadDir(); 
    setCurrentPath(''); 
    setSearchQuery('');
  }, [loadDir]);

  const handleInspect = (path: string) => {
    if (activeDrive === 'local') {
      ZenithService.readFile(path).then(r => r?.content != null && setInspectedFile({ path, content: r.content, connId: 'local' }));
    } else {
      const params: Record<string,string> = { path };
      if (activeSiteDriveId) params['drive_id'] = activeSiteDriveId;
      const qs = new URLSearchParams(params).toString();
      fetch(`/api/connections/${activeDrive}/explorer/read?${qs}`)
        .then(r => r.json())
        .then(data => {
          if (data.content != null) setInspectedFile({ path: data.path, content: data.content, connId: activeDrive });
        })
        .catch(() => {});
    }
  };

  // Helper to resolve the items in the current path
  const getCurrentItems = useCallback(() => {
    if (activeSiteDriveId) {
      // Site mode: backend đã trả về đúng cấp, dùng tree trực tiếp
      return tree;
    }
    if (!currentPath) return tree;
    const parts = currentPath.split('/');
    let current = tree;
    for (const part of parts) {
      const found = current.find(item => item.name === part && item.type === 'directory');
      if (found && found.children) {
        current = found.children;
      } else {
        return [];
      }
    }
    return current;
  }, [tree, currentPath, activeSiteDriveId]);

  const handleFolderClick = (folderName: string) => {
    if (activeSiteDriveId) {
      // Site mode: cần load từ backend với path mới
      const newPath = currentPath ? `${currentPath}/${folderName}` : folderName;
      setCurrentPath(newPath);
      setSearchQuery('');
      loadDir(newPath);
    } else {
      setCurrentPath(prev => prev ? `${prev}/${folderName}` : folderName);
      setSearchQuery('');
    }
  };

  const handleBackClick = () => {
    if (!currentPath) return;
    const parts = currentPath.split('/');
    parts.pop();
    const newPath = parts.join('/');
    setCurrentPath(newPath);
    setSearchQuery('');
    if (activeSiteDriveId) loadDir(newPath);
  };

  const handleBreadcrumbClick = (index: number) => {
    const parts = currentPath.split('/');
    const newPath = parts.slice(0, index + 1).join('/');
    setCurrentPath(newPath);
    setSearchQuery('');
    if (activeSiteDriveId) loadDir(newPath);
  };

  const handleNewFile = async () => {
    const filename = prompt('Nhập tên tệp tin mới (ví dụ: notes.txt):');
    if (!filename) return;
    const targetPath = currentPath ? `${currentPath}/${filename}` : filename;
    try {
      const body: Record<string, any> = { path: targetPath, is_dir: false };
      if (activeSiteDriveId) body['drive_id'] = activeSiteDriveId;
      const res = await fetch(`/api/connections/${activeDrive}/explorer/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.error) alert(data.error);
      else loadDir();
    } catch { alert('Không thể tạo file'); }
  };

  const handleNewFolder = async () => {
    const foldername = prompt('Nhập tên thư mục mới:');
    if (!foldername) return;
    const targetPath = currentPath ? `${currentPath}/${foldername}` : foldername;
    try {
      const body: Record<string, any> = { path: targetPath, is_dir: true };
      if (activeSiteDriveId) body['drive_id'] = activeSiteDriveId;
      const res = await fetch(`/api/connections/${activeDrive}/explorer/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.error) alert(data.error);
      else loadDir();
    } catch { alert('Không thể tạo thư mục'); }
  };

  const handleDelete = async (e: React.MouseEvent, itemPath: string, isDir: boolean) => {
    e.stopPropagation();
    if (!confirm(`Bạn có chắc chắn muốn xóa ${isDir ? 'thư mục' : 'tệp tin'} này không?`)) return;
    try {
      const params: Record<string,string> = { path: itemPath, is_dir: String(isDir) };
      if (activeSiteDriveId) params['drive_id'] = activeSiteDriveId;
      const qs = new URLSearchParams(params).toString();
      const res = await fetch(`/api/connections/${activeDrive}/explorer/delete?${qs}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (data.error) alert(data.error);
      else loadDir();
    } catch { alert('Không thể xóa mục này'); }
  };

  const currentItems = getCurrentItems();
  const filteredItems = currentItems.filter(item => 
    item.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group folders first
  const sortedItems = useMemo(() => {
    return [...filteredItems].sort((a, b) => {
      if (a.type === 'directory' && b.type !== 'directory') return -1;
      if (a.type !== 'directory' && b.type === 'directory') return 1;
      return a.name.localeCompare(b.name);
    });
  }, [filteredItems]);

  const connDrives = drives.filter(d => d.status === 'active' || d.status === 'syncing');

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]">
      {/* Drive Selectors */}
      <div className="shrink-0 p-4 border-b border-white/5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {DRIVE_ICONS[activeDrive] || <HardDrive className="w-4 h-4 text-sky-400" />}
            <h3 className="text-[11px] font-black uppercase tracking-widest text-white/90">{driveName}</h3>
          </div>
          <button onClick={() => loadDir()} className="p-2 text-white/20 hover:text-white"><RefreshCw className="w-3.5 h-3.5" /></button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button onClick={() => { setActiveDrive('local'); setDriveName('Local Drive'); }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-wider transition-all ${activeDrive === 'local' ? 'bg-sky-500/20 border-sky-500/40 text-sky-400' : 'bg-white/5 border-white/10 text-white/30 hover:bg-white/10'}`}>
            <HardDrive className="w-3.5 h-3.5" />Local
          </button>
          {connDrives.map(d => (
            <button key={d.id} onClick={() => { setActiveDrive(d.id); setDriveName(d.name); setActiveDriveType(d.type); setShowShared(false); }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-wider transition-all ${activeDrive === d.id ? 'bg-sky-500/20 border-sky-500/40 text-sky-400' : 'bg-white/5 border-white/10 text-white/30 hover:bg-white/10'}`}>
              {DRIVE_ICONS[d.type] || <Cloud className="w-3.5 h-3.5" />}{d.name}
            </button>
          ))}
          {/* Nut Shared With Me chi hien khi dang dung OneDrive/SharePoint */}
          {['onedrive','sharepoint','gdrive'].includes(activeDriveType) && (
            <button
              onClick={async () => {
                const next = !showShared;
                setShowShared(next);
                if (next && sharedItems.length === 0) {
                  setSharedLoading(true);
                  setSharedError(null);
                  try {
                    const res = await fetch(`/api/connections/${activeDrive}/explorer/shared`);
                    const data = await res.json();
                    if (data.error) setSharedError(data.error);
                    else setSharedItems(data.items || []);
                  } catch(e: any) { setSharedError(e.message); }
                  setSharedLoading(false);
                }
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-wider transition-all ${
                showShared ? 'bg-purple-500/20 border-purple-500/40 text-purple-400' : 'bg-white/5 border-white/10 text-white/30 hover:bg-white/10'
              }`}>
              <Share2 className="w-3.5 h-3.5" />Shared
            </button>
          )}
        </div>
      </div>

      {/* Explorer Controls: Back, Path Breadcrumbs, Search */}
      <div className="shrink-0 px-4 py-3 bg-white/[0.01] border-b border-white/5 space-y-2.5">
        {/* Site Context Banner */}
        {activeSiteDriveId && (
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse shrink-0" />
            <span className="text-[10px] text-orange-300/90 font-medium truncate flex-1">{activeSiteName}</span>
            <button
              onClick={() => { setActiveSiteDriveId(''); setActiveSiteName(''); setCurrentPath(''); setSearchQuery(''); }}
              className="text-[9px] text-orange-400/60 hover:text-orange-300 font-medium shrink-0"
            >
              ← Quay lại
            </button>
          </div>
        )}
        <div className="flex items-center gap-2">
          {/* Back Button */}
          <button 
            onClick={handleBackClick} 
            disabled={!currentPath}
            className={`p-1.5 rounded-lg border transition-all ${currentPath ? 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10' : 'bg-transparent border-transparent text-white/10 cursor-not-allowed'}`}
          >
            <ChevronRight className="w-4 h-4 transform rotate-180" />
          </button>
          
          {/* Breadcrumbs Path */}
          <div className="flex-1 flex items-center gap-1 text-[11px] text-white/40 overflow-x-auto whitespace-nowrap scrollbar-none py-1">
            <span 
              onClick={() => { setCurrentPath(''); setSearchQuery(''); }}
              className="hover:text-white/85 cursor-pointer font-medium"
            >
              Root
            </span>
            {currentPath.split('/').filter(Boolean).map((part, idx) => (
              <React.Fragment key={idx}>
                <span className="text-white/15">/</span>
                <span 
                  onClick={() => handleBreadcrumbClick(idx)}
                  className="hover:text-white/85 cursor-pointer font-medium max-w-[80px] truncate"
                >
                  {part}
                </span>
              </React.Fragment>
            ))}
          </div>

          {/* New Actions */}
          <div className="flex items-center gap-1 shrink-0">
            <button 
              onClick={handleNewFile}
              title="Tạo file mới" 
              className="p-1 rounded bg-white/5 border border-white/10 text-white/50 hover:text-white hover:bg-white/10 transition-all"
            >
              <Plus className="w-3 h-3" />
            </button>
            <button 
              onClick={handleNewFolder}
              title="Tạo thư mục mới" 
              className="p-1 rounded bg-white/5 border border-white/10 text-white/50 hover:text-white hover:bg-white/10 transition-all"
            >
              <FolderPlus className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Search inside folder */}
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Tìm kiếm trong thư mục hiện tại..."
          className="w-full px-3 py-1.5 rounded-lg bg-black/40 border border-white/5 text-[11px] text-white placeholder-white/20 focus:outline-none focus:border-sky-500/40 transition-all"
        />
      </div>

      {/* Folders & Files Grid Layout */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className="flex-1 min-h-0 overflow-y-auto custom-scroll p-3 relative"
      >
        {isDragging && (
          <div className="absolute inset-0 bg-sky-500/10 border-2 border-dashed border-sky-500/40 rounded-2xl flex flex-col items-center justify-center pointer-events-none z-50 backdrop-blur-[2px]">
            <Upload className="w-8 h-8 text-sky-400 animate-bounce mb-2" />
            <p className="text-[11px] font-bold text-sky-400">Thả các tệp tin vào đây để tải lên</p>
          </div>
        )}

        {showShared ? (
          // === SHARED WITH ME PANEL ===
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Share2 className="w-4 h-4 text-purple-400" />
              <h4 className="text-[11px] font-black uppercase tracking-widest text-purple-300">Chia sẻ &amp; Sites</h4>
              <span className="text-[9px] text-white/20 font-normal normal-case tracking-normal ml-1">({sharedItems.length} mục)</span>
              <button
                onClick={async () => {
                  setSharedLoading(true); setSharedError(null);
                  try {
                    const res = await fetch(`/api/connections/${activeDrive}/explorer/shared`);
                    const data = await res.json();
                    if (data.error) setSharedError(data.error);
                    else setSharedItems(data.items || []);
                  } catch(e: any) { setSharedError(e.message); }
                  setSharedLoading(false);
                }}
                className="ml-auto p-1 text-white/20 hover:text-white"
              ><RefreshCw className="w-3 h-3" /></button>
            </div>
            {sharedLoading ? (
              <div className="flex items-center justify-center py-8 opacity-40"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : sharedError ? (
              <div className="p-4 text-[11px] text-amber-400/80 bg-amber-500/5 border border-amber-500/10 rounded-xl">{sharedError}</div>
            ) : sharedItems.length === 0 ? (
              <div className="p-6 text-center text-[11px] text-white/30">Không có tài liệu nào được chia sẻ.</div>
            ) : (
              <div className="grid grid-cols-1 gap-1.5">
                {sharedItems.map((item, idx) => {
                  const isSite = item.source === 'sharepoint_site';
                  const isDir = item.type === 'directory';
                  const { icon, color } = isSite
                    ? { icon: <Link2 className="w-4 h-4" />, color: 'text-orange-400' }
                    : getFileIconAndColor(item.name, isDir);
                  const sizeLabel = item.size > 0
                    ? item.size > 1048576 ? `${(item.size/1048576).toFixed(1)} MB`
                    : item.size > 1024 ? `${(item.size/1024).toFixed(0)} KB`
                    : `${item.size} B` : '';
                  const subtitle = isSite
                    ? (item.web_url ? new URL(item.web_url).pathname : '')
                    : `👤 ${item.shared_by}${sizeLabel ? ` • ${sizeLabel}` : ''}`;

                  const handleSiteClick = async () => {
                    if (!isSite) return;
                    try {
                      const res = await fetch(`/api/connections/${activeDrive}/explorer/site-drive?site_id=${encodeURIComponent(item.site_id)}`);
                      const data = await res.json();
                      if (data.error) { alert(data.error); return; }
                      setActiveSiteDriveId(data.drive_id);
                      setActiveSiteName(item.name);
                      setCurrentPath('');
                      setSearchQuery('');
                      setShowShared(false);
                    } catch(e: any) { alert('Lỗi khi mở site: ' + e.message); }
                  };

                  return (
                    <div
                      key={idx}
                      onClick={isSite ? handleSiteClick : undefined}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all group ${isSite ? 'bg-orange-500/[0.04] hover:bg-orange-500/[0.08] border-orange-500/10 hover:border-orange-500/20 cursor-pointer' : 'bg-purple-500/[0.03] hover:bg-purple-500/[0.08] border-purple-500/10 hover:border-purple-500/20'}`}
                    >
                      <div className={color}>{icon}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] text-white/85 font-medium truncate">{item.name}</p>
                        <p className="text-[10px] text-white/30 truncate">{subtitle}</p>
                      </div>
                      {isSite ? (
                        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1">
                          <span className="text-[9px] text-orange-400/70 font-medium">Duyệt →</span>
                          <a href={item.web_url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                            className="p-1.5 rounded-lg bg-white/5 text-white/30 hover:text-white hover:bg-white/10 transition-all" title="Mở trong trình duyệt">
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      ) : (
                        <a
                          href={item.web_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 transition-all"
                          title="Mở trong trình duyệt"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        ) : loading ? (
          <div className="h-full flex items-center justify-center opacity-20"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : loadError ? (
          <div className="p-6 text-center text-[11px] text-amber-400/80 leading-relaxed">{loadError}</div>
        ) : sortedItems.length === 0 ? (
          <div className="p-6 text-center text-[11px] text-white/30">Thư mục trống.</div>
        ) : (
          <div className="grid grid-cols-1 gap-1">
            {sortedItems.map(item => {
              const isDir = item.type === 'directory';
              const { icon, color } = getFileIconAndColor(item.name, isDir);
              const ext = item.name.split('.').pop()?.toUpperCase() || '';
              
              return (
                <div 
                  key={item.path} 
                  onClick={() => isDir ? handleFolderClick(item.name) : handleInspect(item.path)}
                  className="group flex items-center gap-3 px-3 py-2 rounded-xl bg-white/[0.01] hover:bg-white/[0.04] border border-white/[0.02] hover:border-white/5 cursor-pointer transition-all relative"
                >
                  {/* File Icon */}
                  <div className={color}>
                    {icon}
                  </div>

                  {/* Name and Metadata */}
                  <div className="flex-1 min-w-0">
                    <p className="text-[11.5px] font-bold text-white/80 group-hover:text-white truncate">{item.name}</p>
                    {isDir ? (
                      <p className="text-[9px] text-white/20 mt-0.5">Thư mục • {item.children?.length || 0} mục</p>
                    ) : (
                      <p className="text-[9px] text-white/20 mt-0.5">
                        Tệp {ext} • {formatSize(item.size)}
                      </p>
                    )}
                  </div>

                  {/* Hover Actions: Delete */}
                  <button 
                    onClick={(e) => handleDelete(e, item.path, isDir)}
                    title="Xóa"
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-white/30 hover:text-rose-400 hover:bg-rose-500/10 transition-all shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
});

const ARTIFACT_EMPTY_HINT: Record<string, { icon: React.ReactNode; text: string }> = {
  plan: { icon: <Sparkles className="w-10 h-10 text-fuchsia-400/40" />, text: 'Chưa có kế hoạch. Sau khi Planner ghi implementation_plan.md, nội dung sẽ hiện tại đây.' },
  tasks: { icon: <FileText className="w-10 h-10 text-amber-400/40" />, text: 'Chưa có nhiệm vụ. Sau khi Planner ghi task.md, nội dung sẽ hiện tại đây.' },
  walkthrough: { icon: <ScrollText className="w-10 h-10 text-cyan-400/40" />, text: 'Chưa có giải pháp. Kết quả JKAI dài hoặc walkthrough.md sẽ hiện ở đây sau mission.' },
};

const ARTIFACT_TYPE_META: Record<string, { icon: React.ReactNode; gradient: string; border: string }> = {
  plan: {
    icon: <Sparkles className="w-4 h-4" />,
    gradient: 'from-fuchsia-500/10 to-transparent',
    border: 'border-fuchsia-500/20',
  },
  tasks: {
    icon: <ClipboardList className="w-4 h-4" />,
    gradient: 'from-amber-500/10 to-transparent',
    border: 'border-amber-500/20',
  },
  walkthrough: {
    icon: <ScrollText className="w-4 h-4" />,
    gradient: 'from-cyan-500/10 to-transparent',
    border: 'border-cyan-500/20',
  },
};

export const ArtifactGallery = memo(({ content, type }: { content: string, type: string }) => {
  const { setInspectedFile } = useZenithStore();
  const meta = ARTIFACT_TYPE_META[type] || ARTIFACT_TYPE_META.walkthrough;
  const emptyHint = ARTIFACT_EMPTY_HINT[type];

  const artifacts = useMemo(() => {
    const raw = (content || '').trim();
    if (
      !raw || 
      raw.startsWith('# Chưa có') || 
      raw.startsWith('# No ') || 
      raw.includes('Chưa có dữ liệu') ||
      raw.includes('Chưa có kế hoạch') ||
      raw.includes('Chưa có nhiệm vụ') ||
      raw.includes('Chưa có giải pháp') ||
      raw.includes('No Documentation Found') ||
      raw.includes('Khởi tạo nhiệm vụ để tạo dữ liệu') ||
      raw.includes('Không tìm thấy Hồ sơ')
    ) return [];
    if (type === 'walkthrough') {

      const firstLine = raw.split('\n')[0].replace(/^#+\s*/, '').trim();
      return [{ title: firstLine || 'Giải pháp kiến trúc', body: raw.replace(/^#+\s*.*\n?/, '') }];
    }
    if (type === 'plan') {
      // If plan content is just the raw prompt fallback without Markdown plan structure
      if (!raw.includes('#') && !raw.includes('##') && !raw.includes('step_') && !raw.includes('Step') && !raw.includes('CHECKLIST') && !raw.includes('LỘ TRÌNH')) {
        return [];
      }
      const firstLine = raw.split('\n')[0].replace(/^#+\s*/, '').trim();
      return [{ title: firstLine || 'Kế hoạch kiến trúc', body: raw.replace(/^#+\s*.*\n?/, '') }];
    }

    if (blocks.length <= 1 && !raw.includes('\n#')) return [{ title: type === 'tasks' ? 'Nhiệm vụ' : type, body: raw }];
    return blocks.map(b => ({ title: b.split('\n')[0].trim(), body: b.split('\n').slice(1).join('\n').trim() }));
  }, [content, type]);

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]">
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4 space-y-3">
        {artifacts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-4 px-6 text-center">
            <div className="opacity-30">{emptyHint?.icon}</div>
            <p className="text-[11px] leading-relaxed max-w-xs text-white/30">{emptyHint?.text || 'Chưa có dữ liệu.'}</p>
          </div>
        ) : (
          artifacts.map((art, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => setInspectedFile({ path: art.title, content: art.body })}
              className={`group rounded-xl bg-white/[0.02] border border-white/[0.06] overflow-hidden cursor-pointer transition-all hover:bg-white/[0.04] ${type === 'tasks' ? 'hover:border-amber-500/30' : 'hover:border-cyan-500/30'}`}
            >
              <div className={`bg-gradient-to-r ${meta.gradient} p-4`}>
                <div className="flex items-center gap-2.5 mb-3">
                  <div className={`${type === 'tasks' ? 'text-amber-400' : 'text-cyan-400'}`}>{meta.icon}</div>
                  <h4 className="text-[13px] font-bold text-white/90">{art.title}</h4>
                </div>
                <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed text-white/50 line-clamp-4 group-hover:line-clamp-none transition-all">
                  <MarkdownRenderer content={art.body} />
                </div>
                <div className="mt-3 flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-white/20 group-hover:text-white/40 transition-colors">
                  <Maximize2 className="w-3 h-3" />
                  Xem chi tiết
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
});

// ─── FILE PREVIEW (INSPECTOR) ────────────────────────────────────────────────

export const FilePreview = memo(() => {
  const inspectedFile = useZenithStore(s => s.inspectedFile);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const language = useZenithStore(s => s.language);
  
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [saving, setSaving] = useState(false);
  
  useEffect(() => {
    if (inspectedFile) {
      setEditedContent(inspectedFile.content);
      setIsEditing(false);
    }
  }, [inspectedFile]);

  if (!inspectedFile) return null;
  const dict = Dictionary[language as keyof typeof Dictionary] || Dictionary.en;

  const handleSave = async () => {
    setSaving(true);
    try {
      const connId = inspectedFile.connId || 'local';
      const res = await fetch(`/api/connections/${connId}/explorer/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: inspectedFile.path,
          content: editedContent
        })
      });
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setInspectedFile({ ...inspectedFile, content: editedContent });
        setIsEditing(false);
      }
    } catch {
      alert('Không thể lưu file');
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="absolute inset-0 z-50 bg-[#060910] flex flex-col min-h-0 overflow-hidden">
      <div className="shrink-0 p-4 border-b border-white/5 flex items-center justify-between bg-black/40">
        <div className="flex items-center gap-3">
          <FileCode2 className="w-4 h-4 text-sky-400" />
          <span className="text-[11px] font-black uppercase tracking-widest text-white/90 truncate max-w-[200px]">{inspectedFile.path.split('/').pop()}</span>
        </div>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button 
                onClick={handleSave} 
                disabled={saving}
                className="px-2.5 py-1 rounded-lg bg-emerald-500/20 border border-emerald-500/35 text-emerald-400 text-[10px] font-bold uppercase tracking-wider hover:bg-emerald-500/30 transition-all flex items-center gap-1"
              >
                {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                Lưu
              </button>
              <button 
                onClick={() => { setIsEditing(false); setEditedContent(inspectedFile.content); }}
                className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white/40 text-[10px] font-bold uppercase tracking-wider hover:bg-white/10 transition-all"
              >
                Hủy
              </button>
            </>
          ) : (
            <button 
              onClick={() => setIsEditing(true)}
              className="px-2.5 py-1 rounded-lg bg-sky-500/20 border border-sky-500/35 text-sky-400 text-[10px] font-bold uppercase tracking-wider hover:bg-sky-500/30 transition-all"
            >
              Sửa
            </button>
          )}
          <button onClick={() => setInspectedFile(null)} className="p-2 text-white/20 hover:text-rose-400 transition-colors"><X className="w-4 h-4" /></button>
        </div>
      </div>
      <div className="flex-1 min-h-0 p-4 flex flex-col">
        {isEditing ? (
          <textarea
            value={editedContent}
            onChange={e => setEditedContent(e.target.value)}
            className="flex-1 w-full bg-[#030509] text-white/90 font-mono text-[12px] p-4 border border-white/5 rounded-xl focus:outline-none focus:border-sky-500/40 transition-all custom-scroll resize-none leading-relaxed"
          />
        ) : (
          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll">
            <MarkdownRenderer content={`\`\`\`typescript\n${inspectedFile.content}\n\`\`\``} />
          </div>
        )}
      </div>
    </motion.div>
  );
});

const getCliColor = (tag: string, msg: string = '') => {
  const t = tag.toUpperCase();
  const m = msg.toUpperCase();
  if (t === 'JKAI' || t === 'MISSION_RESULT' || t === 'RESULT' || t === 'DONE' || t === 'ZENITH') return 'text-cyan-400';
  if (t === 'CHAT_INTEL' || t.includes('SUMMARIZER') || t.includes('LEGAL') || t.includes('THU_KY')) return 'text-fuchsia-400';
  if (t === 'PROGRESS' || t.includes('EXECUTOR') || t.includes('ALPHA') || t.includes('BETA')) return 'text-blue-400';
  if (t === 'MASTER' || t.startsWith('MASTER')) return 'text-amber-400';
  if (t === 'ERROR' || t === 'WARN' || t === 'WARNING') return 'text-rose-500';
  if (m.includes('PHASE') || m.includes('STAGE')) return 'text-white/90';
  return 'text-gray-500'; // Mặc định là màu xám nền
};

const isImportantTag = (tag: string, msg: string = '') => {
  const t = tag.toUpperCase();
  const m = msg.toUpperCase();
  const isPhase = m.includes('STAGE') || m.includes('PHASE') || m.includes('ONLINE');
  // Chỉ Master, JKAI, Lỗi hoặc Dòng chuyển giai đoạn quan trọng mới nổi bật
  return ['MISSION_RESULT', 'RESULT', 'DONE', 'ERROR', 'WARN', 'WARNING', 'ZENITH'].includes(t) || t.startsWith('MASTER') || isPhase;
};

const toTitleCase = (str: string, lang: string = 'vi') => {
  if (!str) return '';
  const upper = str.toUpperCase();
  if (upper === 'JKAI') return 'JKAI';
  
  if (lang === 'vi') {
    if (
      upper.includes('GATEWAY') || upper.includes('RECEPTIONIST') || 
      upper.includes('LE_TAN')
    ) return 'Ban Trợ Lý';
    if (
      upper.includes('DATA_SCOUT') || upper.includes('RESEARCH') || upper.includes('SEARCH') || 
      upper.includes('ANTIGRAVITY') || upper.includes('FORGE') || 
      upper.includes('KIẾN TẠO') || upper.includes('KIENTAO') || 
      upper.includes('TÌNH BÁO') || upper.includes('TINHBAO') || upper.includes('CREATOR')
    ) return 'Ban Trợ Lý';
    if (
      upper.includes('SYSTEM') || upper.includes('ADMIN') || upper.includes('HANH_CHINH') ||
      upper.includes('SUMMARIZER') || upper.includes('SYNTHESIS') || 
      upper.includes('LEGAL') || upper.includes('THU_KY') || 
      upper === 'CHAT_INTEL'
    ) return 'Ban Thư Ký';
    if (upper.includes('PLANNER') || upper.includes('THOUGHT') || upper.includes('BAN_KE_HOACH') || upper.includes('TƯ DUY') || upper.includes('STEWARD') || upper.includes('MEMORY') || upper.includes('QUẢN GIA')) return 'Ban Kế Hoạch';
    if (upper.includes('EXECUTOR') || upper.includes('ALPHA') || upper.includes('BETA') || upper === 'PROGRESS' || upper === 'TIẾN TRÌNH' || upper === 'TIẾN_TRÌNH') return 'Ban Thực Thi';
    if (
      upper === 'JKAI' || upper.includes('MISSION_RESULT') || 
      upper.includes('RESULT') || upper.includes('DONE') || 
      upper === 'ZENITH'
    ) return 'JKAI';
    if (upper.includes('CRITIC') || upper.includes('AUDIT') || upper.includes('REVIEW') || upper.includes('GUARDRAIL') || upper.includes('PHAN_BIEN') || upper.includes('PHẢN BIỆN') || upper.includes('BAN_KIEM_SOAT')) return 'Ban Kiểm Soát';
    if (upper.includes('MASTER') || upper.includes('USER')) return 'Master';
    return 'Ban Trợ Lý';
  } else {
    if (
      upper.includes('GATEWAY') || upper.includes('RECEPTIONIST') || 
      upper.includes('LE_TAN')
    ) return 'Assistant Dept';
    if (upper.includes('PLANNER') || upper.includes('THOUGHT') || upper.includes('STEWARD') || upper.includes('MEMORY')) return 'Planning Dept';
    if (upper.includes('EXECUTOR') || upper.includes('ALPHA') || upper.includes('BETA') || upper === 'PROGRESS' || upper === 'TIẾN TRÌNH' || upper === 'TIẾN_TRÌNH') return 'Execution Dept';
    if (
      upper.includes('SUMMARIZER') || upper.includes('SYNTHESIS') || 
      upper.includes('LEGAL') || upper.includes('THU_KY') || 
      upper === 'CHAT_INTEL'
    ) return 'Secretariat';
    if (
      upper === 'JKAI' || upper.includes('MISSION_RESULT') || 
      upper.includes('RESULT') || upper.includes('DONE') || 
      upper === 'ZENITH'
    ) return 'JKAI';
    if (upper.includes('CRITIC') || upper.includes('AUDIT') || upper.includes('REVIEW') || upper.includes('GUARDRAIL')) return 'Audit Dept';
    if (
      upper.includes('DATA_SCOUT') || upper.includes('RESEARCH') || upper.includes('SEARCH') || 
      upper.includes('ANTIGRAVITY') || upper.includes('FORGE') || 
      upper.includes('KIẾN TẠO') || upper.includes('KIENTAO') || 
      upper.includes('TÌNH BÁO') || upper.includes('TINHBAO') ||
      upper.includes('SYSTEM') || upper.includes('ADMIN') || upper.includes('HANH_CHINH')
    ) return 'Administrative Dept';
    if (upper.includes('MASTER') || upper.includes('USER')) return 'Master';
    return 'Assistant Dept';
  }
  
  return str.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('_');
};

/** Map display label → node color class to keep left column consistent with DAG nodes */
const TAG_COLOR_MAP: Record<string, string> = {
  'Master':           'text-amber-400',
  'JKAI':             'text-cyan-400',
  'Ban Kế Hoạch':     'text-blue-300', // Professional blue
  'Ban Kiểm Soát':    'text-orange-400', // Professional amber/orange
  'Ban Thực Thi':     'text-emerald-400', // Professional green
  'Ban Trợ Lý':       'text-teal-300', // Subtle teal
  'Ban Thư Ký':       'text-fuchsia-400', // Kept fuchsia per request
  'Ban Hành Chính':   'text-slate-300', // Subtle corporate slate
};

/** Format timestamp → Vietnamese locale HH:mm:ss DD/MM */
const formatVnTime = (ts: number | undefined): string => {
  if (!ts) return '';
  const d = new Date(ts < 1e12 ? ts * 1000 : ts);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  return `${hh}:${mm}:${ss} ${dd}/${mo}`;
};

const ProcessLogTab = memo(() => {
  const progressLogs = useZenithStore(s => s.progressLogs);
  const language = useZenithStore(s => s.language);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sortedLogs = useMemo(() => {
    return [...progressLogs].sort((a, b) => (a.ts || 0) - (b.ts || 0));
  }, [progressLogs]);

  const maxTagWidth = useMemo(() => {
    let longestLength = 0;
    sortedLogs.forEach((l: any) => {
      const tag = (l.tag || 'SYS').toUpperCase();
      const msg = (l.msg || '').replace(/\[⏱️\s*[\d.]+\s*s\]/g, '').trim();
      if (!msg) return;

      const important = isImportantTag(tag, msg);
      const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER');

      let displayTag = '';
      if (important || isThought) {
        displayTag = (isThought && l.source && l.source.toUpperCase() !== tag)
          ? `${toTitleCase(tag, language)}:${toTitleCase(l.source, language)}`
          : toTitleCase(tag, language);
      } else {
        displayTag = toTitleCase(tag, language);
      }
      
      const fullLabel = `[${displayTag}]`;
      if (fullLabel.length > longestLength) {
        longestLength = fullLabel.length;
      }
    });

    if (longestLength === 0) return 85;
    // Estimate width based on character count: ~7.5px per character + 12px padding/bracket spacing
    return Math.max(85, longestLength * 7.5 + 12);
  }, [sortedLogs, language]);

  // 🛡️ [SCROLL-GUARD]: Khi Master lăn chuột lên → tạm dừng auto-scroll 2 phút
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;

    if (isAtBottom) {
      userScrolledRef.current = false;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    } else {
      userScrolledRef.current = true;
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
      resumeTimerRef.current = setTimeout(() => {
        userScrolledRef.current = false;
      }, 120_000); // 2 phút
    }
  };

  useEffect(() => {
    if (!userScrolledRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [sortedLogs]);

  useEffect(() => {
    return () => { if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current); };
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#060910]/60">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll pt-4 px-4 pb-16"
      >
      <div className="flex flex-col font-sans font-[300] tracking-wide text-[13px] leading-relaxed">
        {sortedLogs.length === 0 && (
          <span className="text-gray-500 italic">Chờ tín hiệu nơ-ron...</span>
        )}
        {sortedLogs.map((l: any, i: number) => {
          const tag = (l.tag || 'SYS').toUpperCase();
          const msg = (l.msg || '')
            .replace(/\[⏱️\s*[\d.]+\s*s\]/g, '')
            .replace(/📥\s*\[GATEWAY\]\s*/g, '')
            .replace(/💎🫡\s*\[ZENITH\]:\s*/g, '')
            .replace(/💎\s*\[ZENITH\]:\s*/g, '')
            .replace(/⚙️\s*/g, '')
            .replace(/⚔️\s*\[[^\]]+\]\s*/g, '') // e.g. ⚔️ [T4: SURGERY]
            .replace(/\[T\d+:\s*[^\]]+\]\s*/g, '') // e.g. [T4: SURGERY]
            .replace(/ZENITH_\d+_([0-9a-fA-F]{4,8})/g, (match: string, hex: string) => `Z-${hex.slice(0,4).toUpperCase()}`)
            .replace(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/g, '$3/$2/$1 $4:$5:$6') // ISO → VN
            .replace(/(\d{4})-(\d{2})-(\d{2})/g, '$3/$2/$1') // YYYY-MM-DD → DD/MM/YYYY
            .trim();
          if (!msg) return null;
          
          const isJkaiOrMaster = tag === 'JKAI' || tag === 'MISSION_RESULT' || tag === 'RESULT' || tag === 'DONE' || tag === 'ZENITH' || tag === 'MASTER' || tag.startsWith('MASTER');
          const isErrorOrWarn = tag === 'ERROR' || tag === 'WARN' || tag === 'WARNING';
          
          const baseTag = toTitleCase(tag, language);
          const displayTag = (tag.includes('THOUGHT') || tag.includes('PLANNER')) && l.source && l.source.toUpperCase() !== tag
            ? `${baseTag}:${toTitleCase(l.source, language)}`
            : baseTag;

          // Color: match display label to DAG node color
          let tagColor = TAG_COLOR_MAP[baseTag] ?? 'text-gray-400';
          let msgColor = 'text-gray-400';
          let isBold = false;

          if (isJkaiOrMaster && tag !== 'MASTER' && !tag.startsWith('MASTER')) {
            tagColor = 'text-cyan-400'; msgColor = 'text-white/85'; isBold = true;
          } else if (tag === 'MASTER' || tag.startsWith('MASTER')) {
            tagColor = 'text-amber-400'; msgColor = 'text-white/85'; isBold = true;
          } else if (isErrorOrWarn) {
            tagColor = 'text-rose-500'; msgColor = 'text-rose-400'; isBold = false;
          } else if (displayTag === 'JKAI') {
            tagColor = 'text-cyan-400'; msgColor = 'text-white/85'; isBold = true;
          }

          const isThought = tag.includes('THOUGHT') || tag.includes('PLANNER');

          return (
            <div 
              key={l.id || i} 
              id={`log-${l.id}`} 
              className={`my-1 flex items-start gap-2.5 ${isJkaiOrMaster ? '' : 'opacity-70'}`}
            >
              {/* Timestamp column */}
              <span className="shrink-0 text-[10px] text-white/20 mt-[3px] w-[70px] tabular-nums leading-tight">
                {formatVnTime(l.ts)}
              </span>
              <span 
                style={{ width: `${maxTagWidth}px` }} 
                className={`${tagColor} ${isBold ? 'font-semibold' : 'font-normal'} shrink-0 text-[11.5px] mt-[2px] whitespace-nowrap overflow-hidden text-ellipsis`}
              >
                [{displayTag}]
              </span>
              <div className={`prose prose-invert compact-prose max-w-none prose-sm flex-1 min-w-0 ${msgColor} font-normal`}>
                <MarkdownRenderer content={msg} />
              </div>
            </div>
          );
        })}
      </div>
      </div>
    </div>
  );
});

// ─── TAB CONTENT MANAGER ─────────────────────────────────────────────────────

export const TabContent = memo(() => {
  const rightTab = useZenithStore(s => s.rightTab);
  const currentArtifacts = useZenithStore(s => s.currentArtifacts);
  const backgroundProposals = useZenithStore(s => s.backgroundProposals);
  const language = useZenithStore(s => s.language);
  const modifiedFiles = useZenithStore(s => s.modifiedFiles);
  const fileEdits = useZenithStore(s => s.fileEdits);
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const dict = Dictionary[language as keyof typeof Dictionary] || Dictionary.en;
  const artifactContent = currentArtifacts[rightTab as keyof typeof currentArtifacts] || '';

  const planRaw = (currentArtifacts['plan'] || '').trim();
  const hasRealPlanContent = !!(
    planRaw && 
    !planRaw.startsWith('# Chưa có') && 
    !planRaw.startsWith('# No ') && 
    !planRaw.includes('Chưa có dữ liệu') && 
    !planRaw.includes('Chưa có kế hoạch') &&
    !planRaw.includes('No Documentation Found')
  );
  const hasProposals = backgroundProposals && backgroundProposals.length > 0;

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden min-h-0">
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {rightTab === 'explorer' && <NeuralExplorer />}
        {rightTab === 'filelab' && <SovereignFileLab />}
        {rightTab === 'progress' && <ProcessLogTab />}
        {rightTab === 'plan' && (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {hasProposals && <ProposalPlanTab />}
            {hasRealPlanContent && <ArtifactGallery content={currentArtifacts['plan'] || ''} type="plan" />}
            {!hasProposals && !hasRealPlanContent && (
              <div className="h-full flex flex-col items-center justify-center gap-4 px-6 text-center">
                <div className="opacity-30"><Sparkles className="w-10 h-10 text-fuchsia-400/40" /></div>
                <p className="text-[11px] leading-relaxed max-w-xs text-white/30">
                  {language === 'vi' ? 'Chưa có kế hoạch hay đề xuất nào.' : 'No proposals or plan yet.'}
                </p>
              </div>
            )}
          </div>
        )}
        {['tasks', 'walkthrough'].includes(rightTab) && <ArtifactGallery content={artifactContent} type={rightTab} />}
        {rightTab === 'changes' && (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-black/20">
            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4 space-y-4">
            {fileEdits.length === 0 && modifiedFiles.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-3 px-6 text-center opacity-40">
                <CircuitBoard className="w-12 h-12" />
                <p className="text-[11px] leading-relaxed max-w-xs">
                  Chưa có thay đổi file. Khi JKAI sửa code (agent loop / patch), diff sẽ hiện tại đây qua sự kiện file_edit.
                </p>
              </div>
            ) : (
              <>
                {fileEdits.map((e, i) => (
                  <div key={`${e.path}-${e.ts}-${i}`} className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
                    <button
                      type="button"
                      onClick={() => ZenithService.readFile(e.path).then(r => r?.content && setInspectedFile({ path: e.path, content: r.content }))}
                      className="w-full px-4 py-3 flex items-center justify-between hover:bg-sky-500/10 text-left border-b border-white/5"
                    >
                      <span className="text-[12px] font-bold text-sky-300 truncate">{e.path}</span>
                      <span className="text-[9px] uppercase text-white/30 shrink-0 ml-2">Mở tab</span>
                    </button>
                    {e.diff ? <SurgicalDiff diff={e.diff} /> : null}
                  </div>
                ))}
                {modifiedFiles.filter(p => !fileEdits.some(e => e.path === p)).map(path => (
                  <button key={path} type="button" onClick={() => ZenithService.readFile(path).then(r => r?.content && setInspectedFile({ path, content: r.content }))} className="w-full p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-sky-500/10 text-left truncate">
                    <span className="text-[12px] font-bold text-white/80">{path.split('/').pop()}</span>
                  </button>
                ))}
              </>
            )}
            </div>
          </div>
        )}
        {rightTab === 'logs' && <MissionHistory />}
        {rightTab === 'connections' && <ConnectionsTab />}
      </div>
      <FilePreview />
    </div>
  );
});
