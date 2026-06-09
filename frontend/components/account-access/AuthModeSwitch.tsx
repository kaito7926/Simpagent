import { ActionButton } from "./ActionButton";

type AuthModeSwitchProps = {
  mode: "login" | "register";
  onChange: (mode: "login" | "register") => void;
};

export function AuthModeSwitch({ mode, onChange }: AuthModeSwitchProps) {
  return (
    <div className="auth-mode-switch" role="group" aria-label="Chế độ tài khoản">
      <ActionButton
        type="button"
        variant={mode === "login" ? "secondary" : "quiet"}
        className={mode === "login" ? "mode-selected" : "mode-unselected"}
        aria-pressed={mode === "login"}
        onClick={() => onChange("login")}
      >
        Đăng nhập
      </ActionButton>
      <ActionButton
        type="button"
        variant={mode === "register" ? "secondary" : "quiet"}
        className={mode === "register" ? "mode-selected" : "mode-unselected"}
        aria-pressed={mode === "register"}
        onClick={() => onChange("register")}
      >
        Đăng ký
      </ActionButton>
    </div>
  );
}
