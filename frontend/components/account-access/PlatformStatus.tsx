import type { ReadinessResponse } from "@/lib/auth-session";
import {
  AGGREGATE_STATE_BODIES,
  AGGREGATE_STATE_LABELS,
  COMPONENT_LABELS,
  aggregateStateTone,
  componentStateLabel,
  detailsDefaultOpen,
  toAggregateUiState,
} from "@/lib/readiness";

import { ActionButton } from "./ActionButton";
import { StatusBadge } from "./StatusBadge";

type PlatformStatusProps = {
  readiness: ReadinessResponse | null;
  isLoading: boolean;
  isRefreshing: boolean;
  onRefresh: () => void;
};

export function PlatformStatus({ readiness, isLoading, isRefreshing, onRefresh }: PlatformStatusProps) {
  const aggregate = isLoading ? "loading" : toAggregateUiState(readiness);
  const detailRows = readiness
    ? (Object.entries(readiness.components) as Array<[keyof ReadinessResponse["components"], string]>)
    : [];

  return (
    <section className="status-panel" aria-labelledby="platform-status-heading">
      <div className="status-panel-header">
        <StatusBadge tone={aggregateStateTone(aggregate)}>{AGGREGATE_STATE_LABELS[aggregate]}</StatusBadge>
        <ActionButton
          type="button"
          variant="secondary"
          onClick={onRefresh}
          disabled={isRefreshing}
          fullWidth={false}
        >
          {isRefreshing ? "Đang kiểm tra..." : "Kiểm tra lại"}
        </ActionButton>
      </div>
      <h2 className="section-heading" id="platform-status-heading">
        {AGGREGATE_STATE_LABELS[aggregate]}
      </h2>
      <p className="body-copy max-copy">{AGGREGATE_STATE_BODIES[aggregate]}</p>

      {detailRows.length > 0 ? (
        <details className="status-details" open={detailsDefaultOpen(readiness)}>
          <summary>Xem trạng thái thành phần</summary>
          <div className="status-detail-list">
            {detailRows.map(([key, value]) => (
              <div className="status-detail-row" key={key}>
                <span className="status-detail-node" aria-hidden="true" />
                <div className="status-detail-copy">
                  <span className="status-detail-label">{COMPONENT_LABELS[key]}</span>
                  <span className="status-detail-value">{componentStateLabel(value)}</span>
                </div>
              </div>
            ))}
          </div>
        </details>
      ) : (
        <p className="body-copy status-empty">Chưa có dữ liệu trạng thái thành phần.</p>
      )}
    </section>
  );
}
