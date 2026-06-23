import React from "react";
import type { AssistantTurn } from "@/lib/chat-session";

import { GroundedAnswer } from "./GroundedAnswer";
import { SearchFailureCard } from "./SearchFailureCard";

type AssistantMessageCardProps = {
  turn: AssistantTurn;
  onPrefillSuggestion: (query: string) => void;
  onRetry: (turnId: string) => void;
  retryDisabled?: boolean;
};

export function AssistantMessageCard({
  turn,
  onPrefillSuggestion,
  onRetry,
  retryDisabled = false,
}: AssistantMessageCardProps) {
  return (
    <article className="message-card assistant-message-card">
      {turn.state === "grounded" && turn.answer ? (
        <GroundedAnswer
          answer={turn.answer}
          provider={turn.provider ?? "gemini"}
          citations={turn.citations}
          sources={turn.sources}
          suggestions={turn.suggestions}
          onPrefillSuggestion={onPrefillSuggestion}
        />
      ) : null}

      {turn.state === "missing_grounding" ? (
        <div className="assistant-answer">
          {turn.answer ? <p className="body-copy">{turn.answer}</p> : null}
          <p className="assistant-note" aria-live="polite">
            Kết quả này có thể tham khảo vì chưa có nguồn xác thực rõ ràng.
          </p>
        </div>
      ) : null}

      {turn.state === "direct" ? (
        <div className="assistant-answer">
          {turn.answer ? <p className="body-copy">{turn.answer}</p> : null}
        </div>
      ) : null}

      {turn.state === "denied" ||
      turn.state === "search_unavailable" ||
      turn.state === "provider_failed" ||
      turn.state === "timeout" ? (
        <SearchFailureCard
          state={turn.state}
          provider={turn.provider}
          correlationId={turn.correlationId ?? null}
          retryDisabled={retryDisabled}
          onRetry={() => onRetry(turn.id)}
        />
      ) : null}
    </article>
  );
}
