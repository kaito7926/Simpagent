import React from "react";
import { Menu, MessageSquarePlus } from "lucide-react";

type ChatMobileBarProps = {
  onOpenNavigation: () => void;
  onNewChat: () => void;
};

export function ChatMobileBar({ onOpenNavigation, onNewChat }: ChatMobileBarProps) {
  return (
    <header className="mobile-chat-header">
      <button type="button" aria-label="Open conversation navigation" onClick={onOpenNavigation}>
        <Menu aria-hidden="true" size={20} strokeWidth={1.75} />
      </button>
      <span>SimpAgent</span>
      <button type="button" onClick={onNewChat}>
        <MessageSquarePlus aria-hidden="true" size={16} strokeWidth={1.75} />
        <span>New chat</span>
      </button>
    </header>
  );
}
