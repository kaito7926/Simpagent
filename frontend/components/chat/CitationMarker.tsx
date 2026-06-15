import React from "react";

import { ActionButton } from "@/components/account-access/ActionButton";

type CitationMarkerProps = {
  marker: number;
  label: string;
  sourceId: string;
};

export function CitationMarker({ marker, label, sourceId }: CitationMarkerProps) {
  function handleJump() {
    if (typeof document === "undefined") {
      return;
    }

    document.getElementById(sourceId)?.focus();
  }

  return (
    <ActionButton
      type="button"
      className="citation-marker"
      aria-label={label}
      fullWidth={false}
      variant="secondary"
      onClick={handleJump}
    >
      [{marker}]
    </ActionButton>
  );
}
