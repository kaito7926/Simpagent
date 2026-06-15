import { Gauge } from "lucide-react";

import { PythonArtifactList } from "@/components/chat/PythonArtifactList";
import { PythonDetailsToggle } from "@/components/chat/PythonDetailsToggle";
import { PythonStatusBadge } from "@/components/chat/PythonStatusBadge";
import type { PresentedLimitReachedCard } from "@/lib/chat/tool-results";

type LimitReachedCardProps = {
  result: PresentedLimitReachedCard;
};

export function LimitReachedCard({ result }: LimitReachedCardProps) {
  return (
    <article
      className="python-card python-surface-warning"
      data-tool-surface="limit-reached"
      role={result.liveRole}
      aria-live={result.liveMode}
    >
      <div className="python-card-spine" aria-hidden="true" />
      <div className="python-card-body">
        <header className="python-card-header">
          <div className="python-card-title-block">
            <div className="python-card-eyebrow-row">
              <span className="python-card-icon" aria-hidden="true">
                <Gauge size={18} strokeWidth={1.75} />
              </span>
              <p className="auth-eyebrow">{result.eyebrow}</p>
            </div>
            <h2 className="python-card-title">{result.title}</h2>
          </div>
          <PythonStatusBadge status={result.status} />
        </header>

        <div className="python-card-meta">
          <span>Limit reached: {result.limitLabel}</span>
          {result.durationLabel ? <span>Duration {result.durationLabel}</span> : null}
        </div>

        <p className="python-card-summary">{result.summary}</p>
        <p className="python-card-helper">{result.helperText}</p>

        <PythonArtifactList artifacts={result.artifacts} />
        {result.details ? <PythonDetailsToggle details={result.details} /> : null}
      </div>
    </article>
  );
}
