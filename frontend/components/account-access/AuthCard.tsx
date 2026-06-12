import React from "react";
import type { FormEvent, ReactNode } from "react";

import type { CurrentUser, SessionState } from "@/lib/auth-session";

import { ActionButton } from "./ActionButton";
import { AuthModeSwitch } from "./AuthModeSwitch";
import { CurrentUserCard } from "./CurrentUserCard";
import { DemoAccountPanel } from "./DemoAccountPanel";
import { InlineAlert } from "./InlineAlert";

type AuthCardProps = {
  sessionState: SessionState;
  authMode: "login" | "register";
  heading: string;
  body: string;
  disabled: boolean;
  isSubmitting: boolean;
  currentUser: CurrentUser | null;
  logoutRetryVisible: boolean;
  formContent: ReactNode;
  globalMessage: string | null;
  errorMessage: string | null;
  correlationId: string | null;
  onModeChange: (mode: "login" | "register") => void;
  onLoginSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRegisterSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onLogout: () => void;
  onGoToLogin: () => void;
  scopeLabels: Record<string, string>;
  demoEnabled: boolean;
  onFillDemoUser: () => void;
  onFillDemoAdmin: () => void;
};

function alertForState(sessionState: SessionState, globalMessage: string | null, correlationId: string | null) {
  if (sessionState === "session_expired") {
    return {
      tone: "warning" as const,
      title: "Session ended",
      message: "Your session is no longer valid. Sign in again to continue.",
      detail: correlationId ? `Reference code: ${correlationId}` : null,
      urgent: true,
    };
  }

  if (globalMessage === "You signed out of this session.") {
    return {
      tone: "success" as const,
      title: undefined,
      message: globalMessage,
      detail: null,
      urgent: false,
    };
  }

  if (globalMessage === "The system is ready for registration and sign in.") {
    return {
      tone: "success" as const,
      title: undefined,
      message: globalMessage,
      detail: null,
      urgent: false,
    };
  }

  if (globalMessage) {
    return {
      tone: "info" as const,
      title: undefined,
      message: globalMessage,
      detail: correlationId ? `Reference code: ${correlationId}` : null,
      urgent: false,
    };
  }

  return null;
}

export function AuthCard({
  sessionState,
  authMode,
  heading,
  body,
  disabled,
  isSubmitting,
  currentUser,
  logoutRetryVisible,
  formContent,
  globalMessage,
  errorMessage,
  correlationId,
  onModeChange,
  onLoginSubmit,
  onRegisterSubmit,
  onLogout,
  onGoToLogin,
  scopeLabels,
  demoEnabled,
  onFillDemoUser,
  onFillDemoAdmin,
}: AuthCardProps) {
  const alert = alertForState(sessionState, globalMessage, correlationId);

  return (
    <section className="card-shell" id="account-content" aria-live="polite">
      <div className="card-intro">
        <h2 className="section-heading">{heading}</h2>
        <p className="body-copy max-copy">{body}</p>
      </div>

      {alert ? (
        <InlineAlert
          tone={alert.tone}
          title={alert.title}
          message={alert.message}
          detail={alert.detail}
          urgent={alert.urgent}
        />
      ) : null}
      {errorMessage ? <InlineAlert tone="danger" message={errorMessage} urgent /> : null}

      {sessionState === "checking_session" ? (
        <div className="checking-state" aria-busy="true">
          <div className="spinner" aria-hidden="true" />
          <span className="body-copy">Please wait a moment.</span>
        </div>
      ) : null}

      {sessionState === "authenticated" && currentUser ? (
        <CurrentUserCard
          user={currentUser}
          scopeLabels={scopeLabels}
          onLogout={onLogout}
          logoutLabel={isSubmitting ? "Signing out..." : logoutRetryVisible ? "Try sign out again" : "Sign out"}
          isSubmitting={isSubmitting}
          logoutRetryVisible={logoutRetryVisible}
        />
      ) : null}

      {sessionState === "registration_accepted" ? (
        <ActionButton type="button" onClick={onGoToLogin}>
          Continue to sign in
        </ActionButton>
      ) : null}

      {sessionState !== "checking_session" && sessionState !== "authenticated" && sessionState !== "registration_accepted" ? (
        <>
          <AuthModeSwitch mode={authMode} onChange={onModeChange} />
          {authMode === "login" ? (
            <form className="auth-form" onSubmit={onLoginSubmit} noValidate>
              {formContent}
            </form>
          ) : (
            <form className="auth-form" onSubmit={onRegisterSubmit} noValidate>
              {formContent}
            </form>
          )}
          {demoEnabled && authMode === "login" && !disabled ? (
            <DemoAccountPanel onFillUser={onFillDemoUser} onFillAdmin={onFillDemoAdmin} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
