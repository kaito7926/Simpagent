import { ActionButton } from "@/components/account-access/ActionButton";
import type { ChatMode, WebsearchProvider } from "@/lib/chat-session";

type ToolModeSwitchProps = {
  mode: ChatMode;
  disabled: boolean;
  searchEnabled: boolean;
  provider?: WebsearchProvider | null;
  onChange: (mode: ChatMode) => void;
};

export function ToolModeSwitch({
  mode,
  disabled,
  searchEnabled,
  provider = null,
  onChange,
}: ToolModeSwitchProps) {
  const searchLabel = provider === "gemini" ? "Google Search" : provider === "firecrawl" ? "Firecrawl Search" : "Web Search";

  return (
    <div className="chat-mode-switch" role="group" aria-label="Response mode">
      <ActionButton
        type="button"
        variant={mode === "direct" ? "secondary" : "quiet"}
        className={mode === "direct" ? "mode-selected" : "mode-unselected"}
        aria-pressed={mode === "direct"}
        disabled={disabled}
        onClick={() => onChange("direct")}
      >
        Direct chat
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
          {searchLabel}
        </ActionButton>
      ) : null}
    </div>
  );
}
