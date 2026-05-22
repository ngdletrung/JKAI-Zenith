import React, { useState, useEffect } from 'react';
import { 
  Folder, File, ChevronRight, ChevronDown, Save, Trash2, 
  RefreshCcw, FileText, Code, Settings, Plus, X, Lock
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  extension?: string;
}

export const SovereignFileLab: React.FC = () => {
  const [tree, setTree] = useState<FileNode | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['.']));

  const fetchTree = async () => {
    try {
      const res = await fetch('/api/system/explorer');
      const data = await res.json();
      setTree(data);
    } catch (err) {
      console.error("Failed to fetch file tree", err);
    }
  };

  useEffect(() => {
    fetchTree();
  }, []);

  const toggleNode = (path: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedNodes(newExpanded);
  };

  const openFile = async (path: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/system/read_file?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      setSelectedFile(path);
      setFileContent(data.content || '');
    } catch (err) {
      console.error("Failed to read file", err);
    } finally {
      setIsLoading(false);
    }
  };

  const [authCode, setAuthCode] = useState('');
  const [showAuth, setShowAuth] = useState(false);
  const [authAction, setAuthAction] = useState<{ type: 'save' | 'delete', path?: string } | null>(null);

  const handleAuthSubmit = async () => {
    if (!authAction) return;
    
    if (authAction.type === 'save') {
      await executeSave(authCode);
    } else {
      await executeDelete(authAction.path!, authCode);
    }
    setAuthCode('');
    setShowAuth(false);
    setAuthAction(null);
  };

  const saveFile = () => {
    if (!selectedFile) return;
    executeSave('');
  };

  const executeSave = async (code: string) => {
    try {
      const res = await fetch('/api/system/save_file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content: fileContent, code })
      });
      if (res.ok) {
        // @ts-ignore
        window.toast?.success("Tệp tin đã được niêm phong chủ quyền!");
      } else {
        // @ts-ignore
        window.toast?.error("Mật mã không chính xác. Quyền truy cập bị từ chối!");
      }
    } catch (err) {
      console.error("Failed to save file", err);
    }
  };

  const deleteItem = (path: string) => {
    if (window.confirm("Thanh lọc file này khỏi hệ thống?")) {
      executeDelete(path, '');
    }
  };

  const executeDelete = async (path: string, code: string) => {
    try {
      const res = await fetch('/api/system/delete_file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, code })
      });
      if (res.ok) {
        fetchTree();
        if (selectedFile === path) setSelectedFile(null);
        // @ts-ignore
        window.toast?.success("Dữ liệu đã được thanh lọc khỏi hệ thống!");
      } else {
        // @ts-ignore
        window.toast?.error("Mật mã không chính xác!");
      }
    } catch (err) {
      console.error("Failed to delete item", err);
    }
  };

  const renderTree = (node: FileNode, level = 0) => {
    const isExpanded = expandedNodes.has(node.path);
    const isSelected = selectedFile === node.path;

    return (
      <div key={node.path}>
        <div 
          className={`flex items-center py-1 px-2 cursor-pointer hover:bg-white/10 rounded group transition-colors ${isSelected ? 'bg-blue-500/20 border-l-2 border-blue-500' : ''}`}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
          onClick={() => node.type === 'directory' ? toggleNode(node.path) : openFile(node.path)}
        >
          {node.type === 'directory' ? (
            isExpanded ? <ChevronDown size={14} className="mr-1 text-gray-400" /> : <ChevronRight size={14} className="mr-1 text-gray-400" />
          ) : (
            <div className="w-[18px]" />
          )}
          
          {node.type === 'directory' ? (
            <Folder size={16} className={`mr-2 ${isExpanded ? 'text-blue-400' : 'text-gray-400'}`} />
          ) : (
            <File size={16} className={`mr-2 ${isSelected ? 'text-blue-400' : 'text-gray-400'}`} />
          )}
          
          <span className={`text-sm truncate ${isSelected ? 'text-blue-100 font-medium' : 'text-gray-300'}`}>
            {node.name}
          </span>

          <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
             <button onClick={(e) => { e.stopPropagation(); deleteItem(node.path); }} className="p-1 hover:text-red-400">
               <Trash2 size={12} />
             </button>
          </div>
        </div>
        
        {node.type === 'directory' && isExpanded && node.children && (
          <div className="overflow-hidden">
            {node.children.map(child => renderTree(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-full w-full bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden text-white">
      {/* Sidebar: File Tree */}
      <div className="w-72 border-r border-white/10 flex flex-col bg-black/20">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-widest text-blue-400 flex items-center gap-2">
            <Code size={18} /> SOVEREIGN LAB
          </h2>
          <button onClick={fetchTree} className="p-1.5 hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-white">
            <RefreshCcw size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-white/10">
          {tree ? renderTree(tree) : (
            <div className="p-4 text-center text-gray-500 text-xs animate-pulse">Initializing Neural Tree...</div>
          )}
        </div>
      </div>

      {/* Main Content: Editor */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        {selectedFile ? (
          <>
            <div className="h-12 border-b border-white/10 flex items-center px-4 bg-black/20 justify-between">
              <div className="flex items-center gap-2 truncate">
                <FileText size={16} className="text-blue-400" />
                <span className="text-xs font-mono text-gray-400 truncate">{selectedFile}</span>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={saveFile}
                  className="flex items-center gap-2 px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-bold transition-all shadow-lg shadow-blue-900/20"
                >
                  <Save size={14} /> SAVE
                </button>
              </div>
            </div>
            <div className="flex-1 relative overflow-hidden">
              {isLoading ? (
                <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm z-10">
                  <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : null}
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                className="w-full h-full p-6 bg-transparent font-mono text-sm resize-none focus:outline-none text-gray-200 leading-relaxed scrollbar-thin scrollbar-thumb-white/10"
                spellCheck={false}
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 opacity-40">
             <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mb-6 border border-white/10">
                <Code size={40} className="text-blue-400" />
             </div>
             <h3 className="text-xl font-bold mb-2">Neural Workspace Idle</h3>
             <p className="text-sm max-w-xs">Select a file from the Sovereign Tree to begin high-fidelity neural editing.</p>
          </div>
        )}
      </div>
    </div>
  );
};
