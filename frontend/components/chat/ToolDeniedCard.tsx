import { ShieldBan } from "lucide-react";

import { PythonStatusBadge } from "@/components/chat/PythonStatusBadge";
import type { PresentedToolDeniedCard } from "@/lib/chat/tool-results";

type ToolDeniedCardProps = {
  result: PresentedToolDeniedCard;
};

export function ToolDeniedCard({ result }: ToolDeniedCardProps) {
  return (
    <article
      className="python-card python-surface-danger"
      data-tool-surface="tool-denied"
      role={result.liveRole}
      aria-live={result.liveMode}
    >
      <div className="python-card-spine" aria-hidden="true" />
      <div className="python-card-body">
        <header className="python-card-header">
          <div className="python-card-title-block">
            <div className="python-card-eyebrow-row">
              <span className="python-card-icon" aria-hidden="true">
                <ShieldBan size={18} strokeWidth={1.75} />
              </span>
              <p className="auth-eyebrow">{result.eyebrow}</p>
            </div>
            <h2 className="python-card-title">{result.title}</h2>
          </div>
          <PythonStatusBadge status={result.status} />
        </header>

        <p className="python-card-summary">{result.message}</p>
        {result.correlationId ? (
          <p className="python-card-helper">Reference code: {result.correlationId}</p>
        ) : (
          <p className="python-card-helper">
            The workspace stays natural-language first and does not expose a dedicated Python mode switch.
          </p>
        )}
      </div>
    </article>
  );
}
