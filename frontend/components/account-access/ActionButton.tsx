import type { ButtonHTMLAttributes, ReactNode } from "react";
import { forwardRef } from "react";

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet";
  icon?: ReactNode;
  fullWidth?: boolean;
};

export const ActionButton = forwardRef<HTMLButtonElement, ActionButtonProps>(function ActionButton(
  {
    variant = "primary",
    icon,
    fullWidth = true,
    className,
    children,
    ...props
  },
  ref,
) {
  const classes = [
    "action-button",
    `action-button-${variant}`,
    fullWidth ? "action-button-full" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} ref={ref} {...props}>
      {icon ? <span className="button-icon" aria-hidden="true">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
});
