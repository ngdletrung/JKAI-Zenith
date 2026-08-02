import React, { memo, useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Radio, FolderOpen, Globe, Cloud, Plus, Trash2, RefreshCw,
  Loader2, CheckCircle, XCircle, AlertTriangle, Clock, Key,
  Link2, Database, HardDrive, ExternalLink,
} from 'lucide-react';

interface Connection {
  id: string;
  name: string;
  type: string;
  config: Record<string, any>;
  status: string;
  created_at: number;
  last_sync: number | null;
  error: string | null;
}

interface FieldDef {
  key: string; label: string; placeholder: string; secret?: boolean;
}

type TypeDef = {
  label: string; icon: React.ReactNode; color: string;
  fields: FieldDef[];
  supportsAuth?: boolean;
};

const CONNECTION_TYPES: Record<string, TypeDef> = {
  local: {
    label: 'Local Folder', icon: <HardDrive className="w-4 h-4" />,
    color: 'text-emerald-400',
    fields: [{ key: 'path', label: 'Folder Path', placeholder: 'D:\\Documents\\Knowledge' }],
  },
  web: {
    label: 'Web URL', icon: <Globe className="w-4 h-4" />,
    color: 'text-sky-400',
    fields: [
      { key: 'url', label: 'URL', placeholder: 'https://example.com/docs' },
      { key: 'depth', label: 'Crawl Depth', placeholder: '0' },
    ],
  },
  onedrive: {
    label: 'OneDrive Cá nhân', icon: <Cloud className="w-4 h-4" />,
    color: 'text-blue-400', supportsAuth: true,
    fields: [{ key: 'folder_path', label: 'Folder Path', placeholder: '/Documents/Knowledge' }],
  },
  gdrive: {
    label: 'Google Drive', icon: <Database className="w-4 h-4" />,
    color: 'text-yellow-400', supportsAuth: true,
    fields: [
      { key: 'folder_path', label: 'Folder Path', placeholder: 'Folder name hoặc để trống (root)' },
    ],
  },
  sharepoint: {
    label: 'SharePoint', icon: <Link2 className="w-4 h-4" />,
    color: 'text-orange-400', supportsAuth: true,
    fields: [{ key: 'site_url', label: 'Site URL', placeholder: 'https://yourorg.sharepoint.com/sites/Knowledge' }],
  },
  dropbox: {
    label: 'Dropbox', icon: <FolderOpen className="w-4 h-4" />,
    color: 'text-indigo-400',
    fields: [
      { key: 'access_token', label: 'Access Token', placeholder: '••••••••', secret: true },
      { key: 'folder_path', label: 'Folder Path', placeholder: '/Knowledge' },
    ],
  },
  rclone: {
    label: 'Rclone Cloud', icon: <Globe className="w-4 h-4" />,
    color: 'text-violet-400',
    fields: [],
  },
};

const AUTH_FIELDS: Record<string, { oauth: FieldDef[]; basic: FieldDef[] }> = {
  onedrive: {
    oauth: [
      { key: 'tenant_id', label: 'Tenant ID', placeholder: 'common hoặc tenant UUID' },
      { key: 'client_id', label: 'Client ID', placeholder: '00000000-0000-0000-0000-000000000000' },
      { key: 'client_secret', label: 'Client Secret', placeholder: '••••••••', secret: true },
    ],
    basic: [
      { key: 'username', label: 'Username', placeholder: 'user@domain.com' },
      { key: 'password', label: 'Password', placeholder: '••••••••', secret: true },
    ],
  },
  gdrive: {
    oauth: [
      { key: 'client_id', label: 'Client ID', placeholder: 'xxxx.apps.googleusercontent.com' },
      { key: 'client_secret', label: 'Client Secret (nếu có)', placeholder: '••••••••', secret: true },
      { key: 'refresh_token', label: 'Refresh Token (tự động lấy)', placeholder: '••••••••', secret: true },
      { key: 'access_token', label: 'Access Token (tự động lấy)', placeholder: '••••••••', secret: true },
    ],
    basic: [],
  },
  sharepoint: {
    oauth: [
      { key: 'tenant_id', label: 'Tenant ID', placeholder: '00000000-0000-0000-0000-000000000000' },
      { key: 'client_id', label: 'Client ID', placeholder: '00000000-0000-0000-0000-000000000000' },
      { key: 'client_secret', label: 'Client Secret', placeholder: '••••••••', secret: true },
    ],
    basic: [
      { key: 'username', label: 'Username', placeholder: 'user@domain.com' },
      { key: 'password', label: 'Password', placeholder: '••••••••', secret: true },
    ],
  },
};

