import test from "node:test";
import assert from "node:assert/strict";

import { ApiError } from "@/lib/api";
import { AuthSessionController } from "@/lib/auth-session";

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

function currentUserBody() {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    email: "demo.user@simpagent.test",
    role: "user",
    scopes: ["chat:read", "chat:write", "tool:python", "tool:websearch"],
    is_active: true,
  };
}

void test("auth controller attaches DPoP proof material to session routes and protected requests", async () => {
  const calls: Array<{ url: string; method: string; dpop: string | null; authorization: string | null }> = [];
  const deviceProof = {
    proofHeader: async (input: string, init: RequestInit = {}) =>
      `proof:${init.method ?? "GET"}:${input}`,
  };
  const fetchImpl: typeof fetch = async (input, init = {}) => {
    const url = String(input);
    const headers = new Headers(init.headers);
    calls.push({
      url,
      method: init.method ?? "GET",
      dpop: headers.get("DPoP"),
      authorization: headers.get("Authorization"),
    });
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({ status: 200, body: currentUserBody() });
    }
    if (url === "/api/protected") {
      if (headers.get("Authorization") === "Bearer token-1") {
        return jsonResponse({
          status: 401,
          body: { error: { code: "stale_token", message: "expired" } },
        });
      }
      return jsonResponse({ status: 200, body: { ok: true } });
    }
    if (url === "/api/auth/refresh") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-2", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/logout") {
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unexpected URL ${url}`);
  };

  const controller = new AuthSessionController("login", {
    fetchImpl,
    getCsrfToken: () => "csrf-token",
    deviceProof,
  });

  await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });
  await controller.authorizedJson<{ ok: boolean }>("/api/protected", { method: "GET" });
  await controller.logout();

  assert.deepEqual(
    calls.map((call) => [call.url, call.dpop]),
    [
      ["/api/auth/login", "proof:POST:/api/auth/login"],
      ["/api/auth/me", "proof:GET:/api/auth/me"],
      ["/api/protected", "proof:GET:/api/protected"],
      ["/api/auth/refresh", "proof:POST:/api/auth/refresh"],
      ["/api/protected", "proof:GET:/api/protected"],
      ["/api/auth/logout", "proof:POST:/api/auth/logout"],
    ],
  );
  assert.equal(calls[2].authorization, "Bearer token-1");
  assert.equal(calls[4].authorization, "Bearer token-2");
});

void test("proof loss expires the local session instead of falling back to bearer-only requests", async () => {
  let proofAvailable = true;
  const deviceProof = {
    proofHeader: async () => {
      if (!proofAvailable) {
        throw new Error("device proof unavailable");
      }
      return "proof-ok";
    },
  };
  const fetchImpl: typeof fetch = async (input) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({ status: 200, body: currentUserBody() });
    }
    throw new Error(`Unexpected bearer fallback to ${url}`);
  };
  const controller = new AuthSessionController("login", {
    fetchImpl,
    getCsrfToken: () => "csrf-token",
    deviceProof,
  });

  await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });
  proofAvailable = false;

  await assert.rejects(() => controller.authorizedJson("/api/protected", { method: "GET" }));
  assert.equal(controller.snapshot.sessionState, "session_expired");
  assert.equal(controller.snapshot.accessToken, null);
});

void test("simultaneous protected requests share one refresh attempt", async () => {
  let refreshCalls = 0;
  let meCalls = 0;
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/refresh") {
      refreshCalls += 1;
      return jsonResponse({
        status: 200,
        body: { access_token: "token-2", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      meCalls += 1;
      if (meCalls === 1) {
        return jsonResponse({
          status: 200,
          body: {
            id: "11111111-1111-1111-1111-111111111111",
            email: "demo.user@simpagent.test",
            role: "user",
            scopes: ["chat:read", "chat:write", "tool:python", "tool:websearch"],
            is_active: true,
          },
        });
      }
      return jsonResponse({
        status: 401,
        body: { error: { code: "stale_token", message: "expired" } },
      });
    }
    if (url === "/api/protected") {
      const authHeader = new Headers(init?.headers).get("Authorization");
      if (authHeader === "Bearer token-1") {
        return jsonResponse({
          status: 401,
          body: { error: { code: "invalid_token", message: "expired" } },
        });
      }
      return jsonResponse({ status: 200, body: { ok: true } });
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

  const [first, second] = await Promise.all([
    controller.authorizedJson<{ ok: boolean }>("/api/protected", { method: "GET" }),
    controller.authorizedJson<{ ok: boolean }>("/api/protected", { method: "GET" }),
  ]);

  assert.equal(first.ok, true);
  assert.equal(second.ok, true);
  assert.equal(refreshCalls, 1);
});

void test("terminal refresh failure clears session and moves to session expired", async () => {
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({
        status: 200,
        body: {
          id: "11111111-1111-1111-1111-111111111111",
          email: "demo.user@simpagent.test",
          role: "user",
          scopes: ["chat:read", "chat:write", "tool:python", "tool:websearch"],
          is_active: true,
        },
      });
    }
    if (url === "/api/protected") {
      return jsonResponse({
        status: 401,
        body: { error: { code: "stale_token", message: "expired", correlation_id: "corr-1" } },
      });
    }
    if (url === "/api/auth/refresh") {
      return jsonResponse({
        status: 401,
        body: { error: { code: "session_invalid", message: "ended", correlation_id: "corr-2" } },
      });
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

  await assert.rejects(() => controller.authorizedJson("/api/protected", { method: "GET" }), ApiError);
  const snapshot = controller.snapshot;
  assert.equal(snapshot.sessionState, "session_expired");
  assert.equal(snapshot.accessToken, null);
  assert.equal(snapshot.currentUser, null);
});

void test("unknown /me authority fails closed after login", async () => {
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      return jsonResponse({
        status: 200,
        body: {
          id: "11111111-1111-1111-1111-111111111111",
          email: "demo.user@simpagent.test",
          role: "owner",
          scopes: ["chat:read"],
          is_active: true,
        },
      });
    }
    throw new Error(`Unexpected URL ${url}`);
  };

  const controller = new AuthSessionController("login", { fetchImpl, getCsrfToken: () => "csrf" });
  const snapshot = await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });

  assert.equal(snapshot.sessionState, "session_expired");
  assert.equal(snapshot.accessToken, null);
});

void test("logout failure preserves authenticated state and surfaces retry copy", async () => {
  let meCalls = 0;
  const fetchImpl: typeof fetch = async (input, init) => {
    const url = String(input);
    if (url === "/api/auth/login") {
      return jsonResponse({
        status: 200,
        body: { access_token: "token-1", token_type: "bearer", expires_in: 600 },
      });
    }
    if (url === "/api/auth/me") {
      meCalls += 1;
      return jsonResponse({
        status: 200,
        body: {
          id: "11111111-1111-1111-1111-111111111111",
          email: "demo.user@simpagent.test",
          role: "user",
          scopes: ["chat:read", "chat:write", "tool:python", "tool:websearch"],
          is_active: true,
        },
      });
    }
    if (url === "/api/auth/logout") {
      return jsonResponse({
        status: 500,
        body: { error: { code: "server_error", message: "boom", correlation_id: "corr-3" } },
      });
    }
    throw new Error(`Unexpected URL ${url}`);
  };

  const controller = new AuthSessionController("login", { fetchImpl, getCsrfToken: () => "csrf" });
  await controller.login({
    email: "demo.user@simpagent.test",
    password: "MatKhauBaoMat123456",
  });

  const snapshot = await controller.logout();
  assert.equal(snapshot.sessionState, "authenticated");
  assert.equal(snapshot.currentUser?.email, "demo.user@simpagent.test");
  assert.equal(snapshot.globalMessage, "Sign out could not be completed. Check your connection and try again.");
  assert.equal(snapshot.correlationId, "corr-3");
  assert.equal(meCalls, 1);
});
