"use client";

import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { DemoConfig } from "@/lib/demo-config";
import {
  AuthSessionController,
  beginOAuth,
  type OAuthProviderId,
  type SessionState,
  type ShellViewModel,
} from "@/lib/auth-session";
import { formsEnabled, oauthProviderState, toAggregateUiState } from "@/lib/readiness";

import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { ActionButton } from "./ActionButton";
import { AuthCard } from "./AuthCard";
import { FormField } from "./FormField";
import { PasswordField } from "./PasswordField";
import { PlatformStatus } from "./PlatformStatus";
import { SecuritySummary } from "./SecuritySummary";

type AccountAccessShellProps = {
  initialMode: string | null;
  demoConfig: DemoConfig;
};

type FormFields = {
  email: string;
  password: string;
  confirmPassword: string;
  inviteCode: string;
};

type FormErrors = {
  email: string | null;
  password: string | null;
  confirmPassword: string | null;
  inviteCode: string | null;
};

const SCOPE_LABELS: Record<string, string> = {
  "chat:read": "Read conversations",
  "chat:write": "Create and update conversations",
  "tool:websearch": "Use Google Search",
  "tool:python": "Use limited Python",
  "admin:read": "View administration data",
  "admin:write": "Change administration data",
};

const NETWORK_ERROR_COPY = "Can't reach the server. Check that the local stack is running and try again.";
const SERVER_ERROR_COPY = "The server couldn't complete this request. Try again.";
const READINESS_RECOVERED_COPY = "The system is ready for registration and sign in.";

function readCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const parts = document.cookie.split(";").map((entry) => entry.trim());
  const match = parts.find((entry) => entry.startsWith("__Host-simpagent_csrf="));
  if (!match) {
    return null;
  }

  return decodeURIComponent(match.slice("__Host-simpagent_csrf=".length));
}

function normalizePasswordForClient(value: string): string {
  return value.normalize("NFC");
}

function buildEmptyErrors(): FormErrors {
  return { email: null, password: null, confirmPassword: null, inviteCode: null };
}

function labelForState(state: SessionState): string {
  switch (state) {
    case "checking_session":
      return "Checking your session";
    case "registration_accepted":
      return "Request received";
    case "authenticated":
      return "You are signed in";
    case "session_expired":
      return "Session ended";
    case "core_not_ready":
      return "System not ready";
    case "anonymous_register":
      return "Create your account";
    case "anonymous_login":
    default:
      return "Sign in to SimpAgent";
  }
}

function bodyForState(state: SessionState): string {
  switch (state) {
    case "checking_session":
      return "SimpAgent is restoring a protected session on this device.";
    case "registration_accepted":
      return "If this address is accepted, you can continue directly to sign in.";
    case "authenticated":
      return "Your protected workspace is ready.";
    case "session_expired":
      return "Your session is no longer valid. Sign in again to continue.";
    case "core_not_ready":
      return "Sign in is temporarily unavailable. Wait for the local stack to finish starting, then try again.";
    case "anonymous_register":
      return "New accounts start with the Standard User role. Roles and scopes are assigned by the server, not chosen here.";
    case "anonymous_login":
    default:
      return "Use your local account to enter the protected SimpAgent workspace.";
  }
}

function titleForViewModel(viewModel: ShellViewModel): string {
  if (viewModel.sessionState === "authenticated") {
    return "Workspace | SimpAgent";
  }

  if (
    viewModel.sessionState === "core_not_ready" ||
    toAggregateUiState(viewModel.readiness) === "not_ready" ||
    toAggregateUiState(viewModel.readiness) === "disconnected"
  ) {
    return "System not ready | SimpAgent";
  }

  return viewModel.authMode === "register"
    ? "Create account | SimpAgent"
    : "Sign in | SimpAgent";
}

