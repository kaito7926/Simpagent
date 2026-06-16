"use client";

import React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type StatePanelState = "loading" | "empty" | "forbidden" | "error";

type StatePanelProps = {
  state: StatePanelState;
  title: string;
  body: string;
  referenceCode?: string | null;
};

function tone(state: StatePanelState): "secondary" | "warning" | "danger" | "outline" {
  if (state === "forbidden") return "warning";
  if (state === "error") return "danger";
  if (state === "loading") return "outline";
  return "secondary";
}

export function StatePanel({ state, title, body, referenceCode }: StatePanelProps) {
  return (
    <Card className="rounded-[20px]">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{body}</CardDescription>
          </div>
          <Badge variant={tone(state)}>{state}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {state === "loading" ? (
          <div className="space-y-3" aria-label="Loading state">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : null}
        {referenceCode ? (
          <code className="inline-block rounded-lg bg-[var(--muted)] px-2 py-1 text-xs">
            Reference code: {referenceCode}
          </code>
        ) : null}
      </CardContent>
    </Card>
  );
}
