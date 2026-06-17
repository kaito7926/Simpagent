import React from "react";

import { ActionButton } from "@/components/account-access/ActionButton";
import { InlineAlert } from "@/components/account-access/InlineAlert";
import type { AssistantTurnState } from "@/lib/chat-session";

type SearchFailureCardProps = {
  state: Extract<AssistantTurnState, "denied" | "search_unavailable" | "provider_failed" | "timeout">;
  correlationId: string | null;
  retryDisabled: boolean;
  onRetry: () => void;
};

const COPY = {
  denied: {
    tone: "warning" as const,
    title: "Search was blocked",
    body: "This request is not allowed to use Google Search. No external search was executed.",
    retry: false,
  },
  search_unavailable: {
    tone: "danger" as const,
    title: "Search is currently unavailable",
    body: "Google Search is not ready for this turn yet. Try the search again or switch back to direct chat.",
    retry: true,
  },
  provider_failed: {
    tone: "danger" as const,
    title: "Search failed",
    body: "The search provider could not complete this request. Try the search again or switch back to direct chat.",
    retry: true,
  },
  timeout: {
    tone: "danger" as const,
    title: "Search timed out",
    body: "Google Search did not return a result in time. Try the search again or switch back to direct chat.",
    retry: true,
  },
};

export function SearchFailureCard({
  state,
  correlationId,
  retryDisabled,
  onRetry,
}: SearchFailureCardProps) {
  const copy = COPY[state];

  return (
    <div className="search-failure-card">
      <InlineAlert
        tone={copy.tone}
        title={copy.title}
        message={copy.body}
        detail={correlationId ? `Reference code: ${correlationId}` : null}
        urgent
      />
      {copy.retry ? (
        <ActionButton
          type="button"
          variant="secondary"
          fullWidth={false}
          className="search-retry-button"
          disabled={retryDisabled}
          onClick={onRetry}
        >
          {retryDisabled ? "Retrying..." : "Retry search"}
        </ActionButton>
      ) : null}
    </div>
  );
}
