import type { FormEvent } from "react";

import { ActionButton } from "@/components/account-access/ActionButton";

import { ToolModeSwitch } from "./ToolModeSwitch";

type MessageComposerProps = {
  draft: string;
  mode: "direct" | "search";
  submitLabel: string;
  disabled: boolean;
  searchEnabled: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  onDraftChange: (draft: string) => void;
  onModeChange: (mode: "direct" | "search") => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function MessageComposer({
  draft,
  mode,
  submitLabel,
  disabled,
  searchEnabled,
  textareaRef,
  onDraftChange,
  onModeChange,
  onSubmit,
}: MessageComposerProps) {
  return (
    <form className="message-composer" onSubmit={onSubmit}>
      <div className="composer-label-row">
        <h2 className="section-heading">Chế độ trả lời</h2>
        <p className="mode-prompt">
          {mode === "search"
            ? "Dùng khi cần thông tin hiện tại và nguồn dẫn."
            : "Không dùng tìm kiếm bên ngoài."}
        </p>
      </div>
      <ToolModeSwitch
        mode={mode}
        disabled={disabled}
        searchEnabled={searchEnabled}
        onChange={onModeChange}
      />
      <label className="form-field" htmlFor="chat-composer">
        <span className="visually-hidden">Ô soạn tin nhắn</span>
        <textarea
          id="chat-composer"
          ref={textareaRef}
          className="text-input chat-textarea"
          value={draft}
          disabled={disabled}
          rows={4}
          onChange={(event) => onDraftChange(event.target.value)}
        />
      </label>
      <ActionButton type="submit" disabled={disabled || !draft.trim()} fullWidth={false}>
        {submitLabel}
      </ActionButton>
    </form>
  );
}
