import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import * as adminApi from "@/lib/admin-api";
import { AuthSessionController } from "@/lib/auth-session";
import { ChatSidebar, type ChatNavigationProps } from "@/components/chat/ChatSidebar";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { SettingsPage } from "@/components/settings/SettingsPage";

type FetchResponse = {
  status: number;
  body?: unknown;
  headers?: Record<string, string>;
};

function jsonResponse({ status, body, headers = {} }: FetchResponse): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      ...headers,
    },
  });
}

function buildController(fetchImpl: typeof fetch): AuthSessionController {
  return new AuthSessionController("login", {
    fetchImpl,
    getCsrfToken: () => "csrf-token",
  });
}

const adminUser = {
  id: "99999999-9999-9999-9999-999999999999",
  email: "demo.admin@simpagent.test",
  role: "admin" as const,
  scopes: ["chat:read", "chat:write", "admin:read", "admin:write"],
  is_active: true,
};

function navigationProps(overrides: Partial<ChatNavigationProps> = {}): ChatNavigationProps {
  return {
    conversations: [],
    activeConversationId: null,
    currentUserEmail: adminUser.email,
    nextCursor: null,
    loading: false,
    loadingMore: false,
    deletingConversationId: null,
    adminCanRead: true,
    adminError: null,
    currentView: "overview",
    onNewChat: () => undefined,
    onSelectConversation: () => undefined,
    onSelectView: () => undefined,
    onLoadMore: () => undefined,
    onDeleteConversation: () => undefined,
    onSignOut: () => undefined,
    ...overrides,
  };
}

void test("admin API wrappers call backend metrics and orchestration endpoints through authorizedJson", async () => {
  const calls: Array<{ url: string; method: string; body: unknown }> = [];
  const controller = {
    authorizedJson: async (url: string, init: RequestInit = {}) => {
      calls.push({
        url,
        method: init.method ?? "GET",
        body: init.body ? JSON.parse(String(init.body)) : null,
      });
      if (url === "/api/admin/metrics") {
        return {
          generated_at: "2026-06-15T17:00:00Z",
          users_total: 3,
          users_active: 2,
          security_events_total: 5,
          security_events_last_24h: 2,
          tool_executions_total: 7,
          tool_executions_last_24h: 1,
          correlation_references_total: 4,
          rate_limit_events_total: 0,
        };
      }
      if (url === "/api/admin/users?limit=25&offset=0") {
        return {
          items: [],
          page: { limit: 25, offset: 0, has_more: false, next_offset: null },
        };
      }
      if (url === "/api/admin/security-events?limit=25&offset=0") {
        return {
          items: [],
          page: { limit: 25, offset: 0, has_more: false, next_offset: null },
        };
      }
      if (url === "/api/admin/tool-executions?limit=25&offset=0") {
        return {
          items: [],
          page: { limit: 25, offset: 0, has_more: false, next_offset: null },
        };
      }
      if (url === "/api/admin/gateway-evidence?limit=25&offset=0") {
        return {
          items: [],
          page: { limit: 25, offset: 0, has_more: false, next_offset: null },
          summary: {
            rate_limit_routes: 1,
            request_size_routes: 1,
            correlation_id_enabled: true,
            route_protection_routes: 1,
          },
        };
      }
      return {
        guardrail_safety_enabled: false,
        trusted_supervisor_enabled: true,
      };
    },
  } as unknown as AuthSessionController;

  assert.equal(typeof adminApi.getAdminMetrics, "function");
  assert.equal(typeof adminApi.getAdminUsers, "function");
  assert.equal(typeof adminApi.getSecurityEvents, "function");
  assert.equal(typeof adminApi.getToolExecutions, "function");
  assert.equal(typeof adminApi.getGatewayEvidence, "function");
  assert.equal(typeof adminApi.getOrchestrationSettings, "function");
  assert.equal(typeof adminApi.updateUserAccess, "function");
  assert.equal(typeof adminApi.setGuardrailSafetyEnabled, "function");
  assert.equal(typeof adminApi.setTrustedSupervisorEnabled, "function");

  await adminApi.getAdminMetrics(controller);
  await adminApi.getAdminUsers(controller, { limit: 25, offset: 0 });
  await adminApi.getSecurityEvents(controller, { limit: 25, offset: 0 });
  await adminApi.getToolExecutions(controller, { limit: 25, offset: 0 });
  await adminApi.getGatewayEvidence(controller, { limit: 25, offset: 0 });
  await adminApi.getOrchestrationSettings(controller);
  await adminApi.updateUserAccess(controller, "user-1", { role: "admin" });
  await adminApi.setGuardrailSafetyEnabled(controller, false);
  await adminApi.setTrustedSupervisorEnabled(controller, true);

  assert.deepEqual(calls, [
    { url: "/api/admin/metrics", method: "GET", body: null },
    { url: "/api/admin/users?limit=25&offset=0", method: "GET", body: null },
    { url: "/api/admin/security-events?limit=25&offset=0", method: "GET", body: null },
    { url: "/api/admin/tool-executions?limit=25&offset=0", method: "GET", body: null },
    { url: "/api/admin/gateway-evidence?limit=25&offset=0", method: "GET", body: null },
    { url: "/api/admin/orchestration", method: "GET", body: null },
    { url: "/api/admin/users/user-1", method: "PATCH", body: { role: "admin" } },
    { url: "/api/admin/orchestration/guardrail", method: "PATCH", body: { enabled: false } },
    { url: "/api/admin/orchestration/trusted-supervisor", method: "PATCH", body: { enabled: true } },
  ]);
});

