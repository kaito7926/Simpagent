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
              <p className="eyebrow">{result.eyebrow}</p>
            </div>
            <h2 className="python-card-title">{result.title}</h2>
          </div>
          <PythonStatusBadge status={result.status} />
        </header>

        <p className="python-card-summary">{result.message}</p>
        {result.correlationId ? (
          <p className="python-card-helper">Mã hỗ trợ: {result.correlationId}</p>
        ) : (
          <p className="python-card-helper">
            Trải nghiệm vẫn giữ ở dạng ngôn ngữ tự nhiên, không có chế độ bật Python riêng.
          </p>
        )}
      </div>
    </article>
  );
}
