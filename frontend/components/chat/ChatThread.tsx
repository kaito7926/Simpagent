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
  onDraftChange,
  onSubmit,
  onRetry,
}: ChatThreadProps) {
  if (!conversation) {
    return (
      <section className="empty-chat-state" aria-labelledby="empty-chat-heading">
        <div className="empty-chat-copy">
          <p className="workspace-kicker">PRIVATE DIRECT CHAT</p>
          <h1 id="empty-chat-heading">Start a private chat</h1>
          <p>
            Ask a question to create your first conversation. Messages stay inside your own
            workspace.
          </p>
        </div>
        <ChatComposer
          value={draft}
          pending={false}
          submitting={submitting}
          onChange={onDraftChange}
          onSubmit={onSubmit}
        />
      </section>
    );
  }

  return (
    <section className="active-chat-thread" aria-labelledby="active-thread-heading">
      <header className="thread-header">
        <p className="workspace-kicker">PRIVATE CONVERSATION</p>
        <h1 id="active-thread-heading">{conversation.title ?? "New chat"}</h1>
      </header>
      <div className="thread-scroll-region">
        {loading ? (
          <p className="thread-loading" role="status">
            Loading conversation...
          </p>
        ) : (
          <MessageList
            messages={conversation.messages}
            retryingClientMessageId={retryingClientMessageId}
            onRetry={onRetry}
          />
        )}
      </div>
      <div className="thread-composer-wrap">
        <ChatComposer
          value={draft}
          pending={pending}
          submitting={submitting}
          onChange={onDraftChange}
          onSubmit={onSubmit}
        />
      </div>
    </section>
  );
}