export function AccountAccessShell({ initialMode, demoConfig }: AccountAccessShellProps) {
  const controller = useMemo(
    () => new AuthSessionController(initialMode, { getCsrfToken: readCsrfToken }),
    [initialMode],
  );

  const [viewModel, setViewModel] = useState<ShellViewModel>(controller.snapshot);
  const [formFields, setFormFields] = useState<FormFields>({
    email: "",
    password: "",
    confirmPassword: "",
    inviteCode: "",
  });
  const [formErrors, setFormErrors] = useState<FormErrors>(buildEmptyErrors());
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCorrelationId, setErrorCorrelationId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReadinessLoading, setIsReadinessLoading] = useState(true);
  const [isReadinessRefreshing, setIsReadinessRefreshing] = useState(false);
  const [logoutRetryVisible, setLogoutRetryVisible] = useState(false);
  const submitButtonRef = useRef<HTMLButtonElement | null>(null);
  const viewModelRef = useRef(viewModel);

  useEffect(() => {
    viewModelRef.current = viewModel;
  }, [viewModel]);

  useEffect(() => {
    document.title = titleForViewModel(viewModel);
  }, [viewModel]);

  useEffect(() => {
    if (!announcement) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setAnnouncement(null), 6000);
    return () => window.clearTimeout(timeoutId);
  }, [announcement]);

  const refreshReadiness = useCallback(
    async (manual: boolean) => {
      if (manual) {
        setIsReadinessRefreshing(true);
      }
      const previouslyEnabled = formsEnabled(viewModelRef.current.readiness);
      const next = await controller.loadReadiness();
      setViewModel(next);
      const nextEnabled = formsEnabled(next.readiness);
      if (!previouslyEnabled && nextEnabled) {
        setAnnouncement(READINESS_RECOVERED_COPY);
      }
      if (manual) {
        setIsReadinessRefreshing(false);
      }
      setIsReadinessLoading(false);
      return next;
    },
    [controller],
  );

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const readiness = await refreshReadiness(false);
      if (cancelled) {
        return;
      }
      setViewModel(readiness);
      const restored = await controller.restoreSession();
      if (cancelled) {
        return;
      }
      setViewModel(restored);
      setIsReadinessLoading(false);
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [controller, refreshReadiness]);

  useEffect(() => {
    const intervalMs = 60_000;
    let intervalId: number | undefined;

    const startPolling = () => {
      if (document.visibilityState !== "visible") {
        return;
      }
      intervalId = window.setInterval(() => {
        void refreshReadiness(false);
      }, intervalMs);
    };

    const stopPolling = () => {
      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = undefined;
      }
    };

    const handleVisibilityChange = () => {
      stopPolling();
      if (document.visibilityState === "visible") {
        void refreshReadiness(false);
        startPolling();
      }
    };

    startPolling();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refreshReadiness]);

  function clearFormState() {
    setErrorMessage(null);
    setErrorCorrelationId(null);
    setFormErrors(buildEmptyErrors());
  }

  function clearPasswords() {
    setFormFields((current) => ({ ...current, password: "", confirmPassword: "" }));
  }

  function validateLogin(): boolean {
    const nextErrors = buildEmptyErrors();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formFields.email.trim())) {
      nextErrors.email = "Enter a valid email address.";
    }
    if (!formFields.password) {
      nextErrors.password = "Enter your password.";
    }
    setFormErrors(nextErrors);
    return !nextErrors.email && !nextErrors.password;
  }

  function validateRegister(): boolean {
    const nextErrors = buildEmptyErrors();
    const normalizedPassword = normalizePasswordForClient(formFields.password);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formFields.email.trim())) {
      nextErrors.email = "Enter a valid email address.";
    }
    if (!formFields.password) {
      nextErrors.password = "Enter a password.";
    } else if (normalizedPassword.length < 15) {
      nextErrors.password = "Password must contain at least 15 characters.";
    } else if (normalizedPassword.length > 128) {
      nextErrors.password = "Password must not exceed 128 characters.";
    }
    if (formFields.confirmPassword !== formFields.password) {
      nextErrors.confirmPassword = "The passwords do not match.";
    }
    setFormErrors(nextErrors);
    return !nextErrors.email && !nextErrors.password && !nextErrors.confirmPassword;
  }

  async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFormState();
    setAnnouncement(null);
    if (!validateLogin()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const nextState = await controller.login({
        email: formFields.email,
        password: formFields.password,
      });
      setViewModel(nextState);
      clearPasswords();
      setLogoutRetryVisible(false);
    } catch (error) {
      clearPasswords();
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage(NETWORK_ERROR_COPY);
      }
      const correlationId =
        typeof error === "object" && error !== null && "correlationId" in error
          ? String((error as { correlationId?: string | null }).correlationId ?? "") || null
          : null;
      setErrorCorrelationId(correlationId);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRegisterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearFormState();
    setAnnouncement(null);
    if (!validateRegister()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const nextState = await controller.register({
        email: formFields.email,
        password: formFields.password,
        inviteCode: formFields.inviteCode,
      });
      setViewModel(nextState);
      clearPasswords();
      setLogoutRetryVisible(false);
    } catch (error) {
      clearPasswords();
      const message = error instanceof Error ? error.message : SERVER_ERROR_COPY;
      setErrorMessage(message);
      const correlationId =
        typeof error === "object" && error !== null && "correlationId" in error
          ? String((error as { correlationId?: string | null }).correlationId ?? "") || null
          : null;
      setErrorCorrelationId(correlationId);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    setIsSubmitting(true);
    clearFormState();
    setAnnouncement(null);
    const nextState = await controller.logout();
    setViewModel(nextState);
    const failed =
      nextState.globalMessage ===
      "Sign out could not be completed. Check your connection and try again.";
    setLogoutRetryVisible(failed);
    setIsSubmitting(false);
  }

  function switchMode(mode: "login" | "register") {
    clearFormState();
    clearPasswords();
    setAnnouncement(null);
    setLogoutRetryVisible(false);
    setViewModel(controller.setAuthMode(mode));
  }

  function handleGoToLogin() {
    switchMode("login");
  }

  function handleOAuthStart(provider: OAuthProviderId) {
    clearFormState();
    setAnnouncement(null);
    void beginOAuth(provider).catch(() => {
      setAnnouncement("Secure sign-in proof could not be prepared. Try again.");
    });
  }

  function fillDemoAccount(kind: "user" | "admin") {
    if (!demoConfig.enabled) {
      return;
    }

    if (kind === "user") {
      setFormFields({
        email: demoConfig.userEmail,
        password: demoConfig.userPassword,
        confirmPassword: "",
        inviteCode: "",
      });
      setAnnouncement("Standard user demo account filled.");
    } else {
      setFormFields({
        email: demoConfig.adminEmail,
        password: demoConfig.adminPassword,
        confirmPassword: "",
        inviteCode: "",
      });
      setAnnouncement("Administrator demo account filled.");
    }

    window.setTimeout(() => submitButtonRef.current?.focus(), 0);
  }

  const formsAreEnabled = formsEnabled(viewModel.readiness);
  const disabled = !formsAreEnabled || isSubmitting;
  const combinedGlobalMessage = announcement ?? viewModel.globalMessage;
  const combinedCorrelationId = errorCorrelationId ?? viewModel.correlationId;
  const oauthProviders = [
    oauthProviderState(viewModel.readiness, "google"),
    oauthProviderState(viewModel.readiness, "github"),
  ];

  if (viewModel.sessionState === "authenticated" && viewModel.currentUser) {
    return (
      <ChatWorkspace
        controller={controller}
        currentUser={viewModel.currentUser}
        onSessionExpired={() => setViewModel(controller.snapshot)}
        onLogout={handleLogout}
      />
    );
  }

  const loginForm = (
    <div className="space-y-6">
      <div className="space-y-2.5">
        <label htmlFor="login-email" className="text-sm font-medium text-foreground">
          Email Address
        </label>
        <input
          id="login-email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={formFields.email}
          disabled={disabled}
          onChange={(event) => setFormFields((current) => ({ ...current, email: event.target.value }))}
          className="flex h-11 w-full rounded-md bg-white border border-gray-300 px-3 py-2 text-foreground placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
        />
        {formErrors.email && <p className="text-sm text-destructive">{formErrors.email}</p>}
      </div>
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <label htmlFor="login-password" className="text-sm font-medium text-foreground">
            Password
          </label>
        </div>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={formFields.password}
          disabled={disabled}
          onChange={(event) => setFormFields((current) => ({ ...current, password: event.target.value }))}
          className="flex h-11 w-full rounded-md bg-white border border-gray-300 px-3 py-2 text-foreground placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
        />
        {formErrors.password && <p className="text-sm text-destructive">{formErrors.password}</p>}
      </div>
      <button
        ref={submitButtonRef}
        type="submit"
        disabled={disabled}
        className="w-full h-11 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-md font-semibold transition-all duration-200 mt-3 flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            Signing in...
          </>
        ) : (
          <>
            <span>Sign in</span>
            <span className="text-lg">✦</span>
          </>
        )}
      </button>
      <p className="text-center text-sm text-muted-foreground mt-4">
        Need an account?{" "}
        <button type="button" onClick={() => switchMode("register")} className="text-blue-600 hover:text-blue-700 font-semibold transition-colors">
          Create account
        </button>
      </p>
    </div>
  );

  const registerForm = (
    <div className="space-y-6">
      <div className="space-y-2.5">
        <label htmlFor="register-email" className="text-sm font-medium text-foreground">
          Email Address
        </label>
        <input
          id="register-email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={formFields.email}
          disabled={disabled}
          onChange={(event) => setFormFields((current) => ({ ...current, email: event.target.value }))}
          className="flex h-11 w-full rounded-md bg-white border border-gray-300 px-3 py-2 text-foreground placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
        />
        {formErrors.email && <p className="text-sm text-destructive">{formErrors.email}</p>}
      </div>
      <div className="space-y-2.5">
        <label htmlFor="register-password" className="text-sm font-medium text-foreground">
          Password
        </label>
        <input
          id="register-password"
          type="password"
          autoComplete="new-password"
          placeholder="••••••••"
          value={formFields.password}
          disabled={disabled}
          onChange={(event) => setFormFields((current) => ({ ...current, password: event.target.value }))}
          className="flex h-11 w-full rounded-md bg-white border border-gray-300 px-3 py-2 text-foreground placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
        />
        <p className="text-xs text-muted-foreground">Use 15 to 128 characters.</p>
        {formErrors.password && <p className="text-sm text-destructive">{formErrors.password}</p>}
      </div>
      <div className="space-y-2.5">
        <label htmlFor="register-confirm-password" className="text-sm font-medium text-foreground">
          Confirm password
        </label>
        <input
          id="register-confirm-password"
          type="password"
          autoComplete="new-password"
          placeholder="••••••••"
          value={formFields.confirmPassword}
          disabled={disabled}
          onChange={(event) => setFormFields((current) => ({ ...current, confirmPassword: event.target.value }))}
          className="flex h-11 w-full rounded-md bg-white border border-gray-300 px-3 py-2 text-foreground placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
        />
        {formErrors.confirmPassword && <p className="text-sm text-destructive">{formErrors.confirmPassword}</p>}
      </div>
      <div className="space-y-2.5">
        <label htmlFor="register-invite-code" className="text-sm font-medium text-foreground">
          Invite code
        </label>
        <input
          id="register-invite-code"
          type="password"
          autoComplete="one-time-code"
          placeholder="Required for public deployment"
          value={formFields.inviteCode}
          disabled={disabled}
          onChange={(event) => setFormFields((current) => ({ ...current, inviteCode: event.target.value }))}
          className="flex h-11 w-full rounded-md bg-white border border-gray-300 px-3 py-2 text-foreground placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-500/30 transition-all"
        />
        {formErrors.inviteCode && <p className="text-sm text-destructive">{formErrors.inviteCode}</p>}
      </div>
      <button
        type="submit"
        disabled={disabled}
        className="w-full h-11 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-md font-semibold transition-all duration-200 mt-3 flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            Sending request...
          </>
        ) : (
          <>
            <span>Create account</span>
            <span className="text-lg">✦</span>
          </>
        )}
      </button>
      <p className="text-center text-sm text-muted-foreground mt-4">
        Already have an account?{" "}
        <button type="button" onClick={() => switchMode("login")} className="text-blue-600 hover:text-blue-700 font-semibold transition-colors">
          Sign in
        </button>
      </p>
    </div>
  );

  return (
    <main className="min-h-[100dvh] relative overflow-hidden bg-background px-4 py-8">
      {/* Subtle gradient background accents */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-100/30 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-cyan-100/20 rounded-full blur-3xl"></div>
      </div>

      <div className="relative min-h-[100dvh] flex flex-col items-center justify-center">
        <a className="sr-only focus:not-sr-only" href="#account-content">
          Skip to account access
        </a>
        <div className="w-full max-w-md">
          <AuthCard
            sessionState={viewModel.sessionState}
            authMode={viewModel.authMode}
            heading={labelForState(viewModel.sessionState)}
            body={bodyForState(viewModel.sessionState)}
            disabled={!formsAreEnabled}
            isSubmitting={isSubmitting}
            currentUser={viewModel.currentUser}
            logoutRetryVisible={logoutRetryVisible}
            formContent={viewModel.authMode === "login" ? loginForm : registerForm}
            globalMessage={combinedGlobalMessage}
            errorMessage={errorMessage}
            correlationId={combinedCorrelationId}
            oauthProviders={oauthProviders}
            onOAuthStart={handleOAuthStart}
            onModeChange={switchMode}
            onLoginSubmit={handleLoginSubmit}
            onRegisterSubmit={handleRegisterSubmit}
            onLogout={handleLogout}
            onGoToLogin={handleGoToLogin}
            scopeLabels={SCOPE_LABELS}
            demoEnabled={demoConfig.enabled}
            onFillDemoUser={() => fillDemoAccount("user")}
            onFillDemoAdmin={() => fillDemoAccount("admin")}
          />
          <div className="mt-8 flex flex-col gap-4">
            <SecuritySummary />
            <PlatformStatus
              readiness={viewModel.readiness}
              isLoading={isReadinessLoading}
              isRefreshing={isReadinessRefreshing}
              onRefresh={() => void refreshReadiness(true)}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
