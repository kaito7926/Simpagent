import React from "react";
import { AlertTriangle } from "lucide-react";

import type { ChatMessage } from "@/lib/chat-types";

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
      <div className="assistant-state assistant-pending" role="status" aria-live="polite">
        <span className="chat-spinner" aria-hidden="true" />
        <span>Generating response...</span>
      </div>
    );
  }

  if (message.status !== "failed") {
    return null;
  }

  const correlationId = metadataString(message, "correlation_id");
  const retryable = message.metadata.retryable !== false && retryClientMessageId !== null;

  return (
    <div className="assistant-state assistant-failed" role="alert">
      <div className="assistant-failed-heading">
        <AlertTriangle aria-hidden="true" size={20} strokeWidth={1.8} />
        <p>The reply could not be completed.</p>
      </div>
      <p>
        Try again. If the issue continues, use the reference code below when asking for support.
      </p>
      {correlationId ? (
        <code className="reference-code">Reference code: {correlationId}</code>
      ) : null}
      {retryable ? (
        <button
          className="chat-secondary-button"
          type="button"
          disabled={retrying}
          onClick={() => onRetry(retryClientMessageId)}
        >
          {retrying ? "Retrying response..." : "Retry response"}
        </button>
      ) : null}
    </div>
  );
}
