import React from "react";
import Image from "next/image";

import type { ChatMessage } from "@/lib/chat-types";

import { AssistantStateRows } from "./AssistantStateRows";
import { MessageMarkdown } from "./MessageMarkdown";

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

function Avatar(props: { role: "user" | "assistant" }) {
  if (props.role === "assistant") {
    return (
      <div className="mt-0.5 grid h-7 w-7 place-items-center overflow-hidden rounded-full border border-zinc-200 bg-white text-[10px] font-bold text-zinc-900 shadow-sm dark:border-zinc-700">
        <Image alt="SimpAgent mark" height={18} src="/brand/auroraguard-logo-mark-white.png" width={18} />
      </div>
    );
  }

  return (
    <div className="mt-0.5 grid h-7 w-7 place-items-center rounded-full bg-zinc-900 text-[10px] font-bold text-white dark:bg-white dark:text-zinc-900">
      YOU
    </div>
  );
}

export function MessageList({
  messages,
  retryingClientMessageId,
  onRetry,
}: MessageListProps) {
  return (
    <ol className="space-y-5" aria-label="Conversation messages">
      {messages.map((message, index) => {
        if (message.role !== "user" && message.role !== "assistant") {
          return null;
        }

        const retryClientMessageId = retryIdFor(messages, index);
        const isUser = message.role === "user";

        return (
          <li className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`} key={message.id}>
            {!isUser ? <Avatar role="assistant" /> : null}
            {message.role === "assistant" && message.status !== "completed" ? (
              <AssistantStateRows
                message={message}
                retryClientMessageId={retryClientMessageId}
                retrying={retryingClientMessageId === retryClientMessageId}
                onRetry={onRetry}
              />
            ) : (
              <article
                className={
                  isUser
                    ? "max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800"
                }
              >
                {message.role === "assistant" ? (
                  <div className="space-y-2">
                    <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                      SimpAgent
                    </div>
                    <MessageMarkdown content={message.content} />
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap break-words">{message.content}</div>
                )}
              </article>
            )}
            {isUser ? <Avatar role="user" /> : null}
          </li>
        );
      })}
    </ol>
  );
}
