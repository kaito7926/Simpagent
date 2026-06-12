"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import type { PresentedExecutionDetails } from "@/lib/chat/tool-results";

type PythonDetailsToggleProps = {
  details: PresentedExecutionDetails;
};

export function PythonDetailsToggle({ details }: PythonDetailsToggleProps) {
  const [isOpen, setIsOpen] = useState(false);
  const summaryLabel = isOpen ? details.openLabel : details.closedLabel;

  return (
    <details
      className="python-details"
      onToggle={(event) => setIsOpen((event.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="python-details-summary">
        <span>{summaryLabel}</span>
        <span className="python-details-icon" aria-hidden="true">
          {isOpen ? <ChevronUp size={16} strokeWidth={1.75} /> : <ChevronDown size={16} strokeWidth={1.75} />}
        </span>
      </summary>

      <div className="python-details-body">
        <dl className="python-details-meta">
          <div className="python-details-meta-row">
            <dt>execution_id</dt>
            <dd>{details.executionId}</dd>
          </div>
          {details.correlationId ? (
            <div className="python-details-meta-row">
              <dt>correlation_id</dt>
              <dd>{details.correlationId}</dd>
            </div>
          ) : null}
        </dl>

        {details.stdout ? (
          <div className="python-output-panel">
            <p className="python-section-label">stdout</p>
            <pre className="python-output-block">{details.stdout}</pre>
          </div>
        ) : null}

        {details.stderr ? (
          <div className="python-output-panel">
            <p className="python-section-label">stderr</p>
            <pre className="python-output-block">{details.stderr}</pre>
          </div>
        ) : null}
      </div>
    </details>
  );
}
