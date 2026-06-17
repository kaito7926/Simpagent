import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthCard } from "@/components/account-access/AuthCard";
import { beginOAuth, type OAuthProviderId, type ReadinessResponse } from "@/lib/auth-session";
import { formsEnabled, oauthProviderState } from "@/lib/readiness";

function readiness(oauth_google: "ready" | "unconfigured", oauth_github: "ready" | "unconfigured"): ReadinessResponse {
  return {
    status: oauth_google === "ready" || oauth_github === "ready" ? "ready" : "degraded",
    components: {
      database: "ready",
      migrations: "ready",
      llm: "unconfigured",
      search: "unconfigured",
      sandbox: "foundation_ready",
      oauth_google,
      oauth_github,
    },
  };
}

function renderAuthCard(providerReadiness: ReadinessResponse): string {
  return renderToStaticMarkup(
    React.createElement(AuthCard, {
      sessionState: "anonymous_login",
      authMode: "login",
      heading: "Sign in to SimpAgent",
      body: "Use Google, GitHub, or your local email and password to enter a protected workspace.",
      disabled: !formsEnabled(providerReadiness),
      isSubmitting: false,
      currentUser: null,
      logoutRetryVisible: false,
      formContent: React.createElement("div", null, [
        React.createElement("label", { key: "email", htmlFor: "login-email" }, "Email Address"),
        React.createElement("input", { key: "input", id: "login-email", name: "email" }),
        React.createElement("button", { key: "submit", type: "submit" }, "Sign in"),
      ]),
      globalMessage: null,
      errorMessage: null,
      correlationId: null,
      oauthProviders: [
        oauthProviderState(providerReadiness, "google"),
        oauthProviderState(providerReadiness, "github"),
      ],
      onOAuthStart: () => undefined,
      onModeChange: () => undefined,
      onLoginSubmit: () => undefined,
      onRegisterSubmit: () => undefined,
      onLogout: () => undefined,
      onGoToLogin: () => undefined,
      scopeLabels: {},
      demoEnabled: false,
      onFillDemoUser: () => undefined,
      onFillDemoAdmin: () => undefined,
    }),
  );
}

void test("auth shell renders configured Google and GitHub CTAs above local credentials", () => {
  const html = renderAuthCard(readiness("ready", "ready"));
  const googleIndex = html.indexOf("Continue with Google");
  const githubIndex = html.indexOf("Continue with GitHub");
  const dividerIndex = html.indexOf("Or use local credentials");
  const emailIndex = html.indexOf("Email Address");

  assert.ok(googleIndex >= 0, "Google CTA should render");
  assert.ok(githubIndex >= 0, "GitHub CTA should render");
  assert.ok(dividerIndex > githubIndex, "local divider should appear after provider CTAs");
  assert.ok(emailIndex > dividerIndex, "local form should remain below the divider");
  assert.doesNotMatch(html, /disabled=""[^>]*Continue with Google|disabled=""[^>]*Continue with GitHub/);
  assert.doesNotMatch(html, /placeholder|fake social|Or sign in with email/i);
});

void test("mixed provider readiness keeps factual provider copy and local credentials", () => {
  const googleOnlyHtml = renderAuthCard(readiness("ready", "unconfigured"));
  assert.match(googleOnlyHtml, /Continue with Google/);
  assert.match(googleOnlyHtml, /GitHub sign-in is not configured/);
  assert.match(googleOnlyHtml, /Or use local credentials/);
  assert.match(googleOnlyHtml, /Email Address/);

  const githubOnlyHtml = renderAuthCard(readiness("unconfigured", "ready"));
  assert.match(githubOnlyHtml, /Google sign-in is not configured/);
  assert.match(githubOnlyHtml, /Continue with GitHub/);
  assert.match(githubOnlyHtml, /Or use local credentials/);
  assert.match(githubOnlyHtml, /Email Address/);

  const disabledHtml = renderAuthCard(readiness("unconfigured", "unconfigured"));
  assert.match(disabledHtml, /Google sign-in is not configured/);
  assert.match(disabledHtml, /GitHub sign-in is not configured/);
  assert.match(disabledHtml, /Or use local credentials/);
  assert.match(disabledHtml, /Email Address/);
});

void test("oauth readiness helper exposes provider-specific enabled and disabled states", () => {
  assert.deepEqual(oauthProviderState(readiness("ready", "unconfigured"), "google"), {
    provider: "google",
    label: "Continue with Google",
    enabled: true,
    unavailableLabel: null,
  });
  assert.deepEqual(oauthProviderState(readiness("ready", "unconfigured"), "github"), {
    provider: "github",
    label: "Continue with GitHub",
    enabled: false,
    unavailableLabel: "GitHub sign-in is not configured",
  });
});

void test("starting OAuth navigates to backend-owned routes without browser token storage", () => {
  const navigation: string[] = [];
  const storageTrap = {
    setItem(key: string) {
      throw new Error(`unexpected browser token storage: ${key}`);
    },
    removeItem(key: string) {
      throw new Error(`unexpected browser token storage: ${key}`);
    },
  };

  for (const provider of ["google", "github"] satisfies OAuthProviderId[]) {
    beginOAuth(provider, {
      navigate: (url) => navigation.push(url),
      localStorage: storageTrap,
      sessionStorage: storageTrap,
    });
  }

  assert.deepEqual(navigation, [
    "/api/auth/oauth/google/start",
    "/api/auth/oauth/github/start",
  ]);
});
