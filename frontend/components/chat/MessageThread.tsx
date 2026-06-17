import type { ChatTurn } from "@/lib/chat-session";

import { AssistantMessageCard } from "./AssistantMessageCard";
import { UserMessageCard } from "./UserMessageCard";

type MessageThreadProps = {
  turns: ChatTurn[];
  mode: "direct" | "search";
  activeRetryId: string | null;
  onPrefillSuggestion: (query: string) => void;
  onRetry: (turnId: string) => void;
};

export function MessageThread({
  turns,
  mode,
  activeRetryId,
  onPrefillSuggestion,
  onRetry,
}: MessageThreadProps) {
  if (turns.length === 0) {
    return (
      <section className="message-thread empty-thread">
        <div className="message-card assistant-message-card">
          <h2 className="section-heading">No messages yet</h2>
          <p className="body-copy">
            {mode === "search"
              ? 'Choose "Google Search", enter a question that needs current information, and send it.'
              : "Write a message to start a direct conversation."}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="message-thread" aria-live="polite">
      {turns.map((turn) =>
        turn.role === "user" ? (
          <UserMessageCard key={turn.id} turn={turn} />
        ) : (
          <AssistantMessageCard
            key={turn.id}
            turn={turn}
            retryDisabled={activeRetryId === turn.id}
            onPrefillSuggestion={onPrefillSuggestion}
            onRetry={onRetry}
          />
        ),
      )}
    </section>
  );
}