void test("admin navigation exposes all six admin surfaces as first-class shared-shell destinations", () => {
  const html = renderToStaticMarkup(React.createElement(ChatSidebar, navigationProps()));

  assert.match(html, /ADMIN/);
  assert.match(html, /Overview/);
  assert.match(html, /Users/);
  assert.match(html, /Security events/);
  assert.match(html, /Tool executions/);
  assert.match(html, /Gateway evidence/);
  assert.match(html, /Orchestration/);
  assert.doesNotMatch(html, /data is unavailable|Not connected/i);
});

void test("workspace overview renders backend-backed aggregate metrics without raw content placeholders", async () => {
  const controller = buildController(async (input) => {
    const url = String(input);
    if (url === "/api/conversations?limit=20") {
      return jsonResponse({ status: 200, body: { items: [], next_cursor: null } });
    }
    if (url === "/api/admin/metrics") {
      return jsonResponse({
      status: 200,
      body: {
        generated_at: "2026-06-15T17:00:00Z",
        users_total: 3,
        users_active: 2,
        security_events_total: 5,
        security_events_last_24h: 2,
        tool_executions_total: 7,
        tool_executions_last_24h: 1,
        correlation_references_total: 4,
        rate_limit_events_total: 0,
      },
    });
    }
    if (url === "/api/admin/orchestration") {
      return jsonResponse({
        status: 200,
        body: {
          guardrail_safety_enabled: true,
          trusted_supervisor_enabled: false,
        },
      });
    }
    throw new Error(`Unexpected URL ${url}`);
  });

  const html = renderToStaticMarkup(
    React.createElement(ChatWorkspace, {
      controller,
      currentUser: adminUser,
      initialView: "overview",
      onSessionExpired: () => undefined,
      onLogout: () => undefined,
    }),
  );

  assert.match(html, /Security overview/);
  assert.match(html, /Active users/);
  assert.match(html, /Security events/);
  assert.match(html, /Tool executions/);
  assert.doesNotMatch(html, /raw prompt|password|not connected|unavailable/i);
});

