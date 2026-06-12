import { FlaskConical, ShieldAlert } from "lucide-react";

import { PythonArtifactList } from "@/components/chat/PythonArtifactList";
import { PythonDetailsToggle } from "@/components/chat/PythonDetailsToggle";
import { PythonStatusBadge } from "@/components/chat/PythonStatusBadge";
import type { PresentedPythonResultCard } from "@/lib/chat/tool-results";

type PythonResultCardProps = {
  result: PresentedPythonResultCard;
};

function cardClassName(status: PresentedPythonResultCard["status"]) {
  switch (status) {
    case "accepted":
    case "running":
      return "python-surface-warning";
    case "policy_error":
    case "infra_failure":
      return "python-surface-danger";
    case "succeeded":
    default:
      return "python-surface-success";
  }
}

export function PythonResultCard({ result }: PythonResultCardProps) {
  return (
    <article
      className={`python-card ${cardClassName(result.status)}`}
      data-python-variant={result.status}
      data-tool-surface="python-result"
      role={result.liveRole}
      aria-live={result.liveMode}
      aria-busy={result.isBusy}
    >
      <div className="python-card-spine" aria-hidden="true" />
      <div className="python-card-body">
        <header className="python-card-header">
          <div className="python-card-title-block">
            <div className="python-card-eyebrow-row">
              <span className="python-card-icon" aria-hidden="true">
                {result.status === "policy_error" ? (
                  <ShieldAlert size={18} strokeWidth={1.75} />
                ) : (
                  <FlaskConical size={18} strokeWidth={1.75} />
                )}
              </span>
              <p className="eyebrow">{result.eyebrow}</p>
            </div>
            <h2 className="python-card-title">{result.title}</h2>
          </div>
          <PythonStatusBadge status={result.status} />
        </header>

        <div className="python-card-meta">
          {result.durationLabel ? <span>Thời lượng {result.durationLabel}</span> : null}
          {result.profileLabel ? <span>Hồ sơ {result.profileLabel}</span> : null}
        </div>

        <p className="python-card-summary">{result.summary}</p>
        {result.helperText ? <p className="python-card-helper">{result.helperText}</p> : null}

        <PythonArtifactList artifacts={result.artifacts} />
        {result.details ? <PythonDetailsToggle details={result.details} /> : null}
      </div>
    </article>
  );
}
