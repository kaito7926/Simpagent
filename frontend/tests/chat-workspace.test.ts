import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import React from "react";

import { AuthSessionController } from "@/lib/auth-session";
import {
  createConversationWithMessage,
  deleteConversation,
  getConversation,
  retryMessage,
  sendMessage,
  undoDeleteConversation,
} from "@/lib/chat-api";
import {
  ChatWorkspace,
  removeConversationSummary,
  restoreConversationSummary,
} from "@/components/chat/ChatWorkspace";
import { ChatDrawer } from "@/components/chat/ChatDrawer";
import { ChatMobileBar } from "@/components/chat/ChatMobileBar";
import {
  ChatSidebar,
  groupConversations,
  type ChatNavigationProps,
} from "@/components/chat/ChatSidebar";
import { ConversationMenu } from "@/components/chat/ConversationMenu";
import { UndoToast } from "@/components/chat/UndoToast";
import type { ConversationSummary } from "@/lib/chat-types";

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

async function signIn(controller: AuthSessionController) {
  await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });
}

const currentUser = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "demo.user@simpagent.test",
  role: "user" as const,
  scopes: ["chat:read", "chat:write"],
  is_active: true,
};

const adminUser = {
  id: "99999999-9999-9999-9999-999999999999",
  email: "demo.admin@simpagent.test",
  role: "admin" as const,
  scopes: ["chat:read", "chat:write", "admin:read", "admin:write"],
  is_active: true,
};

const conversationSummaries: ConversationSummary[] = [
  {
    id: "today-pending",
    owner_id: currentUser.id,
    title: "Today pending",
    message_count: 2,
    state_label: "Pending reply",
    created_at: "2026-06-12T07:00:00Z",
    updated_at: "2026-06-12T08:00:00Z",
  },
  {
    id: "yesterday-retry",
    owner_id: currentUser.id,
    title: "Yesterday retry",
    message_count: 2,
    state_label: "Retry available",
    created_at: "2026-06-11T07:00:00Z",
    updated_at: "2026-06-11T08:00:00Z",
  },
  {
    id: "previous-week",
    owner_id: currentUser.id,
    title: "Previous week",
    message_count: 1,
    state_label: null,
    created_at: "2026-06-08T07:00:00Z",
    updated_at: "2026-06-08T08:00:00Z",
  },
  {
    id: "older",
    owner_id: currentUser.id,
    title: "Older",
    message_count: 1,
    state_label: null,
    created_at: "2026-05-01T07:00:00Z",
    updated_at: "2026-05-01T08:00:00Z",
  },
];

function navigationProps(overrides: Partial<ChatNavigationProps> = {}): ChatNavigationProps {
  return {
    ...navigationPropsBase(),
    ...overrides,
  };
}

function navigationPropsBase(): ChatNavigationProps {
  return {
    conversations: conversationSummaries,
    activeConversationId: "today-pending",
    currentUserEmail: currentUser.email,
    nextCursor: "cursor-next",
    loading: false,
    loadingMore: false,
    deletingConversationId: null,
    adminCanRead: false,
    adminError: null,
    now: new Date("2026-06-12T12:00:00Z"),
    collapsed: false,
    onNewChat: () => undefined,
    onSelectConversation: () => undefined,
    onLoadMore: () => undefined,
    onDeleteConversation: () => undefined,
    onSignOut: () => undefined,
    onToggleCollapse: () => undefined,
  };
}

void test("sidebar groups newest-first navigation and pins account actions last", () => {
  const groups = groupConversations(
    conversationSummaries,
    new Date("2026-06-12T12:00:00Z"),
  );
  assert.deepEqual(
    groups.map((group) => [group.label, group.items.map((item) => item.id)]),
    [
      ["Today", ["today-pending"]],
      ["Yesterday", ["yesterday-retry"]],
      ["Previous 7 Days", ["previous-week"]],
      ["Older", ["older"]],
    ],
  );

  const html = renderToStaticMarkup(React.createElement(ChatSidebar, navigationProps()));
  for (const copy of [
    "SimpAgent",
    "Start New Chat",
    "Today",
    "Today pending",
    "Yesterday",
    "Retry available",
    "Previous week",
    "Older",
    currentUser.email,
    "Sign out",
  ]) {
    assert.notEqual(html.indexOf(copy), -1, `${copy} should appear in the sidebar`);
  }
  assert.match(html, /Today pending/);
});

void test("admin sidebar keeps administration as navigation only", () => {
  const adminHtml = renderToStaticMarkup(
    React.createElement(
      ChatSidebar,
      navigationProps({
        currentUserEmail: adminUser.email,
        adminCanRead: true,
      }),
    ),
  );
  assert.match(adminHtml, /ADMIN/);
  assert.match(adminHtml, /Overview/);
  assert.match(adminHtml, /Settings/);
  assert.doesNotMatch(adminHtml, /Trusted supervisor/);
  assert.doesNotMatch(adminHtml, /Enable|Disable/);

  const userHtml = renderToStaticMarkup(React.createElement(ChatSidebar, navigationProps()));
  assert.doesNotMatch(userHtml, /Trusted supervisor/);
});

