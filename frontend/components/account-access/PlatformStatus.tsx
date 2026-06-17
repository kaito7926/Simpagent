import React from "react";

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
    <section className="space-y-4 rounded-3xl border border-zinc-200 bg-white/90 p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <StatusBadge tone={aggregateStateTone(aggregate)}>{AGGREGATE_STATE_LABELS[aggregate]}</StatusBadge>
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900">{AGGREGATE_STATE_LABELS[aggregate]}</h2>
          <p className="text-sm leading-6 text-zinc-600">{AGGREGATE_STATE_BODIES[aggregate]}</p>
        </div>
        <ActionButton type="button" variant="secondary" onClick={onRefresh} disabled={isRefreshing} fullWidth={false}>
          {isRefreshing ? "Checking..." : "Check again"}
        </ActionButton>
      </div>

      {detailRows.length > 0 ? (
        <details className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4" open={detailsDefaultOpen(readiness)}>
          <summary className="cursor-pointer text-sm font-semibold text-zinc-900">View component status</summary>
          <div className="mt-4 space-y-3">
            {detailRows.map(([key, value]) => (
              <div className="flex items-center justify-between gap-3 border-b border-zinc-200 pb-3 last:border-0 last:pb-0" key={key}>
                <span className="text-sm font-medium text-zinc-900">{COMPONENT_LABELS[key]}</span>
                <span className="text-sm text-zinc-600">{componentStateLabel(value)}</span>
              </div>
            ))}
          </div>
        </details>
      ) : (
        <p className="text-sm text-zinc-600">Component status is not available yet.</p>
      )}
    </section>
  );
}
