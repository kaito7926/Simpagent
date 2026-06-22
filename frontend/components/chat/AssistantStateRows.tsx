import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import type { ChatMessage } from "@/lib/chat-types";

import { ActionButton } from "@/components/account-access/ActionButton";

type AssistantStateRowsProps = {
  message: ChatMessage;
  retryClientMessageId: string | null;
  retrying: boolean;
  onRetry: (clientMessageId: string) => void;
};

function metadataString(message: ChatMessage, key: string): string | null {
  const value = message.metadata[key];
  return typeof value === "string" && value ? value : null;
}

export function AssistantStateRows({
  message,
  retryClientMessageId,
  retrying,
  onRetry,
}: AssistantStateRowsProps) {
  if (message.status === "pending") {
    return (
      <div className="max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800" role="status" aria-live="polite">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.3s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.15s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400"></div>
          </div>
          <span className="text-sm text-zinc-500">AI is thinking...</span>
        </div>
      </div>
    );
  }

  if (message.status !== "failed") {
    return null;
  }

  const correlationId = metadataString(message, "correlation_id");
  const retryable = message.metadata.retryable !== false && retryClientMessageId !== null;

  return (
    <div className="max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800" role="alert">
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertTriangle aria-hidden="true" size={18} strokeWidth={1.8} />
          <p className="text-sm font-semibold">The reply could not be completed.</p>
        </div>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Try again. If the issue continues, use the reference code below when asking for support.
        </p>
        {correlationId ? (
          <code className="inline-flex w-fit rounded-md bg-red-50 px-2 py-1 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
            Reference code: {correlationId}
          </code>
        ) : null}
        {retryable ? (
          <ActionButton
            className="w-fit"
            type="button"
            variant="secondary"
            disabled={retrying}
            fullWidth={false}
            onClick={() => onRetry(retryClientMessageId)}
          >
            <RefreshCw aria-hidden="true" size={16} strokeWidth={1.8} />
            {retrying ? "Retrying response..." : "Retry response"}
          </ActionButton>
        ) : null}
      </div>
    </div>
  );
}
