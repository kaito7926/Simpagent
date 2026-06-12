"use client";

import React, { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { DemoConfig } from "@/lib/demo-config";
import {
  AuthSessionController,
  type SessionState,
  type ShellViewModel,
} from "@/lib/auth-session";
import { formsEnabled, toAggregateUiState } from "@/lib/readiness";

import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { ActionButton } from "./ActionButton";
import { AuthCard } from "./AuthCard";
import { BrandLockup } from "./BrandLockup";
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
};

type FormErrors = {
  email: string | null;
  password: string | null;
  confirmPassword: string | null;
};

const SCOPE_LABELS: Record<string, string> = {
  "chat:read": "Read conversations",
  "chat:write": "Create and update conversations",
  "tool:websearch": "Use web search",
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
  return { email: null, password: null, confirmPassword: null };
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
      return "Create account";
    case "anonymous_login":
    default:
      return "Sign in to SimpAgent";
  }
}

function bodyForState(state: SessionState): string {
  switch (state) {
    case "checking_session":
      return "SimpAgent is checking for a protected session on this device.";
    case "registration_accepted":
      return "If this address can be registered, you can continue to sign in.";
    case "authenticated":
      return "Your protected workspace is ready.";
    case "session_expired":
      return "Your session is no longer valid. Sign in again to continue.";
    case "core_not_ready":
      return "Sign in is temporarily unavailable. Wait for the local stack to finish starting, then try again.";
    case "anonymous_register":
      return "New accounts start with the Standard User role. Roles and scopes are not selectable here.";
    case "anonymous_login":
    default:
      return "Use your local account to open a protected session.";
  }
}

function titleForViewModel(viewModel: ShellViewModel): string {
  if (viewModel.sessionState === "authenticated") {
    return "Private chat | SimpAgent";
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

  function fillDemoAccount(kind: "user" | "admin") {
    if (!demoConfig.enabled) {
      return;
    }

    if (kind === "user") {
      setFormFields({
        email: demoConfig.userEmail,
        password: demoConfig.userPassword,
        confirmPassword: "",
      });
      setAnnouncement("Standard User demo account filled.");
    } else {
      setFormFields({
        email: demoConfig.adminEmail,
        password: demoConfig.adminPassword,
        confirmPassword: "",
      });
      setAnnouncement("Administrator demo account filled.");
    }

    window.setTimeout(() => submitButtonRef.current?.focus(), 0);
  }

  const formsAreEnabled = formsEnabled(viewModel.readiness);
  const disabled = !formsAreEnabled || isSubmitting;
  const combinedGlobalMessage = announcement ?? viewModel.globalMessage;
  const combinedCorrelationId = errorCorrelationId ?? viewModel.correlationId;

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
    <>
      <FormField
        id="login-email"
        label="Email"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={formFields.email}
        disabled={disabled}
        error={formErrors.email}
        onChange={(event) => setFormFields((current) => ({ ...current, email: event.target.value }))}
      />
      <PasswordField
        id="login-password"
        label="Password"
        autoComplete="current-password"
        value={formFields.password}
        disabled={disabled}
        error={formErrors.password}
        onChange={(value) => setFormFields((current) => ({ ...current, password: value }))}
      />
      <ActionButton ref={submitButtonRef} type="submit" disabled={disabled}>
        {isSubmitting ? "Signing in..." : "Sign in"}
      </ActionButton>
      <p className="mode-prompt">
        <span>Need an account?</span>
        <button className="text-link-button" type="button" onClick={() => switchMode("register")}>
          Create account
        </button>
      </p>
    </>
  );

  const registerForm = (
    <>
      <FormField
        id="register-email"
        label="Email"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={formFields.email}
        disabled={disabled}
        error={formErrors.email}
        onChange={(event) => setFormFields((current) => ({ ...current, email: event.target.value }))}
      />
      <PasswordField
        id="register-password"
        label="Password"
        autoComplete="new-password"
        value={formFields.password}
        disabled={disabled}
        hint="Use 15 to 128 characters. Spaces are allowed; uppercase letters, numbers, and symbols are optional."
        error={formErrors.password}
        onChange={(value) => setFormFields((current) => ({ ...current, password: value }))}
      />
      <PasswordField
        id="register-confirm-password"
        label="Confirm password"
        autoComplete="new-password"
        value={formFields.confirmPassword}
        disabled={disabled}
        error={formErrors.confirmPassword}
        onChange={(value) =>
          setFormFields((current) => ({ ...current, confirmPassword: value }))
        }
      />
      <ActionButton type="submit" disabled={disabled}>
        {isSubmitting ? "Sending request..." : "Create account"}
      </ActionButton>
      <p className="mode-prompt">
        <span>Already have an account?</span>
        <button className="text-link-button" type="button" onClick={() => switchMode("login")}>
          Sign in
        </button>
      </p>
    </>
  );

  return (
    <main className="page-shell">
      <a className="skip-link" href="#account-content">
        Skip to account access
      </a>
      <section className="layout-grid">
        <div className="context-column">
          <BrandLockup authenticated={viewModel.sessionState === "authenticated"} />
          <SecuritySummary />
          <PlatformStatus
            readiness={viewModel.readiness}
            isLoading={isReadinessLoading}
            isRefreshing={isReadinessRefreshing}
            onRefresh={() => void refreshReadiness(true)}
          />
        </div>

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
      </section>
    </main>
  );
}
