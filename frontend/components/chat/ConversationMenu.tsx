import React from "react";
import { MoreVertical, Trash2 } from "lucide-react";

import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

import { ActionButton } from "@/components/account-access/ActionButton";

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
      <DropdownMenu onOpenChange={onOpenChange} open={open}>
        <DropdownMenuTrigger asChild>
          <button
            className="conversation-menu-trigger"
            type="button"
            aria-label={`Open actions for ${title}`}
            aria-expanded={open}
          >
            <MoreVertical aria-hidden="true" size={17} strokeWidth={1.75} />
            <span className="visually-hidden">Delete conversation</span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="conversation-menu-popover">
          {confirming ? (
            <div className="delete-confirmation" role="alertdialog" aria-label="Delete conversation">
              <p className="delete-confirmation-title">Delete conversation</p>
              <p className="delete-confirmation-body">
                This removes the conversation from your sidebar now. You can undo for a short time.
              </p>
              <div className="delete-confirmation-actions">
                <ActionButton
                  className="menu-delete-action"
                  type="button"
                  disabled={deleting}
                  variant="secondary"
                  onClick={() => {
                    void onDelete();
                  }}
                >
                  <Trash2 aria-hidden="true" size={15} strokeWidth={1.75} />
                  <span>Delete conversation</span>
                </ActionButton>
                <ActionButton className="menu-keep-action" type="button" variant="quiet" onClick={onKeep}>
                  Keep conversation
                </ActionButton>
              </div>
            </div>
          ) : (
            <ActionButton
              className="menu-delete-action"
              type="button"
              fullWidth
              variant="quiet"
              disabled={deleting}
              onClick={() => onOpenChange(true)}
            >
              <Trash2 aria-hidden="true" size={15} strokeWidth={1.75} />
              <span>Delete conversation</span>
            </ActionButton>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
