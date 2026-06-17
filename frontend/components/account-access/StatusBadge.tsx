import React from "react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

type StatusBadgeProps = {
  tone: "neutral" | "success" | "warning" | "danger";
  children: ReactNode;
};

const VARIANT_MAP = {
  neutral: "secondary",
  success: "success",
  warning: "warning",
  danger: "danger",
} as const;

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return (
    <Badge className={`status-badge tone-${tone}`} variant={VARIANT_MAP[tone]}>
      {children}
    </Badge>
  );
}
