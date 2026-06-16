"use client";

import React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export type EvidencePageInfo = {
  limit: number;
  offset: number;
  has_more: boolean;
  next_offset: number | null;
};

export type EvidenceSnippet = {
  kind: string;
  text: string;
  truncated?: boolean;
};

export type EvidenceRow = {
  id: string;
  primary: string;
  secondary: string;
  status: string;
  correlationId?: string | null;
  fields: Record<string, React.ReactNode>;
  snippets?: EvidenceSnippet[];
};

type EvidenceTableProps = {
  title: string;
  description: string;
  rows: EvidenceRow[];
  page?: EvidencePageInfo;
  emptyTitle: string;
  loading?: boolean;
  onSelectRow?: (row: EvidenceRow) => void;
};

function badgeVariant(status: string): "default" | "secondary" | "success" | "warning" | "danger" | "outline" {
  const normalized = status.toLowerCase();
  if (["high", "critical", "failed", "denied", "inactive"].includes(normalized)) {
    return "danger";
  }
  if (["medium", "warning", "pending", "limited"].includes(normalized)) {
    return "warning";
  }
  if (["success", "succeeded", "active", "enabled"].includes(normalized)) {
    return "success";
  }
  return "secondary";
}

function fieldEntries(row: EvidenceRow) {
  return Object.entries(row.fields).filter(([, value]) => value !== null && value !== undefined && value !== "");
}

export function EvidenceTable({
  title,
  description,
  rows,
  page,
  emptyTitle,
  loading = false,
  onSelectRow,
}: EvidenceTableProps) {
  const headers = rows[0] ? Object.keys(rows[0].fields) : [];

  return (
    <Card className="overflow-hidden rounded-[20px]">
      <CardHeader className="gap-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          {page ? (
            <Badge variant="outline">
              {page.offset + 1}-{page.offset + rows.length} of bounded page
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3" aria-label="Loading evidence">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : rows.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[var(--border)] p-6 text-sm text-[var(--muted-foreground)]">
            <p className="font-semibold text-[var(--foreground)]">{emptyTitle}</p>
            <p className="mt-1">Backend returned an empty bounded page for this surface.</p>
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto rounded-2xl border border-[var(--border)] md:block">
              <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                <thead className="bg-[var(--muted)] text-[var(--muted-foreground)]">
                  <tr>
                    {headers.map((header) => (
                      <th className="px-4 py-3 font-semibold" key={header}>
                        {header}
                      </th>
                    ))}
                    <th className="px-4 py-3 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {rows.map((row) => (
                    <tr className="align-top" key={row.id}>
                      {fieldEntries(row).map(([key, value]) => (
                        <td className="px-4 py-4" key={key}>
                          {key.toLowerCase().includes("status") || key.toLowerCase().includes("severity") ? (
                            <Badge variant={badgeVariant(String(value))}>{value}</Badge>
                          ) : key.toLowerCase().includes("correlation") || key.toLowerCase().includes("reference") ? (
                            <code className="rounded-lg bg-[var(--muted)] px-2 py-1 text-xs">{value}</code>
                          ) : (
                            value
                          )}
                        </td>
                      ))}
                      <td className="px-4 py-4">
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => onSelectRow?.(row)}
                        >
                          Xem chi tiết
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-3 md:hidden">
              {rows.map((row) => (
                <div className="rounded-2xl border border-[var(--border)] p-4" key={row.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{row.primary}</p>
                      <p className="mt-1 text-sm text-[var(--muted-foreground)]">{row.secondary}</p>
                    </div>
                    <Badge variant={badgeVariant(row.status)}>{row.status}</Badge>
                  </div>
                  {row.correlationId ? (
                    <code className="mt-3 inline-block rounded-lg bg-[var(--muted)] px-2 py-1 text-xs">
                      {row.correlationId}
                    </code>
                  ) : null}
                  <Button
                    className="mt-4 w-full"
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => onSelectRow?.(row)}
                  >
                    Xem chi tiết
                  </Button>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
