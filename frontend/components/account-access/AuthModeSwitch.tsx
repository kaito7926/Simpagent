import React from "react";

import { ActionButton } from "./ActionButton";

type AuthModeSwitchProps = {
  mode: "login" | "register";
  onChange: (mode: "login" | "register") => void;
};

export function AuthModeSwitch({ mode, onChange }: AuthModeSwitchProps) {
  return (
    <div className="auth-mode-switch" role="group" aria-label="Account mode">
      <ActionButton
        type="button"
        variant={mode === "login" ? "secondary" : "quiet"}
        className={mode === "login" ? "mode-selected" : "mode-unselected"}
        aria-pressed={mode === "login"}
        onClick={() => onChange("login")}
      >
        Sign in
      </ActionButton>
      <ActionButton
        type="button"
        variant={mode === "register" ? "secondary" : "quiet"}
        className={mode === "register" ? "mode-selected" : "mode-unselected"}
        aria-pressed={mode === "register"}
        onClick={() => onChange("register")}
      >
        Create account
      </ActionButton>
    </div>
  );
}
