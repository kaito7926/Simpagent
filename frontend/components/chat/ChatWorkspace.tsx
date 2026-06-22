"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  getAdminUsers,
  getGatewayEvidence,
  getAdminMetrics,
  getOrchestrationSettings,
  getSecurityEvents,
  getToolExecutions,
  setGuardrailSafetyEnabled,
} from "@/lib/admin-api";
import type {
  AdminMetricsResponse,
  AdminUsersPage,
  GatewayEvidencePage,
  SecurityEventsPage,
  ToolExecutionsPage,
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
import { EvidenceDetailDrawer } from "@/components/admin/EvidenceDetailDrawer";
import { EvidenceTable, type EvidenceRow } from "@/components/admin/EvidenceTable";
import { StatePanel } from "@/components/admin/StatePanel";

type AdminOrchestrationSettings = {
  guardrailSafetyEnabled: boolean;
};

type ChatWorkspaceProps = {
  controller: AuthSessionController;
  currentUser: CurrentUser;
  initialConversation?: ConversationDetail;
  initialView?: AppWorkspaceView;
  initialAdminMetrics?: AdminMetricsResponse | null;
  initialAdminPages?: Partial<AdminEvidencePages>;
  onSessionExpired: () => void;
  onLogout: () => void | Promise<void>;
};

type AdminEvidencePages = {
  users: AdminUsersPage | null;
  securityEvents: SecurityEventsPage | null;
  toolExecutions: ToolExecutionsPage | null;
  gatewayEvidence: GatewayEvidencePage | null;
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

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function userRows(page: AdminUsersPage | null): EvidenceRow[] {
  return (
    page?.items.map((item) => ({
      id: item.id,
      primary: item.email,
      secondary: `${item.role} account with ${item.scopes.length} scopes`,
      status: item.is_active ? "active" : "inactive",
      correlationId: null,
      fields: {
        Email: item.email,
        Role: item.role,
        Scopes: item.scopes.join(", "),
        Status: item.is_active ? "Active" : "Inactive",
        Created: formatDateTime(item.created_at),
        Actions: item.is_demo ? "Demo account" : "Managed account",
      },
      snippets: [
        {
          kind: "user",
          text: `role=${item.role} active=${item.is_active} demo=${item.is_demo} scopes=${item.scopes.join(",")}`,
          truncated: false,
        },
      ],
    })) ?? []
  );
}

function securityEventRows(page: SecurityEventsPage | null): EvidenceRow[] {
  return (
    page?.items.map((item) => ({
      id: item.id,
      primary: item.event_type,
      secondary: item.description,
      status: item.severity,
      correlationId: item.correlation_id,
      fields: {
        "Event type": item.event_type,
        Severity: item.severity,
        User: item.user_id ?? "Unknown",
        Description: item.description,
        "Correlation ID": item.correlation_id ?? "None",
        Time: formatDateTime(item.created_at),
      },
      snippets: item.snippets,
    })) ?? []
  );
}

function toolExecutionRows(page: ToolExecutionsPage | null): EvidenceRow[] {
  return (
    page?.items.map((item) => ({
      id: item.id,
      primary: item.tool_name,
      secondary: item.input_summary,
      status: item.status,
      correlationId: item.correlation_id,
      fields: {
        Tool: item.tool_name,
        Status: item.status,
        User: item.user_id,
        Conversation: item.conversation_id ?? "None",
        "Input summary": item.input_summary,
        "Output summary": item.output_summary ?? "No output summary",
        Duration: item.duration_ms === null ? "Unknown" : `${item.duration_ms} ms`,
        "Correlation ID": item.correlation_id ?? "None",
        Time: formatDateTime(item.created_at),
      },
      snippets: item.snippets,
    })) ?? []
  );
}

function gatewayEvidenceRows(page: GatewayEvidencePage | null): EvidenceRow[] {
  return (
    page?.items.map((item) => ({
      id: item.id,
      primary: item.summary,
      secondary: `${item.source} via ${item.plugin}`,
      status: item.evidence_type,
      correlationId: null,
      fields: {
        Type: item.evidence_type,
        Source: item.source,
        Route: item.route ?? "Global",
        Plugin: item.plugin,
        "Status codes": item.status_codes.length ? item.status_codes.join(", ") : "Config evidence",
        Summary: item.summary,
      },
      snippets: item.snippets,
    })) ?? []
  );
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
    description: "Review the current safety controls for guarded tool orchestration.",
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

function OverviewView(props: {
  metrics: AdminMetricsResponse | null;
  adminSettings: AdminOrchestrationSettings | null;
}) {
  const last24hTotal =
    (props.metrics?.security_events_last_24h ?? 0) +
    (props.metrics?.tool_executions_last_24h ?? 0);

  return (
    <div className="admin-layout">
      <section className="metrics-grid">
        <AdminMetricCard
          label="Active users"
          value={formatCount(props.metrics?.users_active ?? 0)}
          help={`Out of ${formatCount(props.metrics?.users_total ?? 0)} total accounts.`}
          badge="Backend"
          tone="success"
        />
        <AdminMetricCard
          label="Security events"
          value={formatCount(props.metrics?.security_events_total ?? 0)}
          help={`${formatCount(props.metrics?.security_events_last_24h ?? 0)} events in the last 24 hours.`}
          badge="Aggregate"
          tone="warning"
        />
        <AdminMetricCard
          label="Tool executions"
          value={formatCount(props.metrics?.tool_executions_total ?? 0)}
          help={`${formatCount(props.metrics?.tool_executions_last_24h ?? 0)} tool runs in the last 24 hours.`}
          badge="Aggregate"
        />
        <AdminMetricCard
          label="Last 24 hours"
          value={formatCount(last24hTotal)}
          help="Combined security-event and tool-execution activity in the current window."
          badge="24h"
        />
        <AdminMetricCard
          label="Valid correlation references"
          value={formatCount(props.metrics?.correlation_references_total ?? 0)}
          help="Evidence rows that can be traced by reference code without exposing raw content."
          badge="Audit"
          tone="success"
        />
        <AdminMetricCard
          label="429 / rate limit"
          value={formatCount(props.metrics?.rate_limit_events_total ?? 0)}
          help="Gateway or backend rate-limit evidence represented as aggregate counts."
          badge="Bounded"
          tone={props.metrics?.rate_limit_events_total ? "warning" : "neutral"}
        />
      </section>
      <Card className="admin-card">
        <div className="admin-card-copy">
          <p className="small-label">Admin overview</p>
          <h2 className="card-title">Security overview</h2>
        </div>
        <p className="body-copy">
          Metrics are loaded from the backend admin evidence contract and stay limited to bounded aggregate counts.
          Guardrail safety is {props.adminSettings?.guardrailSafetyEnabled ? "enabled" : "disabled"}.
        </p>
      </Card>
    </div>
  );
}

function UsersView(props: {
  page: AdminUsersPage | null;
  adminCanWrite: boolean;
  selectedRow: EvidenceRow | null;
  onSelectRow: (row: EvidenceRow) => void;
  onCloseDrawer: () => void;
}) {
  const rows = userRows(props.page);
  return (
    <div className="admin-layout">
      {!props.adminCanWrite ? (
        <StatePanel
          state="empty"
          title="Read-only admin access"
          body="This account can inspect bounded user evidence, but backend admin:write is required for role or status changes."
        />
      ) : null}
      <EvidenceTable
        title="Users"
        description="Backend-paged accounts with role, scope, and status evidence."
        emptyTitle="No users match the current filter."
        rows={rows}
        page={props.page?.page}
        desktopMinWidth={1280}
        importantFields={["Email", "Role", "Status"]}
        onSelectRow={props.onSelectRow}
      />
      <EvidenceDetailDrawer
        open={props.selectedRow !== null}
        title="User details"
        description="Backend-sanitized user evidence fields."
        row={props.selectedRow}
        onOpenChange={(open) => {
          if (!open) props.onCloseDrawer();
        }}
      />
    </div>
  );
}

function SecurityEventsView(props: {
  page: SecurityEventsPage | null;
  selectedRow: EvidenceRow | null;
  onSelectRow: (row: EvidenceRow) => void;
  onCloseDrawer: () => void;
}) {
  const rows = securityEventRows(props.page);
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
      <EvidenceTable
        title="Security events"
        description="Bounded event evidence from the backend security log."
        emptyTitle="No evidence matches the current filter."
        rows={rows}
        page={props.page?.page}
        onSelectRow={props.onSelectRow}
      />
      <EvidenceDetailDrawer
        open={props.selectedRow !== null}
        title="Security event details"
        description="Backend-sanitized snippets only."
        row={props.selectedRow}
        onOpenChange={(open) => {
          if (!open) props.onCloseDrawer();
        }}
      />
    </div>
  );
}

function ToolExecutionsView(props: {
  page: ToolExecutionsPage | null;
  selectedRow: EvidenceRow | null;
  onSelectRow: (row: EvidenceRow) => void;
  onCloseDrawer: () => void;
}) {
  const rows = toolExecutionRows(props.page);
  return (
    <div className="admin-layout">
      <EvidenceTable
        title="Tool executions"
        description="Search and Python tool summaries with bounded snippets and durations."
        emptyTitle="No evidence matches the current filter."
        rows={rows}
        page={props.page?.page}
        desktopMinWidth={1760}
        importantFields={["Tool", "Status", "Input summary", "Output summary"]}
        onSelectRow={props.onSelectRow}
      />
      <EvidenceDetailDrawer
        open={props.selectedRow !== null}
        title="Tool execution details"
        description="Backend-sanitized input and output summaries only."
        row={props.selectedRow}
        onOpenChange={(open) => {
          if (!open) props.onCloseDrawer();
        }}
      />
    </div>
  );
}

function GatewayEvidenceView(props: {
  page: GatewayEvidencePage | null;
  selectedRow: EvidenceRow | null;
  onSelectRow: (row: EvidenceRow) => void;
  onCloseDrawer: () => void;
}) {
  const rows = gatewayEvidenceRows(props.page);
  return (
    <div className="admin-layout">
      <section className="metrics-grid">
        <AdminMetricCard
          label="Rate-limit routes"
          value={formatCount(props.page?.summary.rate_limit_routes ?? 0)}
          help="Kong routes protected by local rate limiting."
          badge="429"
          tone="warning"
        />
        <AdminMetricCard
          label="Request-size routes"
          value={formatCount(props.page?.summary.request_size_routes ?? 0)}
          help="Kong routes protected by request-size limiting."
          badge="413"
          tone="warning"
        />
        <AdminMetricCard
          label="Correlation ID"
          value={props.page?.summary.correlation_id_enabled ? "Enabled" : "Missing"}
          help="Kong injects or echoes X-Correlation-Id."
          badge="Kong"
          tone={props.page?.summary.correlation_id_enabled ? "success" : "danger"}
        />
      </section>
      <EvidenceTable
        title="Gateway evidence"
        description="Kong-backed route, rate-limit, request-size, and correlation evidence."
        emptyTitle="No evidence matches the current filter."
        rows={rows}
        page={props.page?.page}
        desktopMinWidth={1280}
        importantFields={["Type", "Route", "Plugin", "Status codes"]}
        onSelectRow={props.onSelectRow}
      />
      <EvidenceDetailDrawer
        open={props.selectedRow !== null}
        title="Gateway evidence details"
        description="Backend-sanitized Kong evidence snippets only."
        row={props.selectedRow}
        onOpenChange={(open) => {
          if (!open) props.onCloseDrawer();
        }}
      />
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
            <h2 className="card-title">Agent orchestration controls</h2>
          </div>
          <StatusBadge tone={props.adminSettings ? "success" : "warning"}>
            {props.adminSettings ? "Backend state" : "Loading"}
          </StatusBadge>
        </div>
        <p className="body-copy">
          Review the safety controls that decide whether guarded tool orchestration can proceed. Changes require administrator write scope and destructive disables are confirmed in Settings.
        </p>
        <div className="scope-list">
          <div className="scope-list-item">
            <span className="scope-label">Guardrail safety</span>
            <BadgeLikeStatus enabled={props.adminSettings?.guardrailSafetyEnabled ?? false} />
            <span className="scope-code">One layer of safety checks before tool orchestration.</span>
          </div>
        </div>
        <div className="admin-card-actions">
          <ActionButton type="button" variant="secondary" fullWidth={false} onClick={props.onOpenSettings}>
            Open Settings
          </ActionButton>
        </div>
      </Card>
    </div>
  );
}

function BadgeLikeStatus(props: { enabled: boolean }) {
  return (
    <StatusBadge tone={props.enabled ? "success" : "warning"}>
      {props.enabled ? "Enabled" : "Disabled"}
    </StatusBadge>
  );
}

export function ChatWorkspace({
  controller,
  currentUser,
  initialConversation,
  initialView = "chat",
  initialAdminMetrics = null,
  initialAdminPages,
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
  const [adminMetrics, setAdminMetrics] = useState<AdminMetricsResponse | null>(initialAdminMetrics);
  const [adminPages, setAdminPages] = useState<AdminEvidencePages>({
    users: initialAdminPages?.users ?? null,
    securityEvents: initialAdminPages?.securityEvents ?? null,
    toolExecutions: initialAdminPages?.toolExecutions ?? null,
    gatewayEvidence: initialAdminPages?.gatewayEvidence ?? null,
  });
  const [adminSettings, setAdminSettings] = useState<AdminOrchestrationSettings | null>(null);
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [selectedEvidenceRow, setSelectedEvidenceRow] = useState<EvidenceRow | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [workspaceView, setWorkspaceView] = useState<AppWorkspaceView>(initialView);
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

    async function loadAdminState() {
      if (!adminCanRead) {
        setAdminMetrics(null);
        setAdminPages({
          users: null,
          securityEvents: null,
          toolExecutions: null,
          gatewayEvidence: null,
        });
        setAdminSettings(null);
        setAdminError(null);
        return;
      }
      try {
        const [
          metricsResponse,
          usersResponse,
          securityEventsResponse,
          toolExecutionsResponse,
          gatewayEvidenceResponse,
          orchestrationResponse,
        ] = await Promise.all([
          getAdminMetrics(controller),
          getAdminUsers(controller, { limit: 25, offset: 0 }),
          getSecurityEvents(controller, { limit: 25, offset: 0 }),
          getToolExecutions(controller, { limit: 25, offset: 0 }),
          getGatewayEvidence(controller, { limit: 25, offset: 0 }),
          getOrchestrationSettings(controller),
        ]);
        if (!cancelled) {
          setAdminMetrics(metricsResponse);
          setAdminPages({
            users: usersResponse,
            securityEvents: securityEventsResponse,
            toolExecutions: toolExecutionsResponse,
            gatewayEvidence: gatewayEvidenceResponse,
          });
          setAdminSettings({
            guardrailSafetyEnabled: orchestrationResponse.guardrail_safety_enabled,
          });
          setAdminError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setAdminMetrics(null);
          setAdminPages({
            users: null,
            securityEvents: null,
            toolExecutions: null,
            gatewayEvidence: null,
          });
          setAdminSettings(null);
          setAdminError(
            error instanceof ApiError
              ? error.message
              : "Can't load admin overview and orchestration settings right now.",
          );
        }
      }
    }

    void loadAdminState();
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

  async function updateGuardrailSafety(enabled: boolean) {
    if (!adminCanWrite) {
      return;
    }
    setAdminBusy(true);
    setAdminError(null);
    try {
      const response = await setGuardrailSafetyEnabled(controller, enabled);
      setAdminSettings({
        guardrailSafetyEnabled: response.guardrail_safety_enabled,
      });
    } catch (error) {
      setAdminError(
        error instanceof ApiError
          ? error.message
          : "Can't update guardrail safety setting right now.",
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
    onSelectView: (view) => {
      setSelectedEvidenceRow(null);
      setWorkspaceView(view);
    },
    onLoadMore: () => void loadMoreConversations(),
    onDeleteConversation: (conversationId) => void deleteVisibleConversation(conversationId),
    onSignOut: onLogout,
    onToggleCollapse: () => setSidebarOpen((current) => !current),
  };

  function renderWorkspaceView() {
    if (!adminCanRead && workspaceView !== "chat") {
      return (
        <div className="admin-layout">
          <StatePanel
            state="forbidden"
            title="You do not have permission to view this area."
            body="Use an account with the required access or contact an administrator."
          />
        </div>
      );
    }

    switch (workspaceView) {
      case "overview":
        return <OverviewView adminSettings={adminSettings} metrics={adminMetrics} />;
      case "users":
        return (
          <UsersView
            adminCanWrite={adminCanWrite}
            page={adminPages.users}
            selectedRow={selectedEvidenceRow}
            onCloseDrawer={() => setSelectedEvidenceRow(null)}
            onSelectRow={setSelectedEvidenceRow}
          />
        );
      case "security-events":
        return (
          <SecurityEventsView
            page={adminPages.securityEvents}
            selectedRow={selectedEvidenceRow}
            onCloseDrawer={() => setSelectedEvidenceRow(null)}
            onSelectRow={setSelectedEvidenceRow}
          />
        );
      case "tool-executions":
        return (
          <ToolExecutionsView
            page={adminPages.toolExecutions}
            selectedRow={selectedEvidenceRow}
            onCloseDrawer={() => setSelectedEvidenceRow(null)}
            onSelectRow={setSelectedEvidenceRow}
          />
        );
      case "gateway-evidence":
        return (
          <GatewayEvidenceView
            page={adminPages.gatewayEvidence}
            selectedRow={selectedEvidenceRow}
            onCloseDrawer={() => setSelectedEvidenceRow(null)}
            onSelectRow={setSelectedEvidenceRow}
          />
        );
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
            onGuardrailSafetyToggle={(enabled) => void updateGuardrailSafety(enabled)}
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
            <header className="border-b border-zinc-200/60 px-4 py-8 dark:border-zinc-800 sm:px-6 lg:px-8">
              <div className="mx-auto w-full max-w-[1440px]">
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-2">Administration</p>
                <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
                  {ADMIN_VIEW_META[workspaceView as Exclude<AppWorkspaceView, "chat">].title}
                </h2>
                <p className="text-zinc-600 dark:text-zinc-400">
                  {ADMIN_VIEW_META[workspaceView as Exclude<AppWorkspaceView, "chat">].description}
                </p>
              </div>
            </header>
            <ScrollArea className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
              <div className="mx-auto w-full max-w-[1440px]">
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