function getFields(type: string, authType: string): FieldDef[] {
  if (['gdrive', 'onedrive', 'sharepoint'].includes(type)) return [];
  const meta = CONNECTION_TYPES[type];
  if (!meta) return [];
  if (!meta.supportsAuth) return meta.fields;
  const mode = authType === 'basic' ? 'basic' : 'oauth';
  const authFields = AUTH_FIELDS[type]?.[mode] || [];
  return [...meta.fields, ...authFields];
}

const StatusBadge = ({ status }: { status: string }) => {
  const config: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
    active: { icon: <CheckCircle className="w-3 h-3" />, color: 'text-emerald-400', label: 'Active' },
    syncing: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: 'text-sky-400', label: 'Syncing' },
    error: { icon: <AlertTriangle className="w-3 h-3" />, color: 'text-rose-400', label: 'Error' },
    disabled: { icon: <XCircle className="w-3 h-3" />, color: 'text-gray-500', label: 'Disabled' },
  };
  const s = config[status] || config.active;
  return (
    <span className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${s.color}`}>
      {s.icon}{s.label}
    </span>
  );
};

const ConfigDisplay = ({ type, config }: { type: string; config: Record<string, any> }) => {
  const meta = CONNECTION_TYPES[type];
  if (!meta) return null;
  const fields = getFields(type, config.auth_type || 'oauth');
  return (
    <div className="space-y-0.5 mb-3">
      {fields.map((f) => {
        const val = config[f.key];
        if (!val) return null;
        return (
          <div key={f.key} className="text-[10px] text-white/30 font-mono truncate">
            {f.label}: {f.secret ? '••••••••' : String(val).slice(0, 80)}
          </div>
        );
      })}
      {meta.supportsAuth && (
        <div className="text-[10px] text-white/30 font-mono">
          Auth: {config.auth_type === 'basic' ? 'Basic (Username/Password)' : 'OAuth'}
        </div>
      )}
    </div>
  );
};

const REQUIRED_FIELDS: Record<string, string[]> = {
  local: ['path'],
  web: ['url'],
  onedrive: [],
  gdrive: [],
  sharepoint: [],
  dropbox: [],
};

function validateForm(name: string, type: string, config: Record<string, string>): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!name.trim()) errors.name = 'Vui lòng nhập tên kết nối';
  const typeMeta = CONNECTION_TYPES[type];
  if (!typeMeta) { errors.type = 'Loại kết nối không hợp lệ'; return errors; }
  for (const key of REQUIRED_FIELDS[type] || []) {
    if (!config[key]?.trim()) {
      const field = [...(typeMeta.fields), ...(typeMeta.supportsAuth ? AUTH_FIELDS[type]?.oauth || [] : [])].find(f => f.key === key);
      errors[key] = `${field?.label || key} không được để trống`;
    }
  }
  if (typeMeta.supportsAuth) {
    const authType = config.auth_type || 'oauth';
    if (authType === 'basic') {
      if (!config.username?.trim()) errors.username = 'Username không được để trống';
      if (!config.password?.trim()) errors.password = 'Password không được để trống';
    } else {
      if (type === 'sharepoint' && !config.tenant_id?.trim() && !config.refresh_token) errors.tenant_id = 'Tenant ID không được để trống';
      if (!config.client_id?.trim() && !config.refresh_token && type !== 'onedrive') errors.client_id = 'Client ID không được để trống';
      if (!config.client_secret?.trim() && !config.refresh_token) errors.client_secret = 'Client Secret không được để trống';
    }
  }
  return errors;
}

const DEVICE_CODE_TYPES = ['onedrive', 'sharepoint', 'gdrive'];

export const ConnectionsTab = memo(() => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('local');
  const [newConfig, setNewConfig] = useState<Record<string, string>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState('');
  const [dcFlow, setDcFlow] = useState<{ flowId: string; userCode: string; uri: string; status: string } | null>(null);

  const loadConnections = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/connections');
      const data = await res.json();
      setConnections(Array.isArray(data) ? data : []);
    } catch {
      setConnections([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadConnections(); }, [loadConnections]);

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNewName(e.target.value);
    if (formErrors.name) {
      setFormErrors(prev => {
        const next = { ...prev };
        delete next.name;
        return next;
      });
    }
  };

  const resetForm = () => {
    setNewName('');
    setNewType('local');
    setNewConfig({});
    setFormErrors({});
    setApiError('');
  };

  const startRcloneAuth = async () => {
    setApiError('');
    const finalName = newName.trim() || (newType === 'gdrive' ? 'GDrive' : (newType === 'onedrive' ? 'OneDrive Cá nhân' : 'SharePoint'));
    const typeMap: Record<string, string> = {
      gdrive: 'gdrive',
      onedrive: 'onedrive',
      sharepoint: 'sharepoint',
    };
    const rcloneType = typeMap[newType];
    if (!rcloneType) {
      setApiError('Loại kết nối không hỗ trợ Rclone');
      return;
    }

    // SharePoint bắt buộc phải có Site URL
    if (newType === 'sharepoint' && !newConfig.site_url?.trim()) {
      setApiError('Vui lòng nhập SharePoint Site URL (VD: https://yourorg.sharepoint.com/sites/Knowledge)');
      return;
    }
    
    try {
      const res = await fetch('/api/rclone/start-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: finalName,
          type: rcloneType,
          client_id: newConfig.client_id || '',
          client_secret: newConfig.client_secret || '',
          site_url: newConfig.site_url || '',
        }),
      });
      const data = await res.json();
      if (data.error) { setApiError(data.error); return; }
      if (data.url) {
        window.open(data.url, '_blank');
        setShowAdd(false);
        resetForm();
        
        // Tự động kiểm tra danh sách kết nối mỗi 2 giây cho đến khi có kết nối mới hoặc hết 60s
        const startCount = connections.length;
        let elapsed = 0;
        const interval = setInterval(async () => {
          elapsed += 2000;
          try {
            const pollRes = await fetch('/api/connections');
            const pollData = await pollRes.json();
            const list = Array.isArray(pollData) ? pollData : [];
            if (list.length > startCount || elapsed >= 60000) {
              clearInterval(interval);
            }
            setConnections(list);
          } catch {
            if (elapsed >= 60000) clearInterval(interval);
          }
        }, 2000);
      }
    } catch { setApiError('Không thể bắt đầu xác thực Rclone'); }
  };

  const handleTypeChange = (type: string) => {
    const meta = CONNECTION_TYPES[type];
    setNewType(type);
    setNewConfig(meta?.supportsAuth ? { auth_type: 'oauth' } : {});
    setFormErrors({});
    setApiError('');
    if (formErrors.type) setFormErrors((prev) => { const { type: _, ...rest } = prev; return rest; });
  };

  const updateConfig = (key: string, value: string) => {
    setNewConfig((prev) => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors((prev) => { const { [key]: _, ...rest } = prev; return rest; });
  };

  const handleAdd = async () => {
    setApiError('');
    const errors = validateForm(newName, newType, newConfig);
    if (Object.keys(errors).length > 0) { setFormErrors(errors); return; }
    try {
      const res = await fetch('/api/connections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), type: newType, config: newConfig }),
      });
      if (res.ok) {
        setShowAdd(false);
        resetForm();
        await loadConnections();
      } else {
        const data = await res.json().catch(() => ({}));
        setApiError(data?.msg || data?.error || `Lỗi ${res.status}: Không thể thêm kết nối`);
      }
    } catch {
      setApiError('Không thể kết nối tới server');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/connections/${id}`, { method: 'DELETE' });
      await loadConnections();
    } catch {}
  };

  const handleSync = async (id: string) => {
    try {
      await fetch(`/api/connections/${id}/sync`, { method: 'POST' });
      await loadConnections();
    } catch {}
  };

  const typeMeta = CONNECTION_TYPES[newType] || CONNECTION_TYPES.local;

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#020408]">
      <div className="shrink-0 p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Radio className="w-4 h-4 text-sky-400" />
          <h3 className="text-[11px] font-black uppercase tracking-widest text-white/90">External Connections</h3>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadConnections} className="p-2 text-white/20 hover:text-white">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/20 border border-sky-500/30 hover:bg-sky-500/30 text-sky-400 transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="text-[10px] font-bold uppercase tracking-wider">Add</span>
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden custom-scroll p-4 space-y-3">
        {loading ? (
          <div className="h-full flex items-center justify-center opacity-20">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : connections.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-4 px-6 text-center">
            <Radio className="w-12 h-12 text-white/10" />
            <p className="text-[11px] leading-relaxed max-w-xs text-white/30">
              No external connections configured. Click "Add" to connect a local folder, web URL, or cloud service.
            </p>
          </div>
        ) : (
          connections.map((conn) => {
            const meta = CONNECTION_TYPES[conn.type];
            return (
              <motion.div
                key={conn.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="group rounded-xl bg-white/[0.02] border border-white/[0.06] p-4 hover:bg-white/[0.04] transition-all"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={meta?.color || 'text-sky-400'}>
                      {meta?.icon || <FolderOpen className="w-4 h-4" />}
                    </div>
                    <div>
                      <h4 className="text-[13px] font-bold text-white/90">{conn.name}</h4>
                      <span className="text-[9px] text-white/30 tracking-wider uppercase">
                        {meta?.label || conn.type}
                      </span>
                    </div>
                  </div>
                  <StatusBadge status={conn.status} />
                </div>
                <ConfigDisplay type={conn.type} config={conn.config} />
                {conn.last_sync && (
                  <div className="flex items-center gap-1.5 text-[9px] text-white/20">
                    <Clock className="w-3 h-3" />
                    Last sync: {new Date(conn.last_sync * 1000).toLocaleString()}
                  </div>
                )}
                {conn.error && (
                  <div className="flex items-center gap-1.5 text-[9px] text-rose-400 mt-1">
                    <AlertTriangle className="w-3 h-3" />
                    {conn.error}
                  </div>
                )}
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/5">
                  <button
                    onClick={() => handleSync(conn.id)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 hover:bg-sky-500/20 text-white/40 hover:text-sky-400 transition-all"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span className="text-[9px] font-bold uppercase tracking-wider">Sync</span>
                  </button>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 hover:bg-rose-500/20 text-white/40 hover:text-rose-400 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span className="text-[9px] font-bold uppercase tracking-wider">Remove</span>
                  </button>
                </div>
              </motion.div>
            );
          })
        )}
      </div>

      {showAdd && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
        >
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0a0e1a] p-6 max-h-[90vh] overflow-y-auto custom-scroll">
            <h3 className="text-[14px] font-black uppercase tracking-widest text-white/90 mb-6">Add Connection</h3>

            <div className="space-y-4">
              {!['gdrive', 'onedrive', 'sharepoint'].includes(newType) && (
                <div>
                  <label className="text-[9px] font-bold uppercase tracking-wider text-white/40 block mb-1.5">Name</label>
                  <input
                    value={newName}
                    onChange={handleNameChange}
                    placeholder="e.g. My Documents"
                    className={`w-full px-3 py-2 rounded-lg bg-white/5 border text-white text-[12px] placeholder-white/20 focus:outline-none transition-all ${
                      formErrors.name ? 'border-rose-500/50 focus:border-rose-400' : 'border-white/10 focus:border-sky-500/50'
                    }`}
                  />
                  {formErrors.name && <p className="mt-1 text-[10px] text-rose-400">{formErrors.name}</p>}
                </div>
              )}

              <div>
                <label className="text-[9px] font-bold uppercase tracking-wider text-white/40 block mb-1.5">Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(CONNECTION_TYPES)
                    .filter(([key]) => ['local', 'web', 'gdrive', 'onedrive', 'sharepoint'].includes(key))
                    .map(([key, meta]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => handleTypeChange(key)}
                        className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-[11px] font-bold transition-all ${
                          newType === key
                            ? 'bg-sky-500/20 border-sky-500/40 text-sky-400'
                            : 'bg-white/5 border-white/10 text-white/40 hover:bg-white/10'
                        }`}
                      >
                        <span className={meta.color}>{meta.icon}</span>
                        {meta.label}
                      </button>
                    ))}
                </div>
              </div>

              <div className="space-y-3">
                {getFields(newType, newConfig.auth_type || 'oauth').map((f) => (
                  <div key={f.key}>
                    <label className="text-[9px] font-bold uppercase tracking-wider text-white/40 block mb-1.5">
                      {f.label}
                    </label>
                    <input
                      type={f.secret ? 'password' : 'text'}
                      value={newConfig[f.key] || ''}
                      onChange={(e) => updateConfig(f.key, e.target.value)}
                      placeholder={f.placeholder}
                      className={`w-full px-3 py-2 rounded-lg bg-white/5 border text-white text-[12px] placeholder-white/20 focus:outline-none transition-all ${
                        formErrors[f.key] ? 'border-rose-500/50 focus:border-rose-400' : 'border-white/10 focus:border-sky-500/50'
                      }`}
                    />
                    {formErrors[f.key] && <p className="mt-1 text-[10px] text-rose-400">{formErrors[f.key]}</p>}
                  </div>
                ))}
              </div>

              {['gdrive', 'onedrive', 'sharepoint'].includes(newType) && (
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
                  <p className="text-[11px] text-white/80 leading-relaxed font-bold">
                    🚀 Kết nối Đám mây tự động (Rclone):
                  </p>
                  <p className="text-[10px] text-white/40 leading-relaxed">
                    Hệ thống sẽ chạy Rclone ngầm. Khi bạn nhấn nút kết nối ở dưới, một tab trình duyệt mới sẽ tự động được mở ra để xác thực tài khoản GDrive/Microsoft của bạn chỉ với 1 click.
                  </p>

                  {/* SharePoint: bắt buộc nhập Site URL */}
                  {newType === 'sharepoint' && (
                    <div>
                      <label className="block text-[10px] text-white/50 mb-1 font-semibold">
                        🔗 SharePoint Site URL <span className="text-rose-400">*</span>
                      </label>
                      <input
                        type="text"
                        value={newConfig.site_url || ''}
                        onChange={(e) => updateConfig('site_url', e.target.value)}
                        placeholder="https://yourorg.sharepoint.com/sites/Knowledge"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-[12px] placeholder-white/20 focus:outline-none focus:border-orange-500/50 transition-all"
                      />
                      <p className="mt-1 text-[10px] text-white/30">
                        Nhập URL site SharePoint bạn muốn kết nối. Ví dụ: https://hueic.sharepoint.com/sites/Knowledge
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {apiError && (
              <div className="flex items-start gap-2 mt-4 px-3 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <p className="text-[11px] text-rose-300 leading-relaxed">{apiError}</p>
              </div>
            )}

            <div className="flex items-center gap-3 mt-6">
              {['gdrive', 'onedrive', 'sharepoint'].includes(newType) ? (
                <button
                  onClick={startRcloneAuth}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-sky-500/20 border border-sky-500/30 text-sky-400 text-[11px] font-bold uppercase tracking-wider hover:bg-sky-500/30 transition-all"
                >
                  Kết nối với {CONNECTION_TYPES[newType]?.label}
                </button>
              ) : (
                <button
                  onClick={handleAdd}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-sky-500/20 border border-sky-500/30 text-sky-400 text-[11px] font-bold uppercase tracking-wider hover:bg-sky-500/30 transition-all"
                >
                  Add Connection
                </button>
              )}
              <button
                onClick={() => { setShowAdd(false); resetForm(); }}
                className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/40 text-[11px] font-bold uppercase tracking-wider hover:bg-white/10 transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {dcFlow && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 z-[60] bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-[#0a0e1a] p-6 text-center">
            {dcFlow.status === 'completed' ? (
              <>
                <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
                <h3 className="text-[14px] font-black uppercase tracking-widest text-white/90 mb-2">Đăng nhập thành công!</h3>
                <p className="text-[11px] text-white/40 mb-6">Access token và refresh token đã được lưu.</p>
                <button onClick={() => setDcFlow(null)} className="px-6 py-2.5 rounded-xl bg-sky-500/20 border border-sky-500/30 text-sky-400 text-[11px] font-bold uppercase tracking-wider hover:bg-sky-500/30 transition-all">OK</button>
              </>
            ) : dcFlow.status === 'error' ? (
              <>
                <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
                <h3 className="text-[14px] font-black uppercase tracking-widest text-white/90 mb-2">Đăng nhập thất bại</h3>
                <p className="text-[11px] text-white/40 mb-6">{apiError || 'Vui lòng thử lại.'}</p>
                <button onClick={() => setDcFlow(null)} className="px-6 py-2.5 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-400 text-[11px] font-bold uppercase tracking-wider hover:bg-rose-500/30 transition-all">Đóng</button>
              </>
            ) : (
              <>
                <Loader2 className="w-10 h-10 text-sky-400 mx-auto mb-4 animate-spin" />
                <h3 className="text-[14px] font-black uppercase tracking-widest text-white/90 mb-1">{newType === 'onedrive' ? 'Xác thực OneDrive Cá nhân' : newType === 'sharepoint' ? 'Xác thực SharePoint' : 'Xác thực Google Drive'}</h3>
                <p className="text-[10px] text-white/40 mb-4">Quét mã QR hoặc mở link để đăng nhập:</p>
                <div className="flex justify-center mb-3">
                  <img src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(dcFlow.uri)}`} alt="QR Code" className="rounded-xl bg-white p-2" />
                </div>
                <div className="bg-white/5 rounded-xl p-3 mb-3">
                  <p className="text-[9px] text-white/30 uppercase tracking-wider mb-1">Hoặc mở link</p>
                  <p className="text-[11px] font-bold text-sky-400 break-all">{dcFlow.uri}</p>
                </div>
                <div className="bg-white/5 rounded-xl p-3 mb-4">
                  <p className="text-[9px] text-white/30 uppercase tracking-wider mb-1">Mã xác thực</p>
                  <p className="text-[28px] font-black tracking-[0.3em] text-amber-400">{dcFlow.userCode}</p>
                </div>
                <p className="text-[9px] text-white/20 mb-4">Nhập mã này trên màn hình đăng nhập, sau đó JKAI sẽ tự động lấy token.</p>
                <button onClick={() => { setDcFlow(null); setApiError(''); }} className="px-6 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/40 text-[11px] font-bold uppercase tracking-wider hover:bg-white/10 transition-all">Huỷ</button>
              </>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
});
