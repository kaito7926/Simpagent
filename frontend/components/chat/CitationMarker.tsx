import React from "react";

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
    <button
      type="button"
      className="citation-marker"
      aria-label={label}
      onClick={handleJump}
    >
      [{marker}]
    </button>
  );
}
