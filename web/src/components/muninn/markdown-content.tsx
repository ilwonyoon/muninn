"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div className={cn("text-sm leading-relaxed text-foreground", className)}>
    <Markdown
      remarkPlugins={[remarkGfm]}
      children={content}
      components={{
        h1: ({ children }) => (
          <h1 className="mb-4 mt-2 text-xl font-bold tracking-tight text-foreground">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="mb-3 mt-8 text-base font-semibold text-foreground">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mb-2 mt-6 text-sm font-semibold text-foreground">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="mb-4 text-sm leading-[1.75] text-foreground/85">
            {children}
          </p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-foreground">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic text-muted">{children}</em>
        ),
        ul: ({ children }) => (
          <ul className="mb-4 ml-5 list-disc space-y-1.5 text-sm text-foreground/85">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-4 ml-5 list-decimal space-y-1.5 text-sm text-foreground/85">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-sm leading-[1.75]">{children}</li>
        ),
        code: ({ children, className: codeClassName }) => {
          const isBlock = codeClassName?.includes("language-");
          if (isBlock) {
            return (
              <code className="block rounded border border-border bg-card p-3 font-mono text-xs text-foreground">
                {children}
              </code>
            );
          }
          return (
            <code className="rounded bg-card-hover px-1.5 py-0.5 font-mono text-xs text-foreground">
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="mb-3 overflow-x-auto">{children}</pre>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-accent hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        table: ({ children }) => (
          <div className="mb-4 overflow-x-auto rounded border border-border">
            <table className="w-full border-collapse text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b border-border">{children}</thead>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => (
          <tr className="border-b border-border">{children}</tr>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left text-xs font-semibold text-foreground">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-sm text-foreground/80">{children}</td>
        ),
        hr: () => <hr className="my-6 border-border" />,
        blockquote: ({ children }) => (
          <blockquote className="mb-4 border-l-2 border-accent/50 pl-4 text-foreground/60 italic">
            {children}
          </blockquote>
        ),
      }}
    />
    </div>
  );
}
