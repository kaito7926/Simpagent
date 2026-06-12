"use client";

import React, { FormEvent, KeyboardEvent, useState } from "react";
import { ArrowUp } from "lucide-react";

type ChatComposerProps = {
  value: string;
  pending: boolean;
  submitting: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void | Promise<void>;
};

export function ChatComposer({
  value,
  pending,
  submitting,
  onChange,
  onSubmit,
}: ChatComposerProps) {
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const empty = value.trim().length === 0;
  const disabled = pending || submitting;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (empty) {
      setValidationMessage("Write a message before sending.");
      return;
    }
    if (disabled) {
      return;
    }

    setValidationMessage(null);
    void onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  return (
    <form className="chat-composer" onSubmit={submit} noValidate>
      {pending ? (
        <p className="composer-helper" role="status">
          Wait for the current reply to finish before sending another message.
        </p>
      ) : null}
      <label className="composer-label" htmlFor="chat-message">
        Message
      </label>
      <textarea
        id="chat-message"
        className="composer-textarea"
        rows={2}
        value={value}
        placeholder="Message SimpAgent"
        disabled={disabled}
        aria-describedby={validationMessage ? "chat-message-error" : undefined}
        aria-invalid={validationMessage ? true : undefined}
        onChange={(event) => {
          onChange(event.target.value);
          if (validationMessage) {
            setValidationMessage(null);
          }
        }}
        onKeyDown={handleKeyDown}
      />
      <div className="composer-actions">
        <p className="composer-hint">Enter to send. Shift+Enter for a new line.</p>
        <button
          className="chat-send-button"
          type="submit"
          disabled={disabled || empty}
        >
          <ArrowUp aria-hidden="true" size={18} strokeWidth={2} />
          <span>{submitting ? "Sending..." : "Send message"}</span>
        </button>
      </div>
      {validationMessage ? (
        <p className="composer-error" id="chat-message-error" role="alert">
          {validationMessage}
        </p>
      ) : null}
    </form>
  );
}
