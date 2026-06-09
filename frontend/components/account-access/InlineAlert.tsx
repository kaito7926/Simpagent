import type { ReactNode } from "react";

type InlineAlertProps = {
  tone: "info" | "success" | "warning" | "danger";
  title?: string;
  message: ReactNode;
  detail?: string | null;
  urgent?: boolean;
};

export function InlineAlert({ tone, title, message, detail, urgent = false }: InlineAlertProps) {
  return (
    <div className={`inline-alert inline-alert-${tone}`} role={urgent ? "alert" : "status"} aria-live={urgent ? "assertive" : "polite"}>
      {title ? <p className="inline-alert-title">{title}</p> : null}
      <div className="inline-alert-body">{message}</div>
      {detail ? <p className="inline-alert-detail">{detail}</p> : null}
    </div>
  );
}
