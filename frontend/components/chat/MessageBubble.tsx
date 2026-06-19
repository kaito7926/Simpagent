import { Asterisk, User } from "lucide-react";

import { LimitReachedCard } from "@/components/chat/LimitReachedCard";
import { PythonResultCard } from "@/components/chat/PythonResultCard";
import { ToolDeniedCard } from "@/components/chat/ToolDeniedCard";
import { presentPythonToolResult, type ChatMessage } from "@/lib/chat/tool-results";
import { cn } from "@/lib/utils";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.kind === "python") {
    const surface = presentPythonToolResult(message.result);

    return (
      <div className="flex gap-3 justify-start" data-message-kind={message.kind}>
        <div className="mt-0.5 grid h-7 w-7 place-items-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 text-white shadow-sm dark:from-zinc-200 dark:to-zinc-300 dark:text-zinc-900 shrink-0">
          <Asterisk className="h-4 w-4" />
        </div>
        <div className="max-w-[80%] rounded-2xl p-0 text-sm shadow-sm bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 overflow-hidden">
          {surface.kind === "tool-denied" ? <ToolDeniedCard result={surface} /> : null}
          {surface.kind === "limit-reached" ? <LimitReachedCard result={surface} /> : null}
          {surface.kind === "python-result" ? <PythonResultCard result={surface} /> : null}
          <div className="px-3 py-2 text-xs text-zinc-500 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800">
            {message.timestamp}
          </div>
        </div>
      </div>
    );
  }

  const isUser = message.kind === "user";

  return (
    <div
      className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}
      data-message-kind={message.kind}
    >
      {!isUser && (
        <div className="mt-0.5 grid h-7 w-7 place-items-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 text-white shadow-sm dark:from-zinc-200 dark:to-zinc-300 dark:text-zinc-900 shrink-0">
          <Asterisk className="h-4 w-4" />
        </div>
      )}
      
      <div className="flex flex-col gap-1 max-w-[80%]">
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm shadow-sm",
            isUser
              ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
              : "bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 leading-relaxed"
          )}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>
        <div className={cn("text-[10px] text-zinc-500", isUser ? "text-right px-1" : "text-left px-1")}>
          {message.timestamp}
        </div>
      </div>

      {isUser && (
        <div className="mt-0.5 grid h-7 w-7 place-items-center rounded-full bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shrink-0">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
