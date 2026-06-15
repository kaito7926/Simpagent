"use client";

import React, { useId, useState } from "react";

import { Input } from "@/components/ui/input";
import { FormField } from "./FormField";

type PasswordFieldProps = {
  id?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  disabled?: boolean;
  hint?: string;
  error?: string | null;
};

export function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  disabled = false,
  hint,
  error,
}: PasswordFieldProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const [visible, setVisible] = useState(false);
  const actionLabel = visible ? "Hide password" : "Show password";

  return (
    <FormField id={fieldId} label={label} hint={hint} error={error}>
      <div className="password-field-wrap">
        <Input
          id={fieldId}
          className="text-input password-input"
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={[hint ? `${fieldId}-hint` : undefined, error ? `${fieldId}-error` : undefined]
            .filter(Boolean)
            .join(" ") || undefined}
        />
        <button
          className="password-toggle"
          type="button"
          aria-label={actionLabel}
          onClick={() => setVisible((current) => !current)}
          disabled={disabled}
        >
          {actionLabel}
        </button>
      </div>
    </FormField>
  );
}