void test("mobile bar and open drawer expose navigation without extra management actions", () => {
  const mobileBar = renderToStaticMarkup(
    React.createElement(ChatMobileBar, {
      onOpenNavigation: () => undefined,
      onNewChat: () => undefined,
    }),
  );
  assert.match(mobileBar, /Open conversation navigation/);
  assert.match(mobileBar, /SimpAgent/);
  assert.match(mobileBar, /New chat/);

  const drawer = renderToStaticMarkup(
    React.createElement(ChatDrawer, {
      open: true,
      onClose: () => undefined,
      navigationProps: navigationProps(),
    }),
  );
  assert.match(drawer, /role="dialog"/);
  assert.match(drawer, /Conversation navigation/);
  assert.match(drawer, /Delete conversation/);
  assert.doesNotMatch(drawer, /Rename|Archive|Share|Export/);
});

void test("conversation menu confirms delete with exact copy and no extra row actions", () => {
  const html = renderToStaticMarkup(
    React.createElement(ConversationMenu, {
      conversationTitle: "Today pending",
      open: true,
      confirming: true,
      deleting: false,
      onOpenChange: () => undefined,
      onDelete: () => undefined,
      onKeep: () => undefined,
    }),
  );

  assert.match(html, /Delete conversation/);
  assert.match(
    html,
    /This removes the conversation from your sidebar now\. You can undo for a short time\./,
  );
  assert.match(html, /Keep conversation/);
  assert.doesNotMatch(html, /Rename|Archive|Search|Share|Export/);
});

void test("delete removes a row immediately and undo restores it without a page refresh", async () => {
  const calls: Array<{ url: string; method: string }> = [];
  const controller = buildController(async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({ status: 200, body: currentUser });
    }
    calls.push({ url, method: init?.method ?? "GET" });
    if (init?.method === "DELETE") {
      return new Response(null, { status: 204 });
    }
    return jsonResponse({ status: 200, body: conversationSummaries[0] });
  });
  await signIn(controller);

  const deleted = conversationSummaries[0];
  const remaining = removeConversationSummary(conversationSummaries, deleted.id);
  assert.deepEqual(remaining.map((item) => item.id), [
    "yesterday-retry",
    "previous-week",
    "older",
  ]);

  await deleteConversation(controller, deleted.id);
  const restored = await undoDeleteConversation(controller, deleted.id);
  const visible = restoreConversationSummary(remaining, restored);
  assert.equal(visible[0].id, deleted.id);
  assert.deepEqual(calls, [
    {
      url: "/api/conversations/today-pending",
      method: "DELETE",
    },
    {
      url: "/api/conversations/today-pending/undo-delete",
      method: "POST",
    },
  ]);

  const toast = renderToStaticMarkup(
    React.createElement(UndoToast, {
      visible: true,
      undoing: false,
      onUndo: () => undefined,
    }),
  );
  assert.match(toast, /Conversation deleted/);
  assert.match(toast, /Undo/);
});

void test("authenticated empty workspace renders exact composer-first copy", async () => {
  const controller = buildController(async (input) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({ status: 200, body: currentUser });
    }
    if (url === "/api/conversations?limit=20") {
      return jsonResponse({ status: 200, body: { items: [], next_cursor: null } });
    }
    throw new Error(`Unexpected URL ${url}`);
  });
  await signIn(controller);

  const html = renderToStaticMarkup(
    React.createElement(ChatWorkspace, {
      controller,
      currentUser,
      onSessionExpired: () => undefined,
      onLogout: () => undefined,
    }),
  );

  assert.match(html, /New Chat/);
  assert.match(
    html,
    /Say hello to start/,
  );
  assert.match(html, /How can I help you today\?/);
  assert.match(html, /How can I help you today\?/);
  assert.match(html, /No conversations yet/);
  assert.doesNotMatch(html, /provider|upload/i);
});

