"use client";

import React, { useState } from "react";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import oneDark from "react-syntax-highlighter/dist/cjs/styles/prism/one-dark";

type CodeBlockProps = {
  code: string;
  language?: string;
};

const LANGUAGE_ALIASES: Record<string, string> = {
  js: "javascript",
  jsx: "jsx",
  py: "python",
  sh: "bash",
  shell: "bash",
  ts: "typescript",
  tsx: "tsx",
};

export function copyStatusLabel(copied: boolean): string {
  return copied ? "Copied!" : "Copy code";
}

function normalizeLanguage(language?: string): string {
  if (!language) {
    return "text";
  }
  const normalized = language.trim().toLowerCase();
  return LANGUAGE_ALIASES[normalized] ?? normalized;
}

function languageLabel(language: string): string {
  if (language === "text") {
    return "TEXT";
  }
  if (language === "typescript") {
    return "TS";
  }
  if (language === "javascript") {
    return "JS";
  }
  return language.toUpperCase();
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const normalizedLanguage = normalizeLanguage(language);

  async function copyCode() {
    if (!navigator.clipboard) {
      return;
    }
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <figure className="code-block">
      <figcaption className="code-block-header">
        <span>{languageLabel(normalizedLanguage)}</span>
        <button
          className="code-copy-button"
          type="button"
          aria-live="polite"
          onClick={() => {
            void copyCode();
          }}
        >
          {copyStatusLabel(copied)}
        </button>
      </figcaption>
      <SyntaxHighlighter
        className="code-block-pre"
        PreTag="pre"
        CodeTag="code"
        language={normalizedLanguage === "text" ? undefined : normalizedLanguage}
        style={oneDark}
        customStyle={{ margin: 0, background: "transparent" }}
        codeTagProps={{ className: "code-block-code" }}
        wrapLongLines={false}
      >
        {code}
      </SyntaxHighlighter>
    </figure>
  );
}
