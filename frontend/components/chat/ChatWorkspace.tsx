"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { ApiError } from "@/lib/api";
import type { AuthSessionController, CurrentUser } from "@/lib/auth-session";
import {
  createConversationWithMessage,
  deleteConversation,
  getConversation,
  listConversations,
  retryMessage,
  sendMessage,
  undoDeleteConversation,
} from "@/lib/chat-api";
import type {
  ChatMessage,
  ConversationDetail,
  ConversationSummary,
} from "@/lib/chat-types";

import { ChatDrawer } from "./ChatDrawer";
import { ChatMobileBar } from "./ChatMobileBar";
import { ChatSidebar, type ChatNavigationProps } from "./ChatSidebar";
import { ChatThread } from "./ChatThread";
import { UndoToast } from "./UndoToast";

type ChatWorkspaceProps = {
  controller: AuthSessionController;
  currentUser: CurrentUser;
  initialConversation?: ConversationDetail;
  onSessionExpired: () => void;
  onLogout: () => void | Promise<void>;
};

function sortConversations(items: ConversationSummary[]): ConversationSummary[] {
  return [...items].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

export function removeConversationSummary(
  items: ConversationSummary[],
  conversationId: string,
): ConversationSummary[] {
  return items.filter((item) => item.id !== conversationId);
}

export function restoreConversationSummary(
  items: ConversationSummary[],
  restored: ConversationSummary,
): ConversationSummary[] {
  return sortConversations([restored, ...items.filter((item) => item.id !== restored.id)]);
}

function summaryFromDetail(detail: ConversationDetail): ConversationSummary {
  const { messages: _messages, ...summary } = detail;
  return summary;
}

function temporaryMessage(options: {
  conversationId: string;
  id: string;
  role: "user" | "assistant";
  status: "completed" | "pending";
  content: string;
  clientMessageId: string | null;
  sequenceNo: number;
}): ChatMessage {
  return {
    id: options.id,
    conversation_id: options.conversationId,
    sequence_no: options.sequenceNo,
    client_message_id: options.clientMessageId,
    role: options.role,
    status: options.status,
    content: options.content,
    metadata: {},
    created_at: new Date().toISOString(),
  };
}

export function ChatWorkspace({
  controller,
  currentUser,
  initialConversation,
  onSessionExpired,
  onLogout,
}: ChatWorkspaceProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>(
    initialConversation ? [summaryFromDetail(initialConversation)] : [],
  );
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(
    initialConversation ?? null,
  );
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [listLoading, setListLoading] = useState(false);
  const [threadLoading, setThreadLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [sending, setSending] = useState(false);
  const [retryingClientMessageId, setRetryingClientMessageId] = useState<string | null>(null);
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null);
  const [deletedConversationId, setDeletedConversationId] = useState<string | null>(null);
  const [undoingDelete, setUndoingDelete] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [workspaceCorrelationId, setWorkspaceCorrelationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pending = useMemo(
    () =>
      activeConversation?.messages.some(
        (message) => message.role === "assistant" && message.status === "pending",
      ) ?? false,
    [activeConversation],
  );

  const handleApiError = useCallback(
    (error: unknown) => {
      if (controller.snapshot.sessionState === "session_expired") {
        onSessionExpired();
        return;
      }

      setWorkspaceError(
        error instanceof ApiError && error.status >= 500
          ? "The server couldn't complete this request. Try again."
          : "Can't reach the server. Check that the local stack is running and try again.",
      );
      setWorkspaceCorrelationId(error instanceof ApiError ? error.correlationId ?? null : null);
    },
    [controller, onSessionExpired],
  );

  const refreshConversationList = useCallback(
    async (cursor?: string | null) => {
      const page = await listConversations(controller, { cursor: cursor ?? null });
      setConversations((current) =>
        sortConversations(cursor ? [...current, ...page.items] : page.items),
      );
      setNextCursor(page.next_cursor);
      return page.items;
    },
    [controller],
  );

  const clearUndoTimer = useCallback(() => {
    if (undoTimerRef.current) {
      clearTimeout(undoTimerRef.current);
      undoTimerRef.current = null;
    }
  }, []);

  const showUndoToast = useCallback(
    (conversationId: string) => {
      clearUndoTimer();
      setDeletedConversationId(conversationId);
      undoTimerRef.current = setTimeout(() => {
        setDeletedConversationId(null);
        undoTimerRef.current = null;
      }, 6000);
    },
    [clearUndoTimer],
  );

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setListLoading(true);
      try {
        const page = await listConversations(controller);
        if (!cancelled) {
          setConversations(sortConversations(page.items));
          setNextCursor(page.next_cursor);
        }
      } catch (error) {
        if (!cancelled) {
          handleApiError(error);
        }
      } finally {
        if (!cancelled) {
          setListLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [controller, handleApiError]);

  useEffect(() => clearUndoTimer, [clearUndoTimer]);

  async function selectConversation(conversationId: string) {
    setThreadLoading(true);
    setWorkspaceError(null);
    setMobileNavOpen(false);
    try {
      setActiveConversation(await getConversation(controller, conversationId));
    } catch (error) {
      handleApiError(error);
    } finally {
      setThreadLoading(false);
    }
  }

  function startNewChat() {
    setActiveConversation(null);
    setDraft("");
    setWorkspaceError(null);
    setWorkspaceCorrelationId(null);
    setMobileNavOpen(false);
  }

  async function loadMoreConversations() {
    if (!nextCursor || loadingMore) {
      return;
    }
    setLoadingMore(true);
    try {
      await refreshConversationList(nextCursor);
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoadingMore(false);
    }
  }

  async function deleteVisibleConversation(conversationId: string) {
    setDeletingConversationId(conversationId);
    setWorkspaceError(null);
    try {
      await deleteConversation(controller, conversationId);
      setConversations((current) => removeConversationSummary(current, conversationId));
      if (activeConversation?.id === conversationId) {
        setActiveConversation(null);
      }
      setMobileNavOpen(false);
      showUndoToast(conversationId);
    } catch (error) {
      handleApiError(error);
    } finally {
      setDeletingConversationId(null);
    }
  }

  async function undoDeletedConversation() {
    if (!deletedConversationId || undoingDelete) {
      return;
    }
    const conversationId = deletedConversationId;
    setUndoingDelete(true);
    try {
      const restored = await undoDeleteConversation(controller, conversationId);
      setConversations((current) => restoreConversationSummary(current, restored));
      setDeletedConversationId(null);
      clearUndoTimer();
    } catch (error) {
      handleApiError(error);
    } finally {
      setUndoingDelete(false);
    }
  }

  async function recoverPersistedFailure(
    conversationId: string | null,
  ): Promise<ConversationDetail | null> {
    try {
      if (conversationId) {
        const detail = await getConversation(controller, conversationId);
        setActiveConversation(detail);
        setConversations((current) =>
          sortConversations([
            summaryFromDetail(detail),
            ...current.filter((item) => item.id !== detail.id),
          ]),
        );
        return detail;
      }

      const latest = await refreshConversationList();
      if (latest[0]) {
        const detail = await getConversation(controller, latest[0].id);
        setActiveConversation(detail);
        return detail;
      }
    } catch (reloadError) {
      handleApiError(reloadError);
    }
    return null;
  }

  async function submitMessage() {
    const content = draft.trim();
    if (!content || pending || sending) {
      return;
    }

    const clientMessageId = crypto.randomUUID();
    const conversationId = activeConversation?.id ?? null;
    const previousConversation = activeConversation;
    setSending(true);
    setWorkspaceError(null);
    setWorkspaceCorrelationId(null);

    if (activeConversation) {
      const nextSequence = activeConversation.messages.length
        ? Math.max(...activeConversation.messages.map((message) => message.sequence_no)) + 1
        : 1;
      setActiveConversation({
        ...activeConversation,
        messages: [
          ...activeConversation.messages,
          temporaryMessage({
            conversationId: activeConversation.id,
            id: `optimistic-user-${clientMessageId}`,
            role: "user",
            status: "completed",
            content,
            clientMessageId,
            sequenceNo: nextSequence,
          }),
          temporaryMessage({
            conversationId: activeConversation.id,
            id: `optimistic-assistant-${clientMessageId}`,
            role: "assistant",
            status: "pending",
            content: "",
            clientMessageId,
            sequenceNo: nextSequence + 1,
          }),
        ],
      });
    }

    try {
      const detail = conversationId
        ? await sendMessage(controller, conversationId, { clientMessageId, content })
        : await createConversationWithMessage(controller, { clientMessageId, content });
      setActiveConversation(detail);
      setConversations((current) =>
        sortConversations([
          summaryFromDetail(detail),
          ...current.filter((item) => item.id !== detail.id),
        ]),
      );
      setDraft("");
    } catch (error) {
      if (error instanceof ApiError && error.code === "provider_failed") {
        setDraft("");
        await recoverPersistedFailure(conversationId);
      } else {
        setActiveConversation(previousConversation);
        handleApiError(error);
      }
    } finally {
      setSending(false);
    }
  }

  async function retryFailedMessage(clientMessageId: string) {
    if (!activeConversation || retryingClientMessageId) {
      return;
    }

    const conversationId = activeConversation.id;
    setRetryingClientMessageId(clientMessageId);
    setWorkspaceError(null);
    setActiveConversation({
      ...activeConversation,
      messages: activeConversation.messages.map((message) =>
        message.role === "assistant" &&
        message.status === "failed" &&
        (message.client_message_id === clientMessageId ||
          message.metadata.correlation_id !== undefined)
          ? { ...message, status: "pending", metadata: {} }
          : message,
      ),
    });

    try {
      const detail = await retryMessage(controller, conversationId, clientMessageId);
      setActiveConversation(detail);
      setConversations((current) =>
        sortConversations([
          summaryFromDetail(detail),
          ...current.filter((item) => item.id !== detail.id),
        ]),
      );
    } catch (error) {
      if (error instanceof ApiError && error.code === "provider_failed") {
        await recoverPersistedFailure(conversationId);
      } else {
        handleApiError(error);
        await recoverPersistedFailure(conversationId);
      }
    } finally {
      setRetryingClientMessageId(null);
    }
  }

  const navigationProps: ChatNavigationProps = {
    conversations,
    activeConversationId: activeConversation?.id ?? null,
    currentUserEmail: currentUser.email,
    nextCursor,
    loading: listLoading,
    loadingMore,
    deletingConversationId,
    onNewChat: startNewChat,
    onSelectConversation: (conversationId) => void selectConversation(conversationId),
    onLoadMore: () => void loadMoreConversations(),
    onDeleteConversation: (conversationId) => void deleteVisibleConversation(conversationId),
    onSignOut: onLogout,
  };

  return (
    <main
      className={`chat-workspace ${sidebarOpen ? "" : "chat-workspace-sidebar-collapsed"}`}
    >
      <a className="skip-link" href="#chat-content">Skip to chat</a>
      <aside
        className={`conversation-navigation ${sidebarOpen ? "" : "conversation-navigation-collapsed"}`}
        aria-label="Conversation navigation"
      >
        <ChatSidebar {...navigationProps} />
        <button
          className="sidebar-toggle"
          type="button"
          aria-label="Collapse conversation navigation"
          onClick={() => setSidebarOpen(false)}
        >
          <PanelLeftClose aria-hidden="true" size={18} />
        </button>
      </aside>
      {!sidebarOpen ? (
        <button
          className="sidebar-expand"
          type="button"
          aria-label="Expand conversation navigation"
          onClick={() => setSidebarOpen(true)}
        >
          <PanelLeftOpen aria-hidden="true" size={19} />
        </button>
      ) : null}
      <ChatMobileBar
        onOpenNavigation={() => setMobileNavOpen(true)}
        onNewChat={startNewChat}
      />
      <ChatDrawer
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        navigationProps={navigationProps}
      />
      <section className="chat-main" id="chat-content">
        {workspaceError ? (
          <div className="workspace-error" role="alert">
            <p>{workspaceError}</p>
            {workspaceCorrelationId ? (
              <code>Reference code: {workspaceCorrelationId}</code>
            ) : null}
          </div>
        ) : null}
        <ChatThread
          conversation={activeConversation}
          draft={draft}
          loading={threadLoading}
          pending={pending || sending}
          submitting={sending}
          retryingClientMessageId={retryingClientMessageId}
          onDraftChange={setDraft}
          onSubmit={submitMessage}
          onRetry={(clientMessageId) => void retryFailedMessage(clientMessageId)}
        />
        <UndoToast
          visible={deletedConversationId !== null}
          undoing={undoingDelete}
          onUndo={undoDeletedConversation}
        />
      </section>
    </main>
  );
}