void test("first submit sends generated client_message_id through authorizedJson", async () => {
  const calls: Array<{ url: string; init?: RequestInit; authorization: string | null; body: unknown }> = [];
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({ status: 200, body: currentUser });
    }
    if (url === "/api/conversations") {
      calls.push({
        url,
        init,
        authorization: new Headers(init?.headers).get("Authorization"),
        body: JSON.parse(String(init?.body)),
      });
      return jsonResponse({
        status: 201,
        body: {
          id: "22222222-2222-2222-2222-222222222222",
          owner_id: currentUser.id,
          title: "Explain retry safety",
          message_count: 2,
          created_at: "2026-06-12T08:00:00Z",
          updated_at: "2026-06-12T08:00:01Z",
          messages: [
            {
              id: "33333333-3333-3333-3333-333333333333",
              conversation_id: "22222222-2222-2222-2222-222222222222",
              sequence_no: 1,
              client_message_id: "client-uuid-1",
              role: "user",
              status: "completed",
              content: "Explain retry safety",
              metadata: {},
              created_at: "2026-06-12T08:00:00Z",
            },
            {
              id: "44444444-4444-4444-4444-444444444444",
              conversation_id: "22222222-2222-2222-2222-222222222222",
              sequence_no: 2,
              client_message_id: null,
              role: "assistant",
              status: "completed",
              content: "A retry-safe request is idempotent.",
              metadata: {},
              created_at: "2026-06-12T08:00:01Z",
            },
          ],
        },
      });
    }
    throw new Error(`Unexpected URL ${url}`);
  };
  const controller = buildController(fetchImpl);
  await signIn(controller);

  const generatedId = "client-uuid-1";
  const detail = await createConversationWithMessage(controller, {
    content: "Explain retry safety",
    clientMessageId: generatedId,
  });

  assert.equal(detail.id, "22222222-2222-2222-2222-222222222222");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].authorization, "Bearer token-1");
  assert.deepEqual(calls[0].body, {
    initial_message: {
      client_message_id: generatedId,
      content: "Explain retry safety",
      tool_mode: "auto",
    },
  });
  assert.equal(globalThis.localStorage?.getItem("access_token") ?? null, null);
});

void test("active thread reload, pending lockout, failed row, and retry copy are represented", async () => {
  const controller = buildController(async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({ status: 200, body: currentUser });
    }
    if (url === "/api/conversations/22222222-2222-2222-2222-222222222222") {
      return jsonResponse({
        status: 200,
        body: {
          id: "22222222-2222-2222-2222-222222222222",
          owner_id: currentUser.id,
          title: "Provider failure",
          message_count: 2,
          created_at: "2026-06-12T08:00:00Z",
          updated_at: "2026-06-12T08:00:01Z",
          messages: [
            {
              id: "33333333-3333-3333-3333-333333333333",
              conversation_id: "22222222-2222-2222-2222-222222222222",
              sequence_no: 1,
              client_message_id: "failed-client-id",
              role: "user",
              status: "completed",
              content: "Will this fail?",
              metadata: {},
              created_at: "2026-06-12T08:00:00Z",
            },
            {
              id: "44444444-4444-4444-4444-444444444444",
              conversation_id: "22222222-2222-2222-2222-222222222222",
              sequence_no: 2,
              client_message_id: "failed-client-id",
              role: "assistant",
              status: "failed",
              content: "",
              metadata: { correlation_id: "corr-failed-1", retryable: true },
              created_at: "2026-06-12T08:00:01Z",
            },
          ],
        },
      });
    }
    if (url === "/api/conversations/22222222-2222-2222-2222-222222222222/messages") {
      return jsonResponse({
        status: 409,
        body: { error: { code: "turn_in_progress", message: "pending" } },
      });
    }
    if (
      url ===
      "/api/conversations/22222222-2222-2222-2222-222222222222/messages/failed-client-id/retry"
    ) {
      return jsonResponse({
        status: 200,
        body: {
          id: "22222222-2222-2222-2222-222222222222",
          owner_id: currentUser.id,
          title: "Provider failure",
          message_count: 2,
          created_at: "2026-06-12T08:00:00Z",
          updated_at: "2026-06-12T08:00:02Z",
          messages: [],
        },
      });
    }
    throw new Error(`Unexpected URL ${url} ${init?.method ?? "GET"}`);
  });
  await signIn(controller);

  const detail = await getConversation(controller, "22222222-2222-2222-2222-222222222222");
  const html = renderToStaticMarkup(
    React.createElement(ChatWorkspace, {
      controller,
      currentUser,
      initialConversation: detail,
      onSessionExpired: () => undefined,
      onLogout: () => undefined,
    }),
  );

  assert.match(html, /The reply could not be completed\./);
  assert.match(html, /Try again\. If the issue continues, use the reference code below when asking for support\./);
  assert.match(html, /Retry response/);
  assert.match(html, /Reference code: corr-failed-1/);

  await assert.rejects(
    () =>
      sendMessage(controller, "22222222-2222-2222-2222-222222222222", {
        clientMessageId: "blocked-client-id",
        content: "Second message",
      }),
    /pending|response is already pending|turn_in_progress/i,
  );

  const retried = await retryMessage(
    controller,
    "22222222-2222-2222-2222-222222222222",
    "failed-client-id",
  );
  assert.equal(retried.id, "22222222-2222-2222-2222-222222222222");
});
