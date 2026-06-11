import { ActionButton } from "@/components/account-access/ActionButton";
import type { ChatMode } from "@/lib/chat-session";

type ToolModeSwitchProps = {
  mode: ChatMode;
  disabled: boolean;
  searchEnabled: boolean;
  onChange: (mode: ChatMode) => void;
};

export function ToolModeSwitch({
  mode,
  disabled,
  searchEnabled,
  onChange,
}: ToolModeSwitchProps) {
  return (
    <div className="chat-mode-switch" role="group" aria-label="Chế độ trả lời">
      <ActionButton
        type="button"
        variant={mode === "direct" ? "secondary" : "quiet"}
        className={mode === "direct" ? "mode-selected" : "mode-unselected"}
        aria-pressed={mode === "direct"}
        disabled={disabled}
        onClick={() => onChange("direct")}
      >
        Hỏi bình thường
      </ActionButton>
      {searchEnabled ? (
        <ActionButton
          type="button"
          variant={mode === "search" ? "secondary" : "quiet"}
          className={mode === "search" ? "mode-selected" : "mode-unselected"}
          aria-pressed={mode === "search"}
          disabled={disabled}
          onClick={() => onChange("search")}
        >
          Tìm bằng Google
        </ActionButton>
      ) : null}
    </div>
  );
}
