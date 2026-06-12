import React from "react";

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
      <button type="button" disabled={undoing} onClick={() => void onUndo()}>
        {undoing ? "Restoring..." : "Undo"}
      </button>
    </div>
  );
}
