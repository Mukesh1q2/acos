"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { ReactNode } from "react";

interface ChatMarkdownProps {
  content: string;
}

const components: Components = {
  h1: ({ children }: { children?: ReactNode }) => (
    <h1 className="text-xl font-bold text-emerald-400 mt-4 mb-2 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }: { children?: ReactNode }) => (
    <h2 className="text-lg font-bold text-emerald-400 mt-3 mb-1.5 first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }: { children?: ReactNode }) => (
    <h3 className="text-base font-bold text-emerald-400 mt-2.5 mb-1 first:mt-0">
      {children}
    </h3>
  ),
  h4: ({ children }: { children?: ReactNode }) => (
    <h4 className="text-sm font-bold text-foreground mt-2 mb-1 first:mt-0">
      {children}
    </h4>
  ),
  h5: ({ children }: { children?: ReactNode }) => (
    <h5 className="text-sm font-semibold text-foreground mt-2 mb-1 first:mt-0">
      {children}
    </h5>
  ),
  h6: ({ children }: { children?: ReactNode }) => (
    <h6 className="text-xs font-semibold text-foreground mt-2 mb-1 first:mt-0">
      {children}
    </h6>
  ),
  p: ({ children }: { children?: ReactNode }) => (
    <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
  ),
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className="font-bold text-foreground">{children}</strong>
  ),
  em: ({ children }: { children?: ReactNode }) => (
    <em className="italic">{children}</em>
  ),
  code: ({ children, className }: { children?: ReactNode; className?: string }) => {
    const isBlock = className?.startsWith("language-");

    if (isBlock) {
      const language = className?.replace("language-", "") || "";
      return (
        <div className="relative my-2.5 rounded-lg border border-slate-700/60 bg-slate-900/90 overflow-hidden">
          <div className="absolute top-2 right-2">
            <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/50">
              {language || "code"}
            </span>
          </div>
          <pre className="overflow-x-auto p-3 pt-2.5 text-xs leading-relaxed">
            <code className="font-mono text-slate-300">{children}</code>
          </pre>
        </div>
      );
    }

    return (
      <code className="bg-muted/30 rounded px-1.5 py-0.5 font-mono text-emerald-400 text-xs">
        {children}
      </code>
    );
  },
  pre: ({ children }: { children?: ReactNode }) => {
    return <>{children}</>;
  },
  a: ({ children, href }: { children?: ReactNode; href?: string }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-emerald-400 hover:underline underline-offset-2"
    >
      {children}
    </a>
  ),
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className="list-disc ml-4 mb-2 space-y-0.5 marker:text-emerald-500">
      {children}
    </ul>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className="list-decimal ml-4 mb-2 space-y-0.5 marker:text-emerald-500">
      {children}
    </ol>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className="text-sm leading-relaxed pl-1">{children}</li>
  ),
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote className="border-l-2 border-emerald-500/30 bg-emerald-500/5 pl-3 py-1.5 my-2 rounded-r-md">
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr className="my-3 border-0 h-px bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />
  ),
  table: ({ children }: { children?: ReactNode }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-slate-700/50">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: ReactNode }) => (
    <thead className="bg-slate-800/80 border-b border-slate-700/50">
      {children}
    </thead>
  ),
  tbody: ({ children }: { children?: ReactNode }) => (
    <tbody className="divide-y divide-slate-700/30">{children}</tbody>
  ),
  tr: ({ children }: { children?: ReactNode }) => (
    <tr className="hover:bg-slate-800/30 transition-colors">{children}</tr>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="px-3 py-1.5 text-left font-semibold text-foreground whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="px-3 py-1.5 text-slate-300 whitespace-nowrap">{children}</td>
  ),
};

export function ChatMarkdown({ content }: ChatMarkdownProps) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
}
