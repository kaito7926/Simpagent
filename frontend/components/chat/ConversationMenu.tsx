import React from "react";
import { MoreVertical, Trash2 } from "lucide-react";

type ConversationMenuProps = {
  conversationTitle: string | null;
  open: boolean;
  confirming: boolean;
  deleting: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete: () => void | Promise<void>;
  onKeep: () => void;
};

export function ConversationMenu({
  conversationTitle,
  open,
  confirming,
  deleting,
  onOpenChange,
  onDelete,
  onKeep,
}: ConversationMenuProps) {
  const title = conversationTitle ?? "New chat";

  return (
    <div className="conversation-menu">
      <button
        className="conversation-menu-trigger"
        type="button"
        aria-label={`Open actions for ${title}`}
        aria-expanded={open}
        onClick={(event) => {
          event.stopPropagation();
          onOpenChange(!open);
        }}
      >
        <MoreVertical aria-hidden="true" size={17} strokeWidth={1.75} />
        <span className="visually-hidden">Delete conversation</span>
      </button>
      {open ? (
        <div className="conversation-menu-popover" role="menu">
          {confirming ? (
            <div className="delete-confirmation" role="alertdialog" aria-label="Delete conversation">
              <p className="delete-confirmation-title">Delete conversation</p>
              <p className="delete-confirmation-body">
                This removes the conversation from your sidebar now. You can undo for a short time.
              </p>
              <div className="delete-confirmation-actions">
                <button
                  className="menu-delete-action"
                  type="button"
                  disabled={deleting}
                  onClick={(event) => {
                    event.stopPropagation();
                    void onDelete();
                  }}
                >
                  <Trash2 aria-hidden="true" size={15} strokeWidth={1.75} />
                  <span>Delete conversation</span>
                </button>
                <button
                  className="menu-keep-action"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onKeep();
                  }}
                >
                  Keep conversation
                </button>
              </div>
            </div>
          ) : (
            <button
              className="menu-delete-action"
              type="button"
              role="menuitem"
              disabled={deleting}
              onClick={(event) => {
                event.stopPropagation();
                onOpenChange(true);
              }}
            >
              <Trash2 aria-hidden="true" size={15} strokeWidth={1.75} />
              <span>Delete conversation</span>
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}
