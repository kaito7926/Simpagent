"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { InlineAlert } from "@/components/account-access/InlineAlert";
import {
  AuthSessionController,
  type CurrentUser,
  type ReadinessResponse,
} from "@/lib/auth-session";
import {
  ChatSessionController,
  submitChatTurn,
  type ChatSessionSnapshot,
} from "@/lib/chat-session";

import { ConversationHeader } from "./ConversationHeader";
import { MessageComposer } from "./MessageComposer";
import { MessageThread } from "./MessageThread";

function readCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const parts = document.cookie.split(";").map((entry) => entry.trim());
  const match = parts.find((entry) => entry.startsWith("__Host-simpagent_csrf="));
  return match ? decodeURIComponent(match.slice("__Host-simpagent_csrf=".length)) : null;
}

export function ChatShell() {
  const authController = useMemo(
    () => new AuthSessionController("login", { getCsrfToken: readCsrfToken }),
    [],
  );
  const conversationId = useMemo(() => crypto.randomUUID(), []);
  const chatController = useMemo(
    () =>
      new ChatSessionController({
        conversationId,
        sendTurn: (request) =>
          submitChatTurn({
            conversationId,
            request,
            jsonRequest: (input, init) => authController.authorizedJson(input, init),
          }),
      }),
    [authController, conversationId],
  );

  const [chatView, setChatView] = useState<ChatSessionSnapshot>(chatController.snapshot);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  const searchEnabled = currentUser?.scopes.includes("tool:websearch") ?? false;

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const nextReadiness = await authController.loadReadiness();
      if (cancelled) {
        return;
      }
      setReadiness(nextReadiness.readiness);

      const session = await authController.restoreSession();
      if (cancelled) {
        return;
      }

      setCurrentUser(session.currentUser);
      setAuthMessage(session.globalMessage);
      setIsBootstrapping(false);
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [authController]);

  useEffect(() => {
    if (!searchEnabled && chatView.mode === "search") {
      setChatView(chatController.setMode("direct"));
    }
  }, [chatController, chatView.mode, searchEnabled]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currentUser) {
      setAuthMessage("Phiên của bạn không còn hợp lệ. Vui lòng đăng nhập lại để tiếp tục.");
      return;
    }

    const next = await chatController.submitTurn();
    setChatView(next);
  }

  async function handleRetry(turnId: string) {
    const next = await chatController.retryTurn(turnId);
    setChatView(next);
  }

  function handlePrefillSuggestion(query: string) {
    const next = chatController.prefillSuggestion(query);
    setChatView(next);
    window.setTimeout(() => composerRef.current?.focus(), 0);
  }

  return (
    <main className="chat-page-shell">
      <section className="chat-layout">
        <ConversationHeader
          currentUser={currentUser}
          readiness={readiness}
          searchEnabled={searchEnabled}
        />

        {authMessage ? (
          <InlineAlert tone="warning" title="Cần đăng nhập" message={authMessage} urgent />
        ) : null}

        {chatView.errorMessage ? (
          <InlineAlert tone="danger" title="Không thể gửi lượt hỏi" message={chatView.errorMessage} urgent />
        ) : null}

        {chatView.announcement ? (
          <InlineAlert tone="info" message={chatView.announcement} />
        ) : null}

        {isBootstrapping ? (
          <div className="message-card assistant-message-card">
            <div className="checking-state">
              <span className="spinner" aria-hidden="true" />
              <p className="body-copy">Đang khôi phục phiên trò chuyện an toàn...</p>
            </div>
          </div>
        ) : (
          <MessageThread
            turns={chatView.turns}
            mode={chatView.mode}
            activeRetryId={chatView.activeRetryId}
            onPrefillSuggestion={handlePrefillSuggestion}
            onRetry={handleRetry}
          />
        )}

        <MessageComposer
          draft={chatView.draft}
          mode={chatView.mode}
          submitLabel={chatView.submitLabel}
          disabled={chatView.isPending || !currentUser}
          searchEnabled={searchEnabled}
          textareaRef={composerRef}
          onDraftChange={(draft) => setChatView(chatController.setDraft(draft))}
          onModeChange={(mode) => setChatView(chatController.setMode(mode))}
          onSubmit={handleSubmit}
        />
      </section>
    </main>
  );
}
