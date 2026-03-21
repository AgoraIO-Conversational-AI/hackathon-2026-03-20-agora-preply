import { marked } from "marked";
import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { CopyButtonOverlay } from "@/components/ui/CopyButton";

/**
 * Block-level memoization for streaming performance.
 * Splits markdown into blocks via marked.lexer() — during streaming,
 * only the last (incomplete) block re-renders. Completed blocks are memoized.
 * Pattern from PostHog's MarkdownMessage.
 */
function parseMarkdownIntoBlocks(markdown: string): string[] {
  const withLineBreaks = markdown.replace(/(?<!\n)\n(?!\n)/g, "  \n");
  const tokens = marked.lexer(withLineBreaks);
  return tokens.map((token) => token.raw);
}

function extractCodeText(children: React.ReactNode): string {
  if (!children) return "";
  const child = Array.isArray(children) ? children[0] : children;
  if (typeof child === "object" && child !== null && "props" in child) {
    const elementProps = (child as React.ReactElement).props as Record<string, unknown>;
    if (typeof elementProps.children === "string") return elementProps.children;
    if (Array.isArray(elementProps.children)) return (elementProps.children as unknown[]).filter((c) => typeof c === "string").join("");
  }
  return typeof child === "string" ? child : "";
}

const markdownComponents = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  a: ({ href, children }: any) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pre: ({ children }: any) => {
    const code = extractCodeText(children);
    return (
      <div className="group/pre relative">
        <pre>{children}</pre>
        {code && <CopyButtonOverlay text={code} />}
      </div>
    );
  },
};

const MarkdownBlock = memo(function MarkdownBlock({
  content,
}: {
  content: string;
}) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[
        [rehypeHighlight, { detect: true, ignoreMissing: true }],
      ]}
      disallowedElements={["script", "iframe", "object", "embed"]}
      components={markdownComponents}
    >
      {content}
    </ReactMarkdown>
  );
});

export const ChatMarkdown = memo(function ChatMarkdown({
  content,
  id,
}: {
  content: string;
  id: string;
}) {
  const blocks = useMemo(() => parseMarkdownIntoBlocks(content), [content]);
  return (
    <div className="markdown-chat">
      {blocks.map((block, i) => (
        <MarkdownBlock key={`${id}-block-${i}`} content={block} />
      ))}
    </div>
  );
});
