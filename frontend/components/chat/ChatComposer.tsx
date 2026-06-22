import React, { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ArrowUp, Check, Globe, Loader2, Plus } from "lucide-react";

import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

type ChatComposerProps = {
  value: string;
  pending: boolean;
  submitting: boolean;
  mode?: "direct" | "search";
  searchEnabled?: boolean;
  onModeChange?: (mode: "direct" | "search") => void;
  onChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
};

export function ChatComposer({
  value,
  pending,
  submitting,
  mode = "direct",
  searchEnabled = false,
  onModeChange,
  onChange,
  onSubmit,
}: ChatComposerProps) {
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const empty = value.trim().length === 0;
  const disabled = pending || submitting;

  useEffect(() => {
    if (inputRef.current) {
      const textarea = inputRef.current;
      const lineHeight = 24;
      const minHeight = 24;

      textarea.style.height = "auto";
      const scrollHeight = textarea.scrollHeight;
      const calculatedLines = Math.max(1, Math.ceil(scrollHeight / lineHeight));

      if (calculatedLines <= 12) {
        textarea.style.height = `${Math.max(minHeight, scrollHeight)}px`;
        textarea.style.overflowY = "hidden";
      } else {
        textarea.style.height = `${12 * lineHeight}px`;
        textarea.style.overflowY = "auto";
      }
    }
  }, [value]);

  function submit(event?: FormEvent<HTMLFormElement>) {
    if (event) event.preventDefault();
    if (empty) return;
    if (disabled) return;

    setValidationMessage(null);
    void onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  const hasContent = !empty;

  return (
    <div className="border-t border-zinc-200/60 p-4 dark:border-zinc-800">
      <div
        className={cn(
          "mx-auto flex flex-col rounded-3xl border bg-white shadow-sm dark:bg-zinc-950 transition-all duration-200",
          "max-w-3xl border-zinc-200 dark:border-zinc-800"
        )}
      >
        <div className="flex-1 px-4 pt-4 pb-2">
          <textarea
            ref={inputRef}
            value={value}
            disabled={disabled}
            onChange={(e) => {
              onChange(e.target.value);
              if (validationMessage) setValidationMessage(null);
            }}
            placeholder={pending ? "Wait for the current reply..." : "How can I help you today?"}
            rows={1}
            className={cn(
              "w-full resize-none bg-transparent text-sm outline-none placeholder:text-zinc-400 transition-all duration-200 break-words",
              "min-h-[24px] text-left leading-6",
              disabled ? "opacity-50 cursor-not-allowed" : ""
            )}
            onKeyDown={handleKeyDown}
          />
        </div>

        <div className="flex items-center justify-between px-3 pb-3">
          {searchEnabled ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="inline-flex shrink-0 items-center justify-center rounded-full p-2 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
                  title="Tools"
                  type="button"
                  disabled={disabled}
                >
                  <Plus className="h-5 w-5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56" sideOffset={8}>
                <DropdownMenuLabel>Agent tools</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => onModeChange?.(mode === "search" ? "direct" : "search")}
                  className="flex cursor-pointer items-center gap-2"
                >
                  <Globe className="h-4 w-4" />
                  <span className="flex-1">Web Search</span>
                  {mode === "search" && <Check className="h-4 w-4 text-blue-500" />}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <button
              aria-disabled="true"
              className="inline-flex shrink-0 items-center justify-center rounded-full p-2 text-zinc-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-zinc-600"
              title="No tools available for this account"
              type="button"
              disabled
            >
              <Plus className="h-5 w-5" />
            </button>
          )}

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => submit()}
              disabled={disabled || !hasContent}
              type="button"
              className={cn(
                "inline-flex shrink-0 items-center justify-center rounded-full p-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                hasContent && !disabled
                  ? "bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                  : "bg-zinc-200 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-600 cursor-not-allowed"
              )}
            >
              {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowUp className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-2 max-w-3xl px-1 text-center text-[11px] text-zinc-400 dark:text-zinc-500">
        AI can make mistakes. Check important information.
      </div>

      {validationMessage ? (
        <p className="text-center mt-2 text-sm text-destructive" role="alert">
          {validationMessage}
        </p>
      ) : null}
    </div>
  );
}
