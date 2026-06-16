"use client";

import React from "react";

import type { EvidenceRow } from "@/components/admin/EvidenceTable";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

type EvidenceDetailDrawerProps = {
  open: boolean;
  title: string;
  description: string;
  row: EvidenceRow | null;
  onOpenChange: (open: boolean) => void;
};

function bounded(value: React.ReactNode): React.ReactNode {
  if (typeof value !== "string") {
    return value;
  }
  return value.length > 240 ? `${value.slice(0, 237)}...` : value;
}

export function EvidenceDetailDrawer({
  open,
  title,
  description,
  row,
  onOpenChange,
}: EvidenceDetailDrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <aside
      aria-modal="true"
      className="flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-[0_24px_100px_rgba(15,23,42,0.16)]"
      role="dialog"
    >
      <div className="flex flex-col gap-2 text-left">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-[var(--muted-foreground)]">{description}</p>
        <button className="sr-only" onClick={() => onOpenChange(false)} type="button">
          Close details
        </button>
      </div>

      {row ? (
        <div className="space-y-5">
          <div className="rounded-2xl border border-[var(--border)] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold">{row.primary}</p>
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">{row.secondary}</p>
              </div>
              <Badge variant="secondary">{row.status}</Badge>
            </div>
            {row.correlationId ? (
              <code className="mt-3 inline-block rounded-lg bg-[var(--muted)] px-2 py-1 text-xs">
                {row.correlationId}
              </code>
            ) : null}
          </div>

          <div>
            <h3 className="text-sm font-semibold">Allowed fields</h3>
            <dl className="mt-3 space-y-3">
              {Object.entries(row.fields).map(([key, value]) => (
                <div className="rounded-2xl bg-[var(--muted)] px-3 py-2" key={key}>
                  <dt className="text-xs font-semibold text-[var(--muted-foreground)]">{key}</dt>
                  <dd className="mt-1 break-words text-sm">{bounded(value)}</dd>
                </div>
              ))}
            </dl>
          </div>

          <Separator />

          <div>
            <h3 className="text-sm font-semibold">Sanitized snippets</h3>
            {row.snippets && row.snippets.length > 0 ? (
              <div className="mt-3 space-y-3">
                {row.snippets.map((snippet, index) => (
                  <div className="rounded-2xl border border-[var(--border)] p-3" key={`${snippet.kind}-${index}`}>
                    <div className="flex items-center justify-between gap-3">
                      <Badge variant="outline">{snippet.kind}</Badge>
                      {snippet.truncated ? <span className="text-xs text-[var(--muted-foreground)]">Truncated</span> : null}
                    </div>
                    <p className="mt-2 break-words text-sm">{bounded(snippet.text)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                No sanitized snippets were returned for this row.
              </p>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-[var(--muted-foreground)]">Select an evidence row to inspect sanitized details.</p>
      )}
    </aside>
  );
}