void test("orchestration settings show guardrail and trusted-supervisor confirmation copy before destructive disables", () => {
  const guardrailHtml = renderToStaticMarkup(
    React.createElement(SettingsPage, {
      currentUser: adminUser,
      adminSettings: {
        guardrailSafetyEnabled: true,
        trustedSupervisorEnabled: true,
      },
      adminCanWrite: true,
      adminBusy: false,
      adminError: null,
      initialSection: "tools",
      initialConfirmingSetting: "guardrail",
      searchEnabled: true,
      onGuardrailSafetyToggle: () => undefined,
      onTrustedSupervisorToggle: () => undefined,
    }),
  );

  const supervisorHtml = renderToStaticMarkup(
    React.createElement(SettingsPage, {
      currentUser: adminUser,
      adminSettings: {
        guardrailSafetyEnabled: true,
        trustedSupervisorEnabled: true,
      },
      adminCanWrite: true,
      adminBusy: false,
      adminError: null,
      initialSection: "tools",
      initialConfirmingSetting: "trusted-supervisor",
      searchEnabled: true,
      onGuardrailSafetyToggle: () => undefined,
      onTrustedSupervisorToggle: () => undefined,
    }),
  );

  assert.match(guardrailHtml, /Guardrail safety/);
  assert.match(guardrailHtml, /Trusted supervisor Agent/);
  assert.match(guardrailHtml, /Disable guardrail safety\?/);
  assert.match(guardrailHtml, /You are removing one layer of safety checks before tool orchestration\./);
  assert.match(supervisorHtml, /Disable trusted supervisor Agent\?/);
  assert.match(supervisorHtml, /Python turns that depend on this supervision layer will be denied until it is enabled again\./);
});

void test("admin evidence primitives render rows, explicit states, and sanitized drawer snippets", async () => {
  const [{ EvidenceTable }, { EvidenceDetailDrawer }, { StatePanel }] = await Promise.all([
    import("@/components/admin/EvidenceTable"),
    import("@/components/admin/EvidenceDetailDrawer"),
    import("@/components/admin/StatePanel"),
  ]);

  const rows = [
    {
      id: "event-1",
      primary: "admin_access_denied",
      secondary: "Admin evidence access denied.",
      status: "medium",
      correlationId: "corr-denied-1",
      fields: {
        "Event type": "admin_access_denied",
        Severity: "medium",
        User: "user-1",
        Description: "Admin evidence access denied.",
        "Correlation ID": "corr-denied-1",
        Time: "2026-06-16T04:30:00Z",
      },
      snippets: [
        {
          kind: "metadata",
          text: "resource=gateway_evidence required_scope=admin:read decision=deny_scope",
          truncated: false,
        },
      ],
    },
  ];

  const tableHtml = renderToStaticMarkup(
    React.createElement(EvidenceTable, {
      title: "Security events",
      description: "Bounded backend evidence",
      emptyTitle: "No evidence matches the current filter.",
      rows,
      page: { limit: 25, offset: 0, has_more: false, next_offset: null },
      onSelectRow: () => undefined,
    }),
  );

  assert.match(tableHtml, /Security events/);
  assert.match(tableHtml, /admin_access_denied/);
  assert.match(tableHtml, /corr-denied-1/);
  assert.match(tableHtml, /Xem chi tiết/);

  const drawerHtml = renderToStaticMarkup(
    React.createElement(EvidenceDetailDrawer, {
      open: true,
      title: "Security event details",
      description: "Backend-sanitized snippets only",
      row: rows[0],
      onOpenChange: () => undefined,
    }),
  );

  assert.match(drawerHtml, /Security event details/);
  assert.match(drawerHtml, /resource=gateway_evidence/);
  assert.doesNotMatch(drawerHtml, /Bearer|cookie|password|api[_-]?key|raw prompt/i);

  const forbiddenHtml = renderToStaticMarkup(
    React.createElement(StatePanel, {
      state: "forbidden",
      title: "You do not have permission to view this area.",
      body: "Use an account with the required access or contact an administrator.",
    }),
  );
  assert.match(forbiddenHtml, /You do not have permission to view this area\./);
  assert.match(forbiddenHtml, /required access/);
});

