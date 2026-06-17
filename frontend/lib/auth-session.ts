import { ApiError, requestJson, requestNoContent } from "@/lib/api";

export type AuthMode = "login" | "register";
export type SessionState =
  | "checking_session"
  | "anonymous_login"
  | "anonymous_register"
  | "registration_accepted"
  | "authenticated"
  | "session_expired"
  | "core_not_ready";

export type CurrentUser = {
  id: string;
  email: string;
  role: "user" | "admin";
  scopes: string[];
  is_active: boolean;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type RegisterAcceptedResponse = {
  status: string;
  message: string;
};

export type ReadinessComponentState =
  | "ready"
  | "foundation_ready"
  | "unconfigured"
  | "model_unavailable"
  | "unavailable"
  | "out_of_date"
  | "unknown";

export type ReadinessResponse = {
  status: "ready" | "degraded" | "not_ready";
  components: {
    database: ReadinessComponentState;
    migrations: ReadinessComponentState;
    llm: ReadinessComponentState;
    search: ReadinessComponentState;
    sandbox: ReadinessComponentState;
    oauth_google?: ReadinessComponentState;
    oauth_github?: ReadinessComponentState;
  };
};

export type OAuthProviderId = "google" | "github";

export type OAuthProviderState = {
  provider: OAuthProviderId;
  label: string;
  enabled: boolean;
  unavailableLabel: string | null;
};

type OAuthStorageTrap = {
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
};

export type BeginOAuthDependencies = {
  navigate?: (url: string) => void;
  localStorage?: OAuthStorageTrap;
  sessionStorage?: OAuthStorageTrap;
};

export type DemoConfig = {
  enabled: boolean;
  userEmail?: string;
  userPassword?: string;
  adminEmail?: string;
  adminPassword?: string;
};

export type ShellViewModel = {
  authMode: AuthMode;
  sessionState: SessionState;
  currentUser: CurrentUser | null;
  accessToken: string | null;
  readiness: ReadinessResponse | null;
  globalMessage: string | null;
  correlationId: string | null;
};

export type RegisterPayload = {
  email: string;
  password: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type AuthSessionDependencies = {
  fetchImpl?: typeof fetch;
  getCsrfToken?: () => string | null;
};

const DEFAULT_VIEW_MODEL: ShellViewModel = {
  authMode: "login",
  sessionState: "checking_session",
  currentUser: null,
  accessToken: null,
  readiness: null,
  globalMessage: null,
  correlationId: null,
};

function parseMode(mode: string | null | undefined): AuthMode {
  return mode === "register" ? "register" : "login";
}

function anonymousStateForMode(mode: AuthMode): SessionState {
  return mode === "register" ? "anonymous_register" : "anonymous_login";
}

function isKnownRole(role: string): role is "user" | "admin" {
  return role === "user" || role === "admin";
}

const KNOWN_SCOPES = new Set([
  "chat:read",
  "chat:write",
  "tool:websearch",
  "tool:python",
  "admin:read",
  "admin:write",
]);

function isKnownUser(user: CurrentUser): boolean {
  return isKnownRole(user.role) && user.scopes.every((scope) => KNOWN_SCOPES.has(scope));
}

function defaultHeaders(accessToken?: string | null): HeadersInit {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : {};
}

const OAUTH_START_ROUTES: Record<OAuthProviderId, string> = {
  google: "/api/auth/oauth/google/start",
  github: "/api/auth/oauth/github/start",
};

export function beginOAuth(provider: OAuthProviderId, deps: BeginOAuthDependencies = {}): void {
  const startUrl = OAUTH_START_ROUTES[provider];
  const navigate =
    deps.navigate ??
    ((url: string) => {
      window.location.assign(url);
    });

  navigate(startUrl);
}

export class AuthSessionController {
  private readonly fetchImpl: typeof fetch;
  private readonly getCsrfToken: () => string | null;
  private refreshPromise: Promise<string | null> | null = null;
  private model: ShellViewModel;

  constructor(mode: string | null | undefined, deps: AuthSessionDependencies = {}) {
    this.fetchImpl = deps.fetchImpl ?? fetch;
    this.getCsrfToken = deps.getCsrfToken ?? (() => null);
    const authMode = parseMode(mode);
    this.model = {
      ...DEFAULT_VIEW_MODEL,
      authMode,
      sessionState: anonymousStateForMode(authMode),
    };
  }

  get snapshot(): ShellViewModel {
    return { ...this.model };
  }

  setAuthMode(mode: AuthMode): ShellViewModel {
    this.model = {
      ...this.model,
      authMode: mode,
      sessionState:
        this.model.sessionState === "registration_accepted"
          ? "registration_accepted"
          : anonymousStateForMode(mode),
      globalMessage: null,
      correlationId: null,
    };
    return this.snapshot;
  }

  async loadReadiness(): Promise<ShellViewModel> {
    try {
      const readiness = await requestJson<ReadinessResponse>(
        "/ready",
        {
          method: "GET",
          cache: "no-store",
          credentials: "include",
        },
        this.fetchImpl,
      );

      const blocked = readiness.status === "not_ready";
      this.model = {
        ...this.model,
        readiness,
        sessionState: blocked ? "core_not_ready" : this.model.sessionState,
        globalMessage: null,
        correlationId: null,
      };
    } catch {
      this.model = {
        ...this.model,
        readiness: null,
        sessionState: "core_not_ready",
        globalMessage: "Can't reach the server. Check that the local stack is running and try again.",
        correlationId: null,
      };
    }

    return this.snapshot;
  }

  async restoreSession(): Promise<ShellViewModel> {
    this.model = {
      ...this.model,
      sessionState: "checking_session",
      globalMessage: null,
      correlationId: null,
    };

    const accessToken = await this.refreshAccessToken({ suppressFailureMessage: true });
    if (!accessToken) {
      this.model = {
        ...this.model,
        accessToken: null,
        currentUser: null,
        sessionState: anonymousStateForMode(this.model.authMode),
      };
      return this.snapshot;
    }

    return this.loadCurrentUser({ preserveAnonymousOnFailure: true });
  }

  async register(payload: RegisterPayload): Promise<ShellViewModel> {
    await requestJson<RegisterAcceptedResponse>(
      "/api/auth/register",
      {
        method: "POST",
        cache: "no-store",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
      this.fetchImpl,
    );

    this.model = {
      ...this.model,
      sessionState: "registration_accepted",
      globalMessage: null,
      correlationId: null,
    };

    return this.snapshot;
  }

  async login(payload: LoginPayload): Promise<ShellViewModel> {
    const token = await requestJson<TokenResponse>(
      "/api/auth/login",
      {
        method: "POST",
        cache: "no-store",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      },
      this.fetchImpl,
    );

    this.model = {
      ...this.model,
      accessToken: token.access_token,
      globalMessage: null,
      correlationId: null,
    };

    return this.loadCurrentUser({ preserveAnonymousOnFailure: false });
  }

  async logout(): Promise<ShellViewModel> {
    try {
      await requestNoContent(
        "/api/auth/logout",
        {
          method: "POST",
          cache: "no-store",
          credentials: "include",
          headers: {
            "X-CSRF-Token": this.getCsrfToken() ?? "",
          },
        },
        this.fetchImpl,
      );
    } catch (error) {
      if (error instanceof ApiError) {
        this.model = {
          ...this.model,
          globalMessage: "Sign out could not be completed. Check your connection and try again.",
          correlationId: error.correlationId ?? null,
        };
      }
      return this.snapshot;
    }

    this.clearSession();
    this.model = {
      ...this.model,
      sessionState: "anonymous_login",
      authMode: "login",
      globalMessage: "You signed out of this session.",
      correlationId: null,
    };
    return this.snapshot;
  }

  async authorizedJson<T>(input: string, init: RequestInit = {}): Promise<T> {
    return this.requestWithRefresh<T>(input, init);
  }

  private async loadCurrentUser(options: {
    preserveAnonymousOnFailure: boolean;
  }): Promise<ShellViewModel> {
    try {
      const currentUser = await this.requestWithRefresh<CurrentUser>("/api/auth/me", {
        method: "GET",
        cache: "no-store",
      });
      if (!isKnownUser(currentUser)) {
        this.handleSessionEnded();
        return this.snapshot;
      }

      this.model = {
        ...this.model,
        currentUser,
        sessionState: "authenticated",
        globalMessage: null,
        correlationId: null,
      };
      return this.snapshot;
    } catch {
      if (options.preserveAnonymousOnFailure && this.model.accessToken === null) {
        this.model = {
          ...this.model,
          currentUser: null,
          sessionState: anonymousStateForMode(this.model.authMode),
          globalMessage: null,
          correlationId: null,
        };
        return this.snapshot;
      }

      this.handleSessionEnded();
      return this.snapshot;
    }
  }

  private async requestWithRefresh<T>(input: string, init: RequestInit): Promise<T> {
    const firstAttemptToken = this.model.accessToken;
    try {
      return await requestJson<T>(
        input,
        {
          ...init,
          cache: "no-store",
          credentials: "include",
          headers: {
            ...defaultHeaders(firstAttemptToken),
            ...(init.headers ?? {}),
          },
        },
        this.fetchImpl,
      );
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        throw error;
      }

      const refreshedToken = await this.refreshAccessToken({ suppressFailureMessage: false });
      if (!refreshedToken) {
        this.handleSessionEnded(error.correlationId);
        throw error;
      }

      return requestJson<T>(
        input,
        {
          ...init,
          cache: "no-store",
          credentials: "include",
          headers: {
            ...defaultHeaders(refreshedToken),
            ...(init.headers ?? {}),
          },
        },
        this.fetchImpl,
      );
    }
  }

  private async refreshAccessToken(options: {
    suppressFailureMessage: boolean;
  }): Promise<string | null> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const response = await requestJson<TokenResponse>(
          "/api/auth/refresh",
          {
            method: "POST",
            cache: "no-store",
            credentials: "include",
            headers: {
              "X-CSRF-Token": this.getCsrfToken() ?? "",
            },
          },
          this.fetchImpl,
        );

        this.model = {
          ...this.model,
          accessToken: response.access_token,
          correlationId: null,
        };
        return response.access_token;
      } catch (error) {
        this.clearSession();
        if (!options.suppressFailureMessage) {
          const correlationId = error instanceof ApiError ? error.correlationId : null;
          this.handleSessionEnded(correlationId ?? undefined);
        }
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  private clearSession(): void {
    this.model = {
      ...this.model,
      accessToken: null,
      currentUser: null,
    };
  }

  private handleSessionEnded(correlationId?: string): void {
    this.clearSession();
    this.model = {
      ...this.model,
      authMode: "login",
      sessionState: "session_expired",
      globalMessage: "Your session is no longer valid. Sign in again to continue.",
      correlationId: correlationId ?? null,
    };
  }
}
