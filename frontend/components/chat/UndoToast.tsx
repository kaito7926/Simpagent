import React from "react";

import { ActionButton } from "@/components/account-access/ActionButton";

type UndoToastProps = {
  visible: boolean;
  undoing: boolean;
  onUndo: () => void | Promise<void>;
};

export function UndoToast({ visible, undoing, onUndo }: UndoToastProps) {
  if (!visible) {
    return null;
  }

  return (
    <div className="undo-toast" role="status" aria-live="polite">
      <p>Conversation deleted</p>
      <ActionButton type="button" disabled={undoing} fullWidth={false} variant="secondary" onClick={() => void onUndo()}>
        {undoing ? "Restoring..." : "Undo"}
      </ActionButton>
    </div>
  );
}
