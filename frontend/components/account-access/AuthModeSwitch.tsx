import React from "react";

type AuthModeSwitchProps = {
  mode: "login" | "register";
  onChange: (mode: "login" | "register") => void;
};

export function AuthModeSwitch({ mode, onChange }: AuthModeSwitchProps) {
  return (
    <div className="grid grid-cols-2 gap-2" role="group" aria-label="Account mode">
      <button
        type="button"
        className={
          mode === "login"
            ? "h-11 rounded-full border border-zinc-300 bg-white text-sm font-semibold text-zinc-900 shadow-sm"
            : "h-11 rounded-full border border-gray-300 bg-gray-50 text-sm font-medium text-zinc-700 hover:bg-gray-100"
        }
        aria-pressed={mode === "login"}
        onClick={() => onChange("login")}
      >
        Sign in
      </button>
      <button
        type="button"
        className={
          mode === "register"
            ? "h-11 rounded-full border border-zinc-300 bg-white text-sm font-semibold text-zinc-900 shadow-sm"
            : "h-11 rounded-full border border-gray-300 bg-gray-50 text-sm font-medium text-zinc-700 hover:bg-gray-100"
        }
        aria-pressed={mode === "register"}
        onClick={() => onChange("register")}
      >
        Create account
      </button>
    </div>
  );
}
