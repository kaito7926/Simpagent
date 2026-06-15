import React from "react";
import type { FormEvent, ReactNode } from "react";
import Image from "next/image";

import { Card } from "@/components/ui/card";

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
      centered: true,
    };
  }

  if (globalMessage === "The system is ready for registration and sign in.") {
    return {
      tone: "success" as const,
      title: undefined,
      message: globalMessage,
      detail: null,
      urgent: false,
      centered: false,
    };
  }

  if (globalMessage) {
    return {
      tone: "info" as const,
      title: undefined,
      message: globalMessage,
      detail: correlationId ? `Reference code: ${correlationId}` : null,
      urgent: false,
      centered: false,
    };
  }

  return null;
}

function OAuthIcon({ provider }: { provider: "google" | "github" }) {
  if (provider === "google") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" className="oauth-template-icon-svg">
        <path
          fill="currentColor"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="currentColor"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="currentColor"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="currentColor"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" fill="currentColor" viewBox="0 0 20 20" className="oauth-template-icon-svg">
      <path
        clipRule="evenodd"
        d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.868-.013-1.703-2.782.603-3.369-1.343-3.369-1.343-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.002.07 1.527 1.03 1.527 1.03.89 1.529 2.341 1.544 2.914 1.19.092-.926.35-1.557.636-1.914-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.024A9.578 9.578 0 0110 4.836c.85.004 1.705.114 2.504.336 1.909-1.293 2.747-1.024 2.747-1.024.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C17.138 18.194 20 14.44 20 10.017 20 4.484 15.522 0 10 0z"
        fillRule="evenodd"
      />
    </svg>
  );
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
    <div className="w-full max-w-md" id="account-content" aria-live="polite">
      <div className="mb-12 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 mb-6 overflow-hidden rounded-full border border-zinc-200 bg-white shadow-sm">
          <Image
            alt="SimpAgent logo"
            className="h-11 w-11 object-contain"
            height={44}
            priority
            src="/brand/auroraguard-logo-mark-white.png"
            width={44}
          />
        </div>

        <h1 className="text-4xl font-bold text-foreground mb-1 tracking-tight">
          SimpAgent
        </h1>
        <p className="text-base text-muted-foreground max-w-sm mx-auto">
          Intelligent. Secure. Always by your side.
        </p>
      </div>

      <div className="space-y-6">
        {alert ? (
          <InlineAlert
            tone={alert.tone}
            title={alert.title}
            message={alert.message}
            detail={alert.detail}
            urgent={alert.urgent}
            centered={alert.centered}
          />
        ) : null}
        {errorMessage ? <InlineAlert tone="danger" message={errorMessage} urgent /> : null}

        {sessionState === "checking_session" ? (
          <div className="flex flex-col items-center gap-4 py-8" aria-busy="true">
            <span className="w-8 h-8 border-4 border-blue-600/30 border-t-blue-600 rounded-full animate-spin"></span>
            <span className="text-sm text-muted-foreground">Please wait a moment.</span>
          </div>
        ) : null}

        {sessionState === "authenticated" && currentUser ? (
          <CurrentUserCard
            user={currentUser}
            scopeLabels={scopeLabels}
            onLogout={onLogout}
            logoutLabel={
              isSubmitting
                ? "Signing out..."
                : logoutRetryVisible
                  ? "Try sign out again"
                  : "Sign out"
            }
            isSubmitting={isSubmitting}
            logoutRetryVisible={logoutRetryVisible}
          />
        ) : null}

        {sessionState === "registration_accepted" ? (
          <button
            type="button"
            onClick={onGoToLogin}
            className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-semibold transition-all"
          >
            Continue to sign in
          </button>
        ) : null}

        {sessionState !== "checking_session" &&
        sessionState !== "authenticated" &&
        sessionState !== "registration_accepted" ? (
          <>
            <div className="space-y-3">
              <button type="button" disabled className="w-full h-11 bg-gray-50 flex items-center justify-center border border-gray-300 text-foreground rounded-md disabled:opacity-50 transition-all">
                <span className="mr-3 text-gray-700"><OAuthIcon provider="google" /></span>
                Continue with Google
              </button>
              <button type="button" disabled className="w-full h-11 bg-gray-50 flex items-center justify-center border border-gray-300 text-foreground rounded-md disabled:opacity-50 transition-all">
                <span className="mr-3 text-gray-700"><OAuthIcon provider="github" /></span>
                Continue with GitHub
              </button>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-3 text-muted-foreground font-medium">
                  Or sign in with email
                </span>
              </div>
            </div>

            {authMode === "login" ? (
              <form onSubmit={onLoginSubmit} noValidate>
                {formContent}
              </form>
            ) : (
              <form onSubmit={onRegisterSubmit} noValidate>
                {formContent}
              </form>
            )}

            {demoEnabled && authMode === "login" && !disabled ? (
              <DemoAccountPanel onFillUser={onFillDemoUser} onFillAdmin={onFillDemoAdmin} />
            ) : null}

            <p className="text-center text-xs text-muted-foreground mt-8">
              By signing in, you agree to our{" "}
              <a href="#" className="text-blue-600/70 hover:text-blue-700 transition-colors">
                Terms of Service
              </a>
              {" "}and{" "}
              <a href="#" className="text-blue-600/70 hover:text-blue-700 transition-colors">
                Privacy Policy
              </a>
            </p>
          </>
        ) : null}
      </div>
    </div>
  );
}
