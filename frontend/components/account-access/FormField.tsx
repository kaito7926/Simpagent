import React from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type FormFieldProps = {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  error?: string | null;
  children?: ReactNode;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "id">;

export function FormField({ id, label, required = true, hint, error, children, ...inputProps }: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="form-field">
      <Label className="form-label" htmlFor={id}>
        <span>{label}</span>
        {required ? <span className="required-note">Required</span> : null}
      </Label>
      {children ?? (
        <Input {...inputProps} id={id} aria-invalid={Boolean(error)} aria-describedby={describedBy} className="text-input" />
      )}
      {hint ? (
        <p className="field-hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="field-error" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
