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
        };
      }
      return {
        guardrail_safety_enabled: false,
        trusted_supervisor_enabled: true,
      };
    },
  } as unknown as AuthSessionController;

  assert.equal(typeof adminApi.getAdminMetrics, "function");
  assert.equal(typeof adminApi.getOrchestrationSettings, "function");
  assert.equal(typeof adminApi.setGuardrailSafetyEnabled, "function");
  assert.equal(typeof adminApi.setTrustedSupervisorEnabled, "function");

  await adminApi.getAdminMetrics(controller);
  await adminApi.getOrchestrationSettings(controller);
  await adminApi.setGuardrailSafetyEnabled(controller, false);
  await adminApi.setTrustedSupervisorEnabled(controller, true);

  assert.deepEqual(calls, [
    { url: "/api/admin/metrics", method: "GET", body: null },
    { url: "/api/admin/orchestration", method: "GET", body: null },
    { url: "/api/admin/orchestration/guardrail", method: "PATCH", body: { enabled: false } },
    { url: "/api/admin/orchestration/trusted-supervisor", method: "PATCH", body: { enabled: true } },
  ]);
});

void test("admin navigation exposes Overview and Orchestration as first-class shared-shell destinations", () => {
  const html = renderToStaticMarkup(React.createElement(ChatSidebar, navigationProps()));

  assert.match(html, /ADMIN/);
  assert.match(html, /Overview/);
  assert.match(html, /Orchestration/);
  assert.doesNotMatch(html, /data is unavailable|Not connected|placeholder/i);
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
  const html = renderToStaticMarkup(
    React.createElement(SettingsPage, {
      currentUser: adminUser,
      adminSettings: {
        guardrailSafetyEnabled: true,
        trustedSupervisorEnabled: true,
      },
      adminCanWrite: true,
      adminBusy: false,
      adminError: null,
      searchEnabled: true,
      onGuardrailSafetyToggle: () => undefined,
      onTrustedSupervisorToggle: () => undefined,
    }),
  );

  assert.match(html, /Guardrail safety/);
  assert.match(html, /Trusted supervisor Agent/);
  assert.match(html, /Disable guardrail safety\?/);
  assert.match(html, /You are removing one layer of safety checks before tool orchestration\./);
  assert.match(html, /Disable trusted supervisor Agent\?/);
  assert.match(html, /Python turns that depend on this supervision layer will be denied until it is enabled again\./);
});
