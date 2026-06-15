"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  getOrchestrationSettings,
  setTrustedSupervisorEnabled,
} from "@/lib/admin-api";
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

import { ActionButton } from "@/components/account-access/ActionButton";
import { StatusBadge } from "@/components/account-access/StatusBadge";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatDrawer } from "./ChatDrawer";
import { ChatMobileBar } from "./ChatMobileBar";
import { ChatSidebar, type AppWorkspaceView, type ChatNavigationProps } from "./ChatSidebar";
import { ChatThread } from "./ChatThread";
import { UndoToast } from "./UndoToast";
import { SettingsPage } from "@/components/settings/SettingsPage";

type AdminOrchestrationSettings = {
  trustedSupervisorEnabled: boolean;
};

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

function formatCount(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

const ADMIN_VIEW_META: Record<
  Exclude<AppWorkspaceView, "chat">,
  { title: string; description: string }
> = {
  overview: {
    title: "Overview",
    description: "Review account activity, granted scopes, and current safety boundaries.",
  },
  users: {
    title: "Users",
    description: "Inspect the signed-in account and authorization shape available in this session.",
  },
  "security-events": {
    title: "Security events",
    description: "Review security evidence when backend event data is available.",
  },
  "tool-executions": {
    title: "Tool executions",
    description: "Review Search and Python execution evidence when tool telemetry is available.",
  },
  "gateway-evidence": {
    title: "Gateway evidence",
    description: "Review gateway rate-limit and correlation evidence when it is available.",
  },
  orchestration: {
    title: "Orchestration",
    description: "Review the trusted supervisor boundary for controlled Python turns.",
  },
  settings: {
    title: "Settings",
    description: "Manage account details, tool availability, and administrative controls.",
  },
};

function AdminMetricCard(props: {
  label: string;
  value: string;
  help: string;
  badge: string;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  return (
    <Card className="admin-metric-card">
      <div className="metric-row">
        <p className="metric-label">{props.label}</p>
        <StatusBadge tone={props.tone ?? "neutral"}>{props.badge}</StatusBadge>
      </div>
      <p className="metric-value">{props.value}</p>
      <p className="metric-help">{props.help}</p>
    </Card>
  );
}

function EmptyAdminState(props: { title: string; body: string }) {
  return (
    <Card className="admin-empty-card">
      <h2 className="card-title">{props.title}</h2>
      <p className="body-copy">{props.body}</p>
    </Card>
  );
}

function OverviewView(props: { conversations: ConversationSummary[]; currentUser: CurrentUser; adminSettings: AdminOrchestrationSettings | null }) {
  const adminScopeCount = props.currentUser.scopes.filter((scope) => scope.startsWith("admin:")).length;

  return (
    <div className="admin-layout">
      <section className="metrics-grid">
        <AdminMetricCard label="Active conversations" value={formatCount(props.conversations.length)} help="Recent workspace activity visible in this browser session." badge="Session" />
        <AdminMetricCard label="Granted scopes" value={formatCount(props.currentUser.scopes.length)} help="Current signed-in scope set for the protected account." badge="Token" tone="success" />
        <AdminMetricCard label="Admin scopes" value={formatCount(adminScopeCount)} help="Administrative capabilities currently available to this user." badge="Token" tone={adminScopeCount > 0 ? "warning" : "neutral"} />
        <AdminMetricCard label="Trusted supervisor" value={props.adminSettings?.trustedSupervisorEnabled ? "On" : "Off"} help="Python guardrail orchestration status returned by the backend." badge={props.adminSettings ? "Backend" : "Unavailable"} tone={props.adminSettings?.trustedSupervisorEnabled ? "success" : "warning"} />
        <AdminMetricCard label="Evidence references" value="Correlation-aware" help="Operational surfaces preserve correlation references for support and audit review." badge="Derived" />
        <AdminMetricCard label="Gateway evidence" value="Not connected" help="Gateway evidence is hidden from navigation until backend data is available." badge="Unavailable" />
      </section>
      <Card className="admin-card">
        <div className="admin-card-copy">
          <p className="small-label">Admin overview</p>
          <h2 className="card-title">Security and operations at a glance</h2>
        </div>
        <p className="body-copy">
          Use this area to inspect the current session, authorization boundaries, security evidence, and administrative settings without mixing them into chat.
        </p>
      </Card>
    </div>
  );
}

function UsersView(props: { currentUser: CurrentUser }) {
  return (
    <div className="admin-layout">
      <Card className="admin-table-card">
        <div className="admin-card-copy">
          <p className="small-label">Users</p>
          <h2 className="card-title">Protected account summary</h2>
        </div>
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Scopes</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              <tr className="admin-table-row">
                <td>{props.currentUser.email}</td>
                <td>{props.currentUser.role}</td>
                <td>{props.currentUser.scopes.join(", ")}</td>
                <td>{props.currentUser.is_active ? "Active" : "Inactive"}</td>
                <td>Available from backend admin endpoints</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="admin-mobile-list">
          <div className="admin-row">
            <strong>{props.currentUser.email}</strong>
            <span className="row-meta">Role: {props.currentUser.role}</span>
            <span className="row-meta">Scopes: {props.currentUser.scopes.join(", ")}</span>
          </div>
        </div>
      </Card>
      <EmptyAdminState title="User directory unavailable" body="Only the signed-in account is available in this local workspace. Directory paging is hidden until backend data is connected." />
    </div>
  );
}

function SecurityEventsView() {
  return (
    <div className="admin-layout">
      <Card className="admin-card">
        <div className="admin-card-copy">
          <p className="small-label">Security events</p>
          <h2 className="card-title">Filterable evidence shell</h2>
        </div>
        <div className="admin-filter-pill-row">
          {[
            "All",
            "Failed sign-ins",
            "Access denied",
            "Refresh replay",
            "429 / rate limit",
            "Python / sandbox",
            "Google Search",
          ].map((label, index) => (
            <button className={`filter-pill ${index === 0 ? "filter-pill-active" : ""}`} key={label} type="button">
              {label}
            </button>
          ))}
        </div>
      </Card>
      <EmptyAdminState title="No security events loaded" body="Security evidence will appear here when the backend returns event rows for this local stack." />
    </div>
  );
}

function ToolExecutionsView() {
  return (
    <div className="admin-layout">
      <EmptyAdminState title="Tool execution evidence unavailable" body="Search and Python execution summaries will appear here after telemetry data is connected." />
    </div>
  );
}

function GatewayEvidenceView() {
  return (
    <div className="admin-layout">
      <Card className="admin-card">
        <div className="admin-card-copy">
          <p className="small-label">Gateway evidence</p>
          <h2 className="card-title">Rate-limit and correlation evidence</h2>
        </div>
        <p className="body-copy">
          Gateway evidence is not connected in this local workspace. This page avoids fake telemetry and stays out of primary navigation until real data is available.
        </p>
      </Card>
    </div>
  );
}

function OrchestrationView(props: {
  adminSettings: AdminOrchestrationSettings | null;
  onOpenSettings: () => void;
}) {
  return (
    <div className="admin-layout">
      <Card className="admin-card">
        <div className="topbar-row">
          <div className="admin-card-copy">
            <p className="small-label">Orchestration</p>
            <h2 className="card-title">Trusted supervisor boundary</h2>
          </div>
          <StatusBadge tone={props.adminSettings?.trustedSupervisorEnabled ? "success" : "warning"}>
            {props.adminSettings?.trustedSupervisorEnabled ? "Enabled" : "Disabled"}
          </StatusBadge>
        </div>
        <p className="body-copy">
          Trusted supervisor changes now live in Settings so chat, navigation, and administration keep separate responsibilities.
        </p>
        <div className="admin-card-actions">
          <ActionButton type="button" variant="secondary" fullWidth={false} onClick={props.onOpenSettings}>
            Open Settings
          </ActionButton>
        </div>
      </Card>
    </div>
  );
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
  const [adminSettings, setAdminSettings] = useState<AdminOrchestrationSettings | null>(null);
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [workspaceView, setWorkspaceView] = useState<AppWorkspaceView>("chat");
  const [toolMode, setToolMode] = useState<"auto" | "google_search" | "python">("auto");
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pending = useMemo(
    () =>
      activeConversation?.messages.some(
        (message) => message.role === "assistant" && message.status === "pending",
      ) ?? false,
    [activeConversation],
  );
  const adminCanRead = currentUser.scopes.includes("admin:read");
  const adminCanWrite = currentUser.scopes.includes("admin:write");
  const searchEnabled = currentUser.scopes.includes("tool:websearch");

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

  useEffect(() => {
    let cancelled = false;

    async function loadAdminSettings() {
      if (!adminCanRead) {
        setAdminSettings(null);
        setAdminError(null);
        return;
      }
      try {
        const response = await getOrchestrationSettings(controller);
        if (!cancelled) {
          setAdminSettings({
            trustedSupervisorEnabled: response.trusted_supervisor_enabled,
          });
          setAdminError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setAdminSettings(null);
          setAdminError(
            error instanceof ApiError
              ? error.message
              : "Can't load admin orchestration settings right now.",
          );
        }
      }
    }

    void loadAdminSettings();
    return () => {
      cancelled = true;
    };
  }, [adminCanRead, controller]);

  useEffect(() => {
    if (toolMode === "google_search" && !searchEnabled) {
      setToolMode("auto");
    }
  }, [searchEnabled, toolMode]);

  async function selectConversation(conversationId: string) {
    setThreadLoading(true);
    setWorkspaceError(null);
    setMobileNavOpen(false);
    setWorkspaceView("chat");
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
    setWorkspaceView("chat");
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
        ? await sendMessage(controller, conversationId, {
            clientMessageId,
            content,
            toolMode,
          })
        : await createConversationWithMessage(controller, {
            clientMessageId,
            content,
            toolMode,
          });
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

  async function updateTrustedSupervisor(enabled: boolean) {
    if (!adminCanWrite) {
      return;
    }
    setAdminBusy(true);
    setAdminError(null);
    try {
      const response = await setTrustedSupervisorEnabled(controller, enabled);
      setAdminSettings({
        trustedSupervisorEnabled: response.trusted_supervisor_enabled,
      });
    } catch (error) {
      setAdminError(
        error instanceof ApiError
          ? error.message
          : "Can't update trusted supervisor setting right now.",
      );
    } finally {
      setAdminBusy(false);
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
    adminCanRead,
    adminError,
    collapsed: !sidebarOpen,
    currentView: workspaceView,
    onNewChat: startNewChat,
    onSelectConversation: (conversationId) => void selectConversation(conversationId),
    onSelectView: setWorkspaceView,
    onLoadMore: () => void loadMoreConversations(),
    onDeleteConversation: (conversationId) => void deleteVisibleConversation(conversationId),
    onSignOut: onLogout,
    onToggleCollapse: () => setSidebarOpen((current) => !current),
  };

  function renderWorkspaceView() {
    if (!adminCanRead && workspaceView !== "chat") {
      return (
        <div className="admin-layout">
          <EmptyAdminState title="Access denied" body="This account does not have permission to view administrative surfaces." />
        </div>
      );
    }

    switch (workspaceView) {
      case "overview":
        return <OverviewView adminSettings={adminSettings} conversations={conversations} currentUser={currentUser} />;
      case "users":
        return <UsersView currentUser={currentUser} />;
      case "security-events":
        return <SecurityEventsView />;
      case "tool-executions":
        return <ToolExecutionsView />;
      case "gateway-evidence":
        return <GatewayEvidenceView />;
      case "orchestration":
        return (
          <OrchestrationView
            adminSettings={adminSettings}
            onOpenSettings={() => setWorkspaceView("settings")}
          />
        );
      case "settings":
        return (
          <SettingsPage
            currentUser={currentUser}
            adminSettings={adminSettings}
            adminCanWrite={adminCanWrite}
            adminBusy={adminBusy}
            adminError={adminError}
            searchEnabled={searchEnabled}
            onTrustedSupervisorToggle={(enabled) => void updateTrustedSupervisor(enabled)}
          />
        );
      case "chat":
      default:
        return (
          <ChatThread
            conversation={activeConversation}
            draft={draft}
            loading={threadLoading}
            pending={pending || sending}
            retryingClientMessageId={retryingClientMessageId}
            searchEnabled={searchEnabled}
            submitting={sending}
            toolMode={toolMode}
            onDraftChange={setDraft}
            onRetry={(clientMessageId) => void retryFailedMessage(clientMessageId)}
            onSubmit={submitMessage}
            onToolModeChange={setToolMode}
          />
        );
    }
  }

  return (
    <div className="flex h-[100dvh] min-h-[100dvh] w-full flex-col overflow-hidden bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 md:flex-row">
      <div className="hidden h-full shrink-0 md:flex">
        <ChatSidebar {...navigationProps} />
      </div>
      <ChatMobileBar
        onOpenNavigation={() => setMobileNavOpen(true)}
        onNewChat={startNewChat}
      />
      <ChatDrawer
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        navigationProps={navigationProps}
      />
      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden" id="workspace-content" tabIndex={-1}>
        {workspaceError ? (
          <div className="p-4 m-4 bg-red-100 border border-red-200 text-red-900 rounded-lg" role="alert">
            <p>{workspaceError}</p>
            {workspaceCorrelationId ? (
              <code className="text-sm">Reference code: {workspaceCorrelationId}</code>
            ) : null}
          </div>
        ) : null}

        {workspaceView === "chat" ? (
          <ChatThread
            conversation={activeConversation}
            draft={draft}
            loading={threadLoading}
            pending={pending || sending}
            retryingClientMessageId={retryingClientMessageId}
            searchEnabled={searchEnabled}
            submitting={sending}
            toolMode={toolMode}
            onDraftChange={setDraft}
            onRetry={(clientMessageId) => void retryFailedMessage(clientMessageId)}
            onSubmit={submitMessage}
            onToolModeChange={setToolMode}
          />
        ) : (
          <div className="flex flex-col h-full bg-white dark:bg-zinc-900">
            <header className="border-b border-zinc-200/60 px-6 py-8 dark:border-zinc-800">
              <div className="max-w-3xl mx-auto w-full">
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-2">Administration</p>
                <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
                  {ADMIN_VIEW_META[workspaceView as Exclude<AppWorkspaceView, "chat">].title}
                </h2>
                <p className="text-zinc-600 dark:text-zinc-400">
                  {ADMIN_VIEW_META[workspaceView as Exclude<AppWorkspaceView, "chat">].description}
                </p>
              </div>
            </header>
            <ScrollArea className="flex-1 px-6 py-6">
              <div className="max-w-3xl mx-auto w-full">
                {renderWorkspaceView()}
              </div>
            </ScrollArea>
          </div>
        )}

        <UndoToast
          visible={deletedConversationId !== null}
          undoing={undoingDelete}
          onUndo={undoDeletedConversation}
        />
      </main>
    </div>
  );
}
