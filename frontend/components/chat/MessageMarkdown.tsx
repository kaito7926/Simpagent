"use client";

import React from "react";
import Markdown, { type Components, type UrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";

import { CodeBlock } from "./CodeBlock";

type MessageMarkdownProps = {
  content: string;
};

const SCHEME_PATTERN = /^[a-zA-Z][a-zA-Z\d+.-]*:/;
const HTML_TAG_PATTERN = /<\/?[A-Za-z][^>\n]*>/g;
const ALLOWED_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

function textFromChildren(children: React.ReactNode): string {
  if (typeof children === "string" || typeof children === "number") {
    return String(children);
  }
  if (Array.isArray(children)) {
    return children.map((child) => textFromChildren(child)).join("");
  }
  return "";
}

export function safeMarkdownHref(href: string | null | undefined): string | undefined {
  if (!href) {
    return undefined;
  }

  const trimmed = href.trim();
  if (trimmed !== href || !SCHEME_PATTERN.test(trimmed)) {
    return undefined;
  }

  try {
    const parsed = new URL(trimmed);
    return ALLOWED_LINK_PROTOCOLS.has(parsed.protocol) ? trimmed : undefined;
  } catch {
    return undefined;
  }
}

const markdownUrlTransform: UrlTransform = (url) => safeMarkdownHref(url);

function escapeRawHtmlTags(content: string): string {
  return content.replace(HTML_TAG_PATTERN, (tag) =>
    tag.replace(/[<>]/g, (match) => `\\${match}`),
  );
}

const markdownComponents: Components = {
  a({ children, href, ...props }) {
    const safeHref = safeMarkdownHref(href);
    if (!safeHref) {
      return <span className="markdown-link-inert">{children}</span>;
    }
    return (
      <a {...props} href={safeHref} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  },
  code({ children, className, ...props }) {
    const code = textFromChildren(children);
    const language = /language-([\w-]+)/.exec(className ?? "")?.[1];
    const isBlock = Boolean(language) || code.endsWith("\n");
    if (isBlock) {
      return <CodeBlock code={code.replace(/\n$/, "")} language={language} />;
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  pre({ children }) {
    return <>{children}</>;
  },
};

export function MessageMarkdown({ content }: MessageMarkdownProps) {
  const escapedContent = escapeRawHtmlTags(content);

  return (
    <div className="markdown-content">
      <Markdown
        components={markdownComponents}
        remarkPlugins={[remarkGfm]}
        urlTransform={markdownUrlTransform}
      >
        {escapedContent}
      </Markdown>
    </div>
  );
}
