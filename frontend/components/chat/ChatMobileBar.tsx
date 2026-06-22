import React from "react";
import Image from "next/image";
import { Menu, MessageSquarePlus } from "lucide-react";

import { ActionButton } from "@/components/account-access/ActionButton";

type ChatMobileBarProps = {
  onOpenNavigation: () => void;
  onNewChat: () => void;
};

export function ChatMobileBar({ onOpenNavigation, onNewChat }: ChatMobileBarProps) {
  return (
    <header className="mobile-bar flex h-16 shrink-0 items-center gap-3 border-b border-zinc-200/70 bg-white px-3 dark:border-zinc-800 dark:bg-zinc-950 md:hidden">
      <button
        className="mobile-bar-button inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-zinc-200 text-zinc-700 transition hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-900"
        type="button"
        aria-label="Open conversation navigation"
        onClick={onOpenNavigation}
      >
        <Menu aria-hidden="true" size={20} strokeWidth={1.75} />
      </button>
      <div className="mobile-bar-brand flex min-w-0 flex-1 items-center gap-2 text-sm font-semibold tracking-tight">
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-white shadow-sm dark:border-zinc-700">
          <Image alt="SimpAgent mark" height={22} src="/brand/auroraguard-logo-mark-white.png" width={22} />
        </span>
        <span className="truncate">SimpAgent</span>
      </div>
      <ActionButton type="button" fullWidth={false} onClick={onNewChat}>
        <MessageSquarePlus aria-hidden="true" size={16} strokeWidth={1.75} />
        <span>New chat</span>
      </ActionButton>
    </header>
  );
}
