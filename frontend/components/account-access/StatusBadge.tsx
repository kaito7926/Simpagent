import type { ReactNode } from "react";

type StatusBadgeProps = {
  tone: "neutral" | "success" | "warning" | "danger";
  children: ReactNode;
};

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return <span className={`status-badge tone-${tone}`}>{children}</span>;
}
