import React, { memo, useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Brain, Sparkles, Target, Activity, Zap, FileCode2, Terminal, Check, Copy, ExternalLink, ChevronRight } from 'lucide-react';
import mermaid from 'mermaid';
import toast from 'react-hot-toast';
import { useZenithStore } from '../../store/zenithStore';
import { ZenithService } from '../../services/ZenithService';

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

export const CodeBlock = memo(({ children }: { children: any }) => {
  const [copied, setCopied] = useState(false);
  const text = String(children).replace(/\n$/, '');
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Đã sao chép chữ ký hệ thống', { id: 'copy-code' });
  };
  return (
    <div className="relative group/code my-3">
      <pre className="p-4 rounded-xl bg-black/40 border border-white/5 font-mono text-[11px] overflow-x-auto custom-scroll">
        {children}
      </pre>
      <button onClick={handleCopy} className="absolute top-2 right-2 p-1.5 rounded-lg bg-white/5 border border-white/10 opacity-0 group-hover/code:opacity-100 transition-all hover:bg-white/10">
        {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-white/40" />}
      </button>
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

// ─── MAIN RENDERER ───────────────────────────────────────────────────────────

export const MarkdownRenderer = memo(({ content }: { content: string }) => {
  const setInspectedFile = useZenithStore(s => s.setInspectedFile);
  
  return (
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

          const isFilePath = isInline && (contentStr.includes('/') || contentStr.includes('\\')) && (contentStr.includes('.') || contentStr.length > 5);
          if (!isInline) return <CodeBlock>{children}</CodeBlock>;

          return (
            <code className="px-1.5 py-0.5 rounded bg-white/10 text-cyan-300 font-mono text-[11px] group/file cursor-pointer relative" onClick={() => {
              if (isFilePath) {
                ZenithService.readFile(contentStr.trim()).then(r => {
                  if (r.ok) setInspectedFile({ path: contentStr.trim(), content: r.content });
                });
              }
            }}>
              {children}
              {isFilePath && <ExternalLink className="w-2.5 h-2.5 inline ml-1 opacity-0 group-hover/file:opacity-100 transition-opacity" />}
            </code>
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
              if (React.isValidElement(node) && node.props && 'children' in node.props) {
                return React.cloneElement(node, {
                  children: cleanAlertTag(node.props.children)
                } as any);
              }
              return node;
            };
            const cleanContent = React.Children.map(children, cleanAlertTag);
            return <AlertBlock type={type}>{cleanContent}</AlertBlock>;
          }
          return <blockquote className="border-l-4 border-white/10 pl-4 my-4 italic text-white/40">{children}</blockquote>;
        },
        table: ({ children }) => <div className="overflow-x-auto my-6 border border-white/10 rounded-2xl shadow-2xl"><table className="w-full text-left border-collapse">{children}</table></div>,
        th: ({ children }) => <th className="px-5 py-3 border-b border-white/10 bg-white/[0.03] font-black text-cyan-400/80 uppercase tracking-widest text-[10px]">{children}</th>,
        td: ({ children }) => <td className="px-5 py-3 border-b border-white/[0.01] text-white/60 text-sm">{children}</td>,
        hr: () => <hr className="my-8 border-white/5" />
      }}
    >
      {content}
    </ReactMarkdown>
  );
});
