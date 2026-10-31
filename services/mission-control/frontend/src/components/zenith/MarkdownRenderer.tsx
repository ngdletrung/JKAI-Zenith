import React, { memo, useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Brain, Sparkles, Target, Activity, Zap, FileCode2, Terminal, Check, Copy, 
  ExternalLink, ChevronRight, Image as ImageIcon, Eye, Download, X, ZoomIn, ZoomOut, 
  RotateCw, FileSpreadsheet, FileText, Maximize2, Camera, ScrollText, Folder 
} from 'lucide-react';
import mermaid from 'mermaid';
import toast from 'react-hot-toast';
import { useZenithStore } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';
import { FileChangesCard } from './FileChangesCard';

// ─── SUB-COMPONENTS ──────────────────────────────────────────────────────────

export const AlertBlock = memo(({ type, children }: { type: string, children: any }) => {
  const config = {
    NOTE: { icon: Brain, color: 'text-sky-400', bg: 'bg-sky-400/10', border: 'border-sky-400/20' },
    TIP: { icon: Sparkles, color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20' },
    IMPORTANT: { icon: Target, color: 'text-indigo-400', bg: 'bg-indigo-400/10', border: 'border-indigo-400/20' },
    WARNING: { icon: Activity, color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20' },
    CAUTION: { icon: Zap, color: 'text-rose-400', bg: 'bg-rose-400/10', border: 'border-rose-400/20' },
  }[type] || { icon: Brain, color: 'text-white/40', bg: 'bg-white/5', border: 'border-white/10' };

  return (
    <div className={`my-4 p-4 rounded-xl border-l-4 ${config.bg} ${config.border} flex gap-4 transition-all hover:scale-[1.01]`}>
      <div className={`shrink-0 ${config.color}`}><config.icon className="w-5 h-5" /></div>
      <div className="flex-1 text-[13px] leading-relaxed text-white/70">{children}</div>
    </div>
  );
});

export const CodeBlock = memo(({ children, lang }: { children: any, lang?: string }) => {
  const [copied, setCopied] = useState(false);
  const text = String(children).replace(/\n$/, '');
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Đã sao chép mã nguồn', { id: 'copy-code' });
  };
  return (
    <div className="relative group/code my-3 rounded-xl overflow-hidden border border-white/10 bg-black/60 shadow-xl">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-white/[0.04] border-b border-white/5 text-[10px] font-mono text-white/40">
        <span className="uppercase tracking-widest font-bold text-sky-400/90">{lang || 'CODE'}</span>
        <button onClick={handleCopy} className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/60 hover:text-white transition-all">
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400 text-[9px] font-bold uppercase">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span className="text-[9px] font-bold uppercase">Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 font-mono text-[11px] leading-relaxed overflow-x-auto custom-scroll text-slate-200">
        {children}
      </pre>
    </div>
  );
});

export const MermaidBlock = memo(({ chart }: { chart: string }) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    if (chartRef.current && active) {
      chartRef.current.removeAttribute('data-processed');
      mermaid.run({
        nodes: [chartRef.current],
        suppressErrors: true
      });
    }
    return () => { active = false; };
  }, [chart]);

  return (
    <div className="my-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] overflow-hidden group/mermaid relative">
      <div className="absolute top-2 right-2 p-1.5 rounded-lg bg-white/5 opacity-0 group-hover/mermaid:opacity-100 transition-all cursor-pointer hover:bg-sky-500 hover:text-white" onClick={() => { navigator.clipboard.writeText(chart); toast.success('Mã nguồn đồ họa đã được sao chép', { id: 'mermaid-copy' }); }}>
        <Copy className="w-3.5 h-3.5" />
      </div>
      <div ref={chartRef} className="mermaid flex justify-center">
        {chart}
      </div>
    </div>
  );
});

// ─── LIGHTBOX MODAL ──────────────────────────────────────────────────────────

