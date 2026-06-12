import { Bot, FlaskConical, UserRound } from "lucide-react";

import { LimitReachedCard } from "@/components/chat/LimitReachedCard";
import { PythonResultCard } from "@/components/chat/PythonResultCard";
import { ToolDeniedCard } from "@/components/chat/ToolDeniedCard";
import { presentPythonToolResult, type ChatMessage } from "@/lib/chat/tool-results";

type MessageBubbleProps = {
  message: ChatMessage;
};

function SenderAvatar({ kind }: { kind: "assistant" | "user" | "python" }) {
  const icon =
    kind === "user" ? (
      <UserRound size={16} strokeWidth={1.75} />
    ) : kind === "python" ? (
      <FlaskConical size={16} strokeWidth={1.75} />
    ) : (
      <Bot size={16} strokeWidth={1.75} />
    );
  return <span className={`chat-avatar chat-avatar-${kind}`} aria-hidden="true">{icon}</span>;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.kind === "python") {
    const surface = presentPythonToolResult(message.result);

    return (
      <div className="chat-message-row chat-message-row-assistant" data-message-kind="python">
        <SenderAvatar kind="python" />
        <div className="chat-message-stack">
          {surface.kind === "tool-denied" ? <ToolDeniedCard result={surface} /> : null}
          {surface.kind === "limit-reached" ? <LimitReachedCard result={surface} /> : null}
          {surface.kind === "python-result" ? <PythonResultCard result={surface} /> : null}
          <span className="chat-message-meta">{message.timestamp}</span>
        </div>
      </div>
    );
  }

  const isUser = message.kind === "user";

  return (
    <div
      className={`chat-message-row ${isUser ? "chat-message-row-user" : "chat-message-row-assistant"}`}
      data-message-kind={message.kind}
    >
      {!isUser ? <SenderAvatar kind="assistant" /> : null}
      <div className="chat-message-stack">
        <article className={`chat-text-bubble ${isUser ? "chat-text-bubble-user" : "chat-text-bubble-assistant"}`}>
          <p className="chat-message-label">{isUser ? "Bạn" : "Trợ lý"}</p>
          <p className="chat-message-content">{message.content}</p>
        </article>
        <span className="chat-message-meta">{message.timestamp}</span>
      </div>
      {isUser ? <SenderAvatar kind="user" /> : null}
    </div>
  );
}
