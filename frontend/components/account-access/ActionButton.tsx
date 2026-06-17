import React, { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet";
  icon?: ReactNode;
  fullWidth?: boolean;
};

const VARIANT_MAP = {
  primary: "default",
  secondary: "secondary",
  quiet: "ghost",
} as const;

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
  return (
    <Button
      className={cn(fullWidth ? "w-full" : "w-auto", className)}
      variant={VARIANT_MAP[variant]}
      ref={ref}
      {...props}
    >
      {icon ? <span className="button-icon" aria-hidden="true">{icon}</span> : null}
      <span>{children}</span>
    </Button>
  );
});
