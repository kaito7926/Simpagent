import React from "react";

import type { ConversationDetail } from "@/lib/chat-types";

import { ChatComposer } from "./ChatComposer";
import { MessageList } from "./MessageList";

type ChatThreadProps = {
  conversation: ConversationDetail | null;
  draft: string;
  loading: boolean;
  pending: boolean;
  submitting: boolean;
  retryingClientMessageId: string | null;
  toolMode?: "auto" | "google_search" | "python";
  onToolModeChange?: (mode: "auto" | "google_search" | "python") => void;
  searchEnabled?: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
  onRetry: (clientMessageId: string) => void;
};

export function ChatThread({
  conversation,
  draft,
  loading,
  pending,
  submitting,
  retryingClientMessageId,
  toolMode = "auto",
  onToolModeChange,
  searchEnabled = false,
  onDraftChange,
  onSubmit,
  onRetry,
}: ChatThreadProps) {
  const composerMode = toolMode === "google_search" ? "search" : "direct";

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col" aria-labelledby="active-thread-heading">
      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mb-2 text-3xl font-serif tracking-tight sm:text-4xl md:text-5xl">
          <span className="block leading-[1.05] font-sans text-2xl" id="active-thread-heading">
            {conversation?.title ?? "New Chat"}
          </span>
        </div>
        <div className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
          {conversation
            ? `Updated recently · ${conversation.message_count} ${conversation.message_count === 1 ? "message" : "messages"}`
            : "Say hello to start"}
        </div>

        <div className="mb-6 flex flex-wrap gap-2 border-b border-zinc-200 pb-5 dark:border-zinc-800">
          {[
            "Certified",
            searchEnabled ? "Grounded Search" : "Private",
            "Secure",
            "Helpful",
          ].map((chip) => (
            <span
              key={chip}
              className="inline-flex items-center rounded-full border border-zinc-200 px-3 py-1 text-xs text-zinc-700 dark:border-zinc-800 dark:text-zinc-200 ui-safe-text"
            >
              {chip}
            </span>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.3s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.15s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400"></div>
            </div>
            <span className="text-sm text-zinc-500">Loading conversation...</span>
          </div>
        ) : (
          <MessageList
            messages={conversation?.messages ?? []}
            retryingClientMessageId={retryingClientMessageId}
            onRetry={onRetry}
          />
        )}
      </div>

      <ChatComposer
        mode={composerMode}
        onModeChange={onToolModeChange ? (mode) => onToolModeChange(mode === "search" ? "google_search" : "auto") : undefined}
        pending={pending}
        searchEnabled={searchEnabled}
        submitting={submitting}
        value={draft}
        onChange={onDraftChange}
        onSubmit={onSubmit}
      />
    </div>
  );
}
