import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import React from "react";

import { AccountAccessShell } from "@/components/account-access/AccountAccessShell";
import { AuthSessionController } from "@/lib/auth-session";
import { listConversations } from "@/lib/chat-api";

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

const currentUser = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "demo.user@simpagent.test",
  role: "user" as const,
  scopes: ["chat:read", "chat:write"],
  is_active: true,
};

void test("chat requests use refresh-on-401 then retry through authorizedJson", async () => {
  const calls: Array<{ url: string; authorization: string | null }> = [];
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
    if (url === "/api/auth/refresh") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-2", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/conversations?limit=20") {
      const authorization = new Headers(init?.headers).get("Authorization");
      calls.push({ url, authorization });
      if (authorization === "Bearer token-1") {
        return jsonResponse({
          status: 401,
          body: { error: { code: "stale_token", message: "expired" } },
        });
      }
      return jsonResponse({ status: 200, body: { items: [], next_cursor: null } });
    }
    throw new Error(`Unexpected URL ${url}`);
  };
  const controller = new AuthSessionController("login", {
    fetchImpl,
    getCsrfToken: () => "csrf-token",
  });

  await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });
  const page = await listConversations(controller);

  assert.deepEqual(page.items, []);
  assert.deepEqual(
    calls.map((call) => call.authorization),
    ["Bearer token-1", "Bearer token-2"],
  );
});

void test("terminal chat session expiry returns to English login copy", async () => {
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
    if (url === "/api/conversations?limit=20") {
      return jsonResponse({
        status: 401,
        body: { error: { code: "stale_token", message: "expired", correlation_id: "corr-expired-1" } },
      });
    }
    if (url === "/api/auth/refresh") {
      return jsonResponse({
        status: 401,
        body: { error: { code: "session_invalid", message: "ended", correlation_id: "corr-expired-2" } },
      });
    }
    throw new Error(`Unexpected URL ${url} ${init?.method ?? "GET"}`);
  };
  const controller = new AuthSessionController("login", {
    fetchImpl,
    getCsrfToken: () => "csrf-token",
  });

  await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });
  await assert.rejects(() => listConversations(controller), /expired|ended/i);

  const snapshot = controller.snapshot;
  assert.equal(snapshot.sessionState, "session_expired");
  assert.equal(snapshot.currentUser, null);
  assert.equal(snapshot.accessToken, null);
  assert.equal(snapshot.globalMessage, "Your session is no longer valid. Sign in again to continue.");

  const html = renderToStaticMarkup(
    React.createElement(AccountAccessShell, {
      initialMode: "login",
      demoConfig: { enabled: false },
    }),
  );
  assert.match(html, /SimpAgent|Session ended/);
  assert.match(html, /Intelligent\. Secure\. Always by your side\.|Your session is no longer valid\. Sign in again to continue\./);
});