void test("workspace renders backend-backed users, event, tool, and gateway evidence pages with drawer actions", () => {
  const controller = buildController(async (input) => {
    const url = String(input);
    if (url === "/api/conversations?limit=20") {
      return jsonResponse({ status: 200, body: { items: [], next_cursor: null } });
    }
    throw new Error(`Unexpected URL ${url}`);
  });

  const initialAdminPages = {
    users: {
      items: [
        {
          id: "user-1",
          email: "member@simpagent.test",
          role: "user",
          scopes: ["chat:read", "chat:write"],
          is_active: true,
          is_demo: false,
          created_at: "2026-06-16T04:00:00Z",
          updated_at: "2026-06-16T04:00:00Z",
        },
      ],
      page: { limit: 25, offset: 0, has_more: false, next_offset: null },
    },
    securityEvents: {
      items: [
        {
          id: "event-1",
          event_type: "admin_access_denied",
          severity: "medium",
          user_id: "user-1",
          description: "Admin evidence access denied.",
          correlation_id: "corr-admin-denied",
          metadata: { resource: "gateway_evidence" },
          snippets: [{ kind: "metadata", text: "resource=gateway_evidence", truncated: false }],
          created_at: "2026-06-16T04:10:00Z",
        },
      ],
      page: { limit: 25, offset: 0, has_more: false, next_offset: null },
    },
    toolExecutions: {
      items: [
        {
          id: "tool-1",
          user_id: "user-1",
          conversation_id: "conversation-1",
          tool_name: "google_search",
          input_summary: "latest public cloud security headlines",
          output_summary: "Grounded answer with citations",
          status: "succeeded",
          duration_ms: 1200,
          correlation_id: "corr-tool-1",
          snippets: [{ kind: "tool_execution", text: "status=succeeded duration_ms=1200", truncated: false }],
          created_at: "2026-06-16T04:11:00Z",
        },
      ],
      page: { limit: 25, offset: 0, has_more: false, next_offset: null },
    },
    gatewayEvidence: {
      items: [
        {
          id: "kong-config-rate-limit-api",
          evidence_type: "rate_limit" as const,
          source: "kong_config" as const,
          route: "api",
          plugin: "rate-limiting",
          status_codes: [429],
          summary: "Kong local rate limiting protects route api.",
          metadata: { route: "api", policy: "local" },
          snippets: [{ kind: "gateway_evidence", text: "route=api policy=local", truncated: false }],
        },
      ],
      page: { limit: 25, offset: 0, has_more: false, next_offset: null },
      summary: {
        rate_limit_routes: 1,
        request_size_routes: 1,
        correlation_id_enabled: true,
        route_protection_routes: 1,
      },
    },
  };

  for (const [view, expected] of [
    ["users", "member@simpagent.test"],
    ["security-events", "admin_access_denied"],
    ["tool-executions", "google_search"],
    ["gateway-evidence", "Kong local rate limiting protects route api."],
  ] as const) {
    const html = renderToStaticMarkup(
      React.createElement(ChatWorkspace, {
        controller,
        currentUser: adminUser,
        initialView: view,
        initialAdminPages,
        onSessionExpired: () => undefined,
        onLogout: () => undefined,
      }),
    );
    assert.match(html, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.match(html, /Xem chi tiết/);
    assert.doesNotMatch(html, /unavailable|not connected|fake telemetry|Available from backend admin endpoints/i);
  }
});

void test("ordinary and under-scoped users receive explicit denied UI while write actions stay scoped", () => {
  const controller = buildController(async (input) => {
    const url = String(input);
    if (url === "/api/conversations?limit=20") {
      return jsonResponse({ status: 200, body: { items: [], next_cursor: null } });
    }
    throw new Error(`Unexpected URL ${url}`);
  });
  const readerOnlyAdmin = {
    ...adminUser,
    scopes: ["chat:read", "chat:write", "admin:read"],
  };

  const deniedHtml = renderToStaticMarkup(
    React.createElement(ChatWorkspace, {
      controller,
      currentUser: {
        ...adminUser,
        role: "user",
        scopes: ["chat:read", "chat:write"],
      },
      initialView: "gateway-evidence",
      onSessionExpired: () => undefined,
      onLogout: () => undefined,
    }),
  );
  assert.match(deniedHtml, /You do not have permission to view this area\./);
  assert.doesNotMatch(deniedHtml, /Kong local rate limiting|fake telemetry/i);

  const readOnlyHtml = renderToStaticMarkup(
    React.createElement(ChatWorkspace, {
      controller,
      currentUser: readerOnlyAdmin,
      initialView: "users",
      initialAdminPages: {
        users: {
          items: [],
          page: { limit: 25, offset: 0, has_more: false, next_offset: null },
        },
      },
      onSessionExpired: () => undefined,
      onLogout: () => undefined,
    }),
  );
  assert.match(readOnlyHtml, /Read-only admin access/);
  assert.doesNotMatch(readOnlyHtml, /Grant administrator access|Deactivate account/);
});
