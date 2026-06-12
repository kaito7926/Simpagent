import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import React from "react";

import { AuthSessionController } from "@/lib/auth-session";
import {
  createConversationWithMessage,
  getConversation,
  retryMessage,
  sendMessage,
} from "@/lib/chat-api";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";

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

  assert.match(html, /Start a private chat/);
  assert.match(
    html,
    /Ask a question to create your first conversation\. Messages stay inside your own workspace\./,
  );
  assert.match(html, /Message/);
  assert.match(html, /Message SimpAgent/);
  assert.match(html, /Send message/);
  assert.match(html, /No conversations yet/);
  assert.doesNotMatch(html, /model|provider|Python|Search|citation|upload|voice/i);
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
    },
  });
  assert.equal(globalThis.localStorage?.getItem("access_token"), null);
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
