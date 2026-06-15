import React from "react";

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
    <div className="mobile-drawer-overlay" role="presentation" onClick={onClose}>
      <aside
        className="mobile-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Conversation navigation"
        onClick={(event) => event.stopPropagation()}
      >
        <ChatSidebar {...navigationProps} />
      </aside>
    </div>
  );
}