const ImageLightboxModal: React.FC<{ url: string | null; onClose: () => void }> = ({ url, onClose }) => {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [fitWidth, setFitWidth] = useState(true);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!url) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-fadeIn">
      {/* Action bar */}
      <div className="absolute top-4 right-4 flex items-center gap-2 z-20 bg-black/70 backdrop-blur-md p-1.5 rounded-2xl border border-white/10 shadow-2xl">
        <button
          onClick={() => setFitWidth(!fitWidth)}
          className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border ${
            fitWidth 
              ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-lg shadow-cyan-500/10' 
              : 'bg-white/10 text-white/70 border-white/10 hover:bg-white/20 hover:text-white'
          }`}
          title="Chế độ đọc cuộn toàn trang (Fit Width)"
        >
          <ScrollText className="w-3.5 h-3.5" />
          <span>{fitWidth ? 'Đang bật Fit Width' : 'Bật Fit Width'}</span>
        </button>

        <div className="w-[1px] h-4 bg-white/10 mx-1" />

        <button 
          onClick={() => setScale(s => Math.min(s + 0.25, 4))}
          className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-all"
          title="Phóng to"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button 
          onClick={() => setScale(s => Math.max(s - 0.25, 0.4))}
          className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-all"
          title="Thu nhỏ"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button 
          onClick={() => setRotation(r => (r + 90) % 360)}
          className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-all"
          title="Xoay ảnh 90°"
        >
          <RotateCw className="w-4 h-4" />
        </button>
        <a 
          href={url} 
          download 
          target="_blank" 
          rel="noreferrer"
          className="p-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition-all flex items-center gap-1"
          title="Tải ảnh về máy"
        >
          <Download className="w-4 h-4" />
        </a>
        <button 
          onClick={onClose}
          className="p-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition-all ml-1"
          title="Đóng (ESC)"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Image Canvas Container */}
      <div className={`w-full flex-1 min-h-0 flex justify-center p-2 overflow-auto custom-scroll ${fitWidth ? 'items-start' : 'items-center'}`}>
        <img 
          src={url} 
          alt="Visual Evidence Full View"
          style={{ 
            transform: fitWidth ? `scale(${scale})` : `scale(${scale}) rotate(${rotation}deg)`, 
            transition: 'transform 0.15s ease-out' 
          }}
          className={`rounded-xl shadow-2xl transition-all ${
            fitWidth 
              ? 'w-full max-w-5xl h-auto object-contain my-auto' 
              : 'max-h-[85vh] max-w-[85vw] object-contain'
          }`}
        />
      </div>

      {/* Bottom hint bar */}
      <div className="shrink-0 pt-2 text-[11px] font-mono text-white/40 flex items-center gap-4">
        <span>Nhấn ESC để đóng</span>
        <span>•</span>
        <span>{fitWidth ? 'Chế độ Cuộn đọc toàn bộ trang (Fit Width)' : 'Chế độ Toàn cảnh (Fit Screen)'}</span>
      </div>
    </div>
  );
};

// ─── MAIN RENDERER ───────────────────────────────────────────────────────────

const KNOWN_FILE_EXTS = new Set([
  'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'ico',
  'py', 'ts', 'tsx', 'js', 'jsx', 'json', 'yaml', 'yml', 'toml', 'sh', 'bat', 'ps1',
  'md', 'txt', 'log', 'csv', 'xlsx', 'xls', 'docx', 'doc', 'pdf'
]);

export const MarkdownRenderer = memo(({ content }: { content: string }) => {
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  
  let formattedContent = content
    .replace(/<think>\n?/g, '```thought\n')
    .replace(/<\/think>\n?/g, '\n```\n');

  // Chuẩn hóa BROWSER_OBSERVATION / STORAGE thành liên kết nội bộ duy nhất
  // Xử lý sạch mọi biến thể có/không có ngoặc, emoji, hoặc đã có link
  formattedContent = formattedContent
    .replace(/\[\s*📁?\s*(?:Thư Mục Lưu Trữ:\s*)?BROWSER_OBSERVATION\s*\](?:\(#browser-observation\))?/gi, '[📁 BROWSER_OBSERVATION](#browser-observation)')
    .replace(/`\[?\s*📁?\s*BROWSER_OBSERVATION\s*\]?`/gi, '[📁 BROWSER_OBSERVATION](#browser-observation)')
    .replace(/\[\s*📁?\s*OBSERVATION\s*\](?:\(#browser-observation\))?/gi, '[📁 OBSERVATION](#browser-observation)')
    .replace(/`\[?\s*📁?\s*OBSERVATION\s*\]?`/gi, '[📁 OBSERVATION](#browser-observation)')
    .replace(/\[\s*📁?\s*STORAGE\s*\](?:\(#open-storage\))?/gi, '[📁 STORAGE](#open-storage)')
    .replace(/`\[?\s*📁?\s*STORAGE\s*\]?`/gi, '[📁 STORAGE](#open-storage)');

  // Auto-embed eye screenshot if mentioned in the message text or code but not yet embedded as markdown image
  const eyeMatch = formattedContent.match(/(eye_\d+\.png)/i);
  if (eyeMatch && !formattedContent.includes('![') && !formattedContent.includes(eyeMatch[1] + ')')) {
    formattedContent += `\n\n![📸 Ảnh chụp toàn trang web](/${eyeMatch[1]})\n`;
  }
  
  return (
    <>
      {lightboxUrl && <ImageLightboxModal url={lightboxUrl} onClose={() => setLightboxUrl(null)} />}
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
          code: ({ node, className, children, ...props }) => {
            const contentStr = String(children);
            const lang = className?.replace('language-', '');
            const isInline = !className?.includes('language-');

            if (lang === 'mermaid') {
              return <MermaidBlock chart={contentStr} />;
            }
            if (lang === 'thought') {
              return (
                <div className="my-3 p-4 rounded-xl bg-indigo-900/10 border border-indigo-500/20 text-indigo-200/80 italic text-[12px] leading-relaxed whitespace-pre-wrap shadow-inner">
                  <Brain className="w-4 h-4 inline-block mr-2 mb-1 text-indigo-400 opacity-80" />
                  <span className="font-semibold text-indigo-300 mr-2">Tư duy Nơ-ron:</span>
                  {contentStr}
                </div>
              );
            }
            if (lang === 'files-changed' || lang === 'changes' || lang === 'files') {
              const lines = contentStr.trim().split('\n').map(l => l.trim()).filter(Boolean);
              return <FileChangesCard files={lines} />;
            }

            if (!isInline) return <CodeBlock lang={lang}>{children}</CodeBlock>;

            // [PENTAD-FILE-GUARD]: Nhận diện tệp tin thông minh tuân thủ OpenCode Guardrail 2
            const trimmed = contentStr.trim();
            const upper = trimmed.toUpperCase();
            if (upper.includes('BROWSER_OBSERVATION') || upper.includes('OBSERVATION') || upper === 'STORAGE' || upper === 'WORKSPACE') {
              const label = trimmed.replace(/^[`\[]+|[`\]]+$/g, '').trim();
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    useZenithStore.getState().setTab('explorer');
                    toast.success('Đang mở Thư mục Lưu trữ trong Explorer...', { id: 'OPEN_STORAGE' });
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1 my-0.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 font-mono text-[11px] font-bold border border-amber-500/30 transition-all cursor-pointer shadow-sm group align-middle active:scale-95"
                  title="Nhấp để mở Thư mục Lưu trữ trong Explorer"
                >
                  <Folder className="w-3.5 h-3.5 text-amber-400 group-hover:scale-110 transition-transform shrink-0" />
                  <span>[{label}]</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-0.5 opacity-60 group-hover:opacity-100 shrink-0" />
                </button>
              );
            }

            const fileExtMatch = trimmed.match(/\.([a-zA-Z0-9]{1,8})$/);
            const ext = fileExtMatch ? fileExtMatch[1].toLowerCase() : '';
            
            const isFilePath = isInline && (
              (KNOWN_FILE_EXTS.has(ext) && !trimmed.includes(' ') && trimmed.length >= 4) ||
              ((trimmed.includes('/') || trimmed.includes('\\')) && (KNOWN_FILE_EXTS.has(ext) || trimmed.includes('.')))
            );

            if (isFilePath) {
              const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes(ext);
              const isSheet = ['xlsx', 'xls', 'csv'].includes(ext);
              const isDoc = ['pdf', 'docx', 'doc'].includes(ext);
              const isCode = ['py', 'ts', 'tsx', 'js', 'json', 'yaml', 'yml', 'sh'].includes(ext);

              const pillColors = isImage 
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25'
                : isSheet 
                ? 'bg-amber-500/15 border-amber-500/30 text-amber-300 hover:bg-amber-500/25'
                : isDoc 
                ? 'bg-purple-500/15 border-purple-500/30 text-purple-300 hover:bg-purple-500/25'
                : isCode 
                ? 'bg-sky-500/15 border-sky-500/30 text-sky-300 hover:bg-sky-500/25'
                : 'bg-white/10 border-white/20 text-cyan-300 hover:bg-white/20';

              const Icon = isImage ? ImageIcon : isSheet ? FileSpreadsheet : isDoc ? FileText : FileCode2;

              const handlePillClick = () => {
                if (isImage) {
                  // Mở Lightbox trực tiếp cho ảnh
                  setLightboxUrl(`/api/system/raw_file?path=${encodeURIComponent(trimmed)}`);
                } else {
                  ZenithService.readFile(trimmed).then(r => {
                    if (r && r.ok) {
                      setInspectedFile({ path: trimmed, content: r.content, type: r.type, raw_url: r.raw_url });
                    } else {
                      toast.error(`Không thể đọc tệp ${trimmed}`);
                    }
                  });
                }
              };

              return (
                <span className="inline-flex items-center gap-1 my-0.5 align-middle">
                  <code 
                    onClick={handlePillClick}
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg border font-mono text-[11px] font-semibold cursor-pointer transition-all shadow-sm group/file ${pillColors}`}
                    title={isImage ? "Nhấp để xem ảnh trực tiếp" : "Nhấp để mở tệp trong Workspace"}
                  >
                    <Icon className="w-3 h-3 shrink-0" />
                    <span>{children}</span>
                    {isImage ? <Eye className="w-2.5 h-2.5 ml-0.5 opacity-60 group-hover/file:opacity-100" /> : <ExternalLink className="w-2.5 h-2.5 ml-0.5 opacity-60 group-hover/file:opacity-100" />}
                  </code>
                </span>
              );
            }

            return (
              <code className="px-1.5 py-0.5 rounded bg-white/10 text-cyan-300 font-mono text-[11px]">
                {children}
              </code>
            );
          },
          img: ({ src, alt }) => {
            if (!src) return null;
            let fullSrc = src;
            if (!src.startsWith('http') && !src.startsWith('/api/') && !src.startsWith('data:')) {
              fullSrc = `/api/system/raw_file?path=${encodeURIComponent(src)}`;
            }
            const fileName = src.split('/').pop() || src;
            const isScreenshot = src.includes('eye_') || src.includes('browse_') || (alt && alt.toLowerCase().includes('screenshot')) || (alt && alt.toLowerCase().includes('ảnh chụp'));

            return (
              <div className="my-3 rounded-2xl overflow-hidden border border-white/10 bg-[#070a12]/95 backdrop-blur-md group/img relative w-full max-w-2xl shadow-2xl">
                {/* Header bar for screenshot or image */}
                <div className="px-3.5 py-2 bg-white/[0.03] border-b border-white/5 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2 truncate text-cyan-400 font-bold">
                    <Camera className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="truncate">{alt || (isScreenshot ? '📸 Ảnh chụp toàn trang (Full-Page Web)' : fileName)}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button 
                      onClick={() => setLightboxUrl(fullSrc)}
                      className="px-2.5 py-1 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 text-[10px] font-bold uppercase transition-all flex items-center gap-1.5 shadow-sm"
                      title="Mở toàn màn hình & Cuộn đọc toàn trang"
                    >
                      <Maximize2 className="w-3 h-3" />
                      <span>Cuộn xem toàn trang</span>
                    </button>
                    <a
                      href={fullSrc}
                      download={fileName}
                      className="p-1 rounded-lg text-white/50 hover:text-emerald-400 hover:bg-white/5 transition-colors"
                      title="Tải ảnh gốc về máy"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>

                {/* Image Container with Scrollable Area for tall screenshots */}
                <div 
                  onClick={() => setLightboxUrl(fullSrc)}
                  className={`cursor-pointer relative group/canvas flex justify-center bg-black/40 ${isScreenshot ? 'max-h-[380px] overflow-y-auto custom-scroll p-2' : 'p-2'}`}
                  title="Nhấp để phóng to toàn màn hình"
                >
                  <img 
                    src={fullSrc} 
                    alt={alt || 'Image Visual Preview'} 
                    className="w-full h-auto rounded-xl object-contain object-top transition-transform duration-300 group-hover/canvas:opacity-95"
                    loading="lazy"
                  />
                  {/* Subtle hover overlay badge */}
                  <div className="absolute inset-x-0 bottom-0 py-3 bg-gradient-to-t from-black/90 to-transparent flex items-center justify-center opacity-0 group-hover/canvas:opacity-100 transition-opacity pointer-events-none">
                    <span className="text-[11px] font-bold text-cyan-300 bg-black/80 px-3.5 py-1 rounded-full border border-cyan-500/30 flex items-center gap-1.5 shadow-xl">
                      <Maximize2 className="w-3.5 h-3.5" />
                      Nhấp để xem cuộn toàn trang (Full-Resolution)
                    </span>
                  </div>
                </div>
              </div>
            );
          },
          blockquote: ({ children }) => {
            const getTextContent = (node: any): string => {
              if (!node) return '';
              if (typeof node === 'string' || typeof node === 'number') return String(node);
              if (Array.isArray(node)) return node.map(getTextContent).join(' ');
              if (node.props && node.props.children) return getTextContent(node.props.children);
              return '';
            };
            const text = React.Children.toArray(children).map(getTextContent).join(' ');

            const alertMatch = text.match(/\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i);
            if (alertMatch) {
              const type = alertMatch[1].toUpperCase();
              const cleanAlertTag = (node: any): any => {
                if (!node) return node;
                if (typeof node === 'string') {
                  return node.replace(/\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i, '').trim();
                }
                if (Array.isArray(node)) {
                  return node.map(cleanAlertTag);
                }
                if (React.isValidElement(node) && node.props && 'children' in (node.props as any)) {
                  return React.cloneElement(node, {
                    children: cleanAlertTag((node.props as any).children)
                  } as any);
                }
                return node;
              };
              const cleanContent = React.Children.map(children, cleanAlertTag);
              return <AlertBlock type={type}>{cleanContent}</AlertBlock>;
            }
            return <blockquote className="border-l-4 border-white/10 pl-4 my-4 italic text-white/40">{children}</blockquote>;
          },
          a: ({ href, children }) => {
            const childrenStr = String(children || '');
            const isObservationLink = href === '#browser-observation' || 
              href === '#open-storage' || 
              href === '#open-explorer' || 
              (href?.startsWith('#') && href.includes('observation')) || 
              childrenStr.includes('BROWSER_OBSERVATION') || 
              childrenStr.includes('OBSERVATION');

            if (isObservationLink) {
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    useZenithStore.getState().setTab('explorer');
                    toast.success('Đang mở Thư mục Lưu trữ trong Explorer...', { id: 'OPEN_STORAGE' });
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1 my-0.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 font-mono text-[11px] font-bold border border-amber-500/30 transition-all cursor-pointer shadow-sm group align-middle active:scale-95"
                  title="Nhấp để mở Thư mục Lưu trữ trong Explorer"
                >
                  <Folder className="w-3.5 h-3.5 text-amber-400 group-hover:scale-110 transition-transform shrink-0" />
                  <span>{children}</span>
                  <ExternalLink className="w-2.5 h-2.5 ml-0.5 opacity-60 group-hover:opacity-100 shrink-0" />
                </button>
              );
            }

            const isExternal = href?.startsWith('http://') || href?.startsWith('https://') || (href && !href.startsWith('/') && !href.startsWith('#') && href.includes('.'));
            const normalizedHref = isExternal && !href?.startsWith('http://') && !href?.startsWith('https://') ? `https://${href}` : (href || '#');
            const isDownload = href?.startsWith('/outputs/') || href?.startsWith('/exports/') || href?.startsWith('/api/system/raw_file') || href?.endsWith('.xlsx') || href?.endsWith('.docx') || href?.endsWith('.pdf');
            
            const handleExternalClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
              e.stopPropagation();
              if (isExternal && typeof window !== 'undefined') {
                // Thử mở qua window.open để đảm bảo tab mới ngay lập tức
                const win = window.open(normalizedHref, '_blank', 'noopener,noreferrer');
                if (win) {
                  // Đã mở thành công tab mới, chặn browser navigation mặc định
                  e.preventDefault();
                }
                // Nếu popup bị trình duyệt chặn, để mặc định target="_blank" tự kích hoạt mở tab mới
              }
            };

            return (
              <a 
                href={normalizedHref} 
                onClick={handleExternalClick}
                {...(isDownload ? { download: true } : {})}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1 my-0.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-semibold text-[12px] border border-emerald-500/20 transition-all cursor-pointer shadow-sm hover:shadow-emerald-500/10 active:scale-95"
              >
                {children}
                <ExternalLink className="w-3 h-3 ml-0.5 shrink-0" />
              </a>
            );
          },
          table: ({ children }) => <div className="overflow-x-auto my-6 border border-white/10 rounded-2xl shadow-2xl"><table className="min-w-full w-max text-left border-collapse">{children}</table></div>,
          th: ({ children }) => <th className="px-5 py-3 border-b border-white/10 bg-white/[0.03] font-black text-cyan-400/80 uppercase tracking-widest text-[10px]">{children}</th>,
          td: ({ children }) => <td className="px-5 py-3 border-b border-white/[0.01] text-white/60 text-sm">{children}</td>,
          hr: () => <hr className="my-8 border-white/5" />
        }}
      >
        {formattedContent}
      </ReactMarkdown>
    </>
  );
});
