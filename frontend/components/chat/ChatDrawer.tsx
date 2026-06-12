import React from "react";
import { X } from "lucide-react";

import { ChatSidebar, type ChatNavigationProps } from "./ChatSidebar";

type ChatDrawerProps = {
  open: boolean;
  onClose: () => void;
  navigationProps: ChatNavigationProps;
};

export function ChatDrawer({ open, onClose, navigationProps }: ChatDrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="mobile-nav-overlay" role="presentation" onClick={onClose}>
      <aside
        className="mobile-conversation-navigation"
        role="dialog"
        aria-modal="true"
        aria-label="Conversation navigation"
        onClick={(event) => event.stopPropagation()}
      >
        <button className="drawer-close-button" type="button" aria-label="Close navigation" onClick={onClose}>
          <X aria-hidden="true" size={18} strokeWidth={1.75} />
        </button>
        <ChatSidebar {...navigationProps} />
      </aside>
    </div>
  );
}
