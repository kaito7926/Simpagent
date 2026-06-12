import React from "react";

import type { ChatMessage } from "@/lib/chat-types";

import { AssistantStateRows } from "./AssistantStateRows";

type MessageListProps = {
  messages: ChatMessage[];
  retryingClientMessageId: string | null;
  onRetry: (clientMessageId: string) => void;
};

function retryIdFor(messages: ChatMessage[], index: number): string | null {
  const message = messages[index];
  if (message.client_message_id) {
    return message.client_message_id;
  }

  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    const candidate = messages[cursor];
    if (candidate.role === "user" && candidate.client_message_id) {
      return candidate.client_message_id;
    }
  }

  return null;
}

export function MessageList({
  messages,
  retryingClientMessageId,
  onRetry,
}: MessageListProps) {
  return (
    <ol className="message-list" aria-label="Conversation messages">
      {messages.map((message, index) => {
        if (message.role !== "user" && message.role !== "assistant") {
          return null;
        }

        const retryClientMessageId = retryIdFor(messages, index);
        return (
          <li
            className={`message-row message-row-${message.role}`}
            key={message.id}
          >
            {message.role === "assistant" && message.status !== "completed" ? (
              <AssistantStateRows
                message={message}
                retryClientMessageId={retryClientMessageId}
                retrying={retryingClientMessageId === retryClientMessageId}
                onRetry={onRetry}
              />
            ) : (
              <article className={`message-card message-card-${message.role}`}>
                <p className="message-role">
                  {message.role === "user" ? "You" : "SimpAgent"}
                </p>
                <div className="message-content">{message.content}</div>
              </article>
            )}
          </li>
        );
      })}
    </ol>
  );
}
