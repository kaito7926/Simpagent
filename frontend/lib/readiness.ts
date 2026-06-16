import type { OAuthProviderId, OAuthProviderState, ReadinessComponentState, ReadinessResponse } from "@/lib/auth-session";

export const AGGREGATE_STATE_LABELS = {
  loading: "Checking system",
  ready: "Ready",
  degraded: "Limited operation",
  not_ready: "Not ready",
  disconnected: "Can't connect",
} as const;

export const AGGREGATE_STATE_BODIES = {
  loading: "Please wait a moment.",
  ready: "Registration and sign in are available.",
  degraded: "Accounts remain available while some AI services are unconfigured or temporarily unavailable.",
  not_ready: "Sign in is temporarily unavailable. Wait for the local stack to finish starting, then try again.",
  disconnected: "Can't reach the server. Check that the local stack is running and try again.",
} as const;

export const COMPONENT_LABELS = {
  database: "Database",
  migrations: "Database schema",
  llm: "AI chat service",
  search: "Grounded search",
  sandbox: "Limited Python foundation",
  oauth_google: "Google sign-in",
  oauth_github: "GitHub sign-in",
} as const;

export const COMPONENT_STATE_LABELS: Record<ReadinessComponentState | "unknown_state", string> = {
  ready: "Ready",
  foundation_ready: "Foundation ready",
  unconfigured: "Unconfigured",
  model_unavailable: "Model unavailable",
  unavailable: "Unavailable",
  out_of_date: "Out of date",
  unknown: "Unknown",
  unknown_state: "Unknown",
};

export type AggregateUiState = keyof typeof AGGREGATE_STATE_LABELS;

export function toAggregateUiState(readiness: ReadinessResponse | null): AggregateUiState {
  if (!readiness) {
    return "disconnected";
  }

  if (readiness.status === "ready") {
    return "ready";
  }

  if (readiness.status === "degraded") {
    return "degraded";
  }

  return "not_ready";
}

export function formsEnabled(readiness: ReadinessResponse | null): boolean {
  const aggregate = toAggregateUiState(readiness);
  return aggregate === "ready" || aggregate === "degraded";
}

const OAUTH_LABELS: Record<OAuthProviderId, string> = {
  google: "Continue with Google",
  github: "Continue with GitHub",
};

const OAUTH_UNAVAILABLE_LABELS: Record<OAuthProviderId, string> = {
  google: "Google sign-in is not configured",
  github: "GitHub sign-in is not configured",
};

export function oauthProviderState(
  readiness: ReadinessResponse | null,
  provider: OAuthProviderId,
): OAuthProviderState {
  const component = provider === "google" ? readiness?.components.oauth_google : readiness?.components.oauth_github;
  const enabled = component === "ready";

  return {
    provider,
    label: OAUTH_LABELS[provider],
    enabled,
    unavailableLabel: enabled ? null : OAUTH_UNAVAILABLE_LABELS[provider],
  };
}

export function componentStateLabel(state: string): string {
  if (state in COMPONENT_STATE_LABELS) {
    return COMPONENT_STATE_LABELS[state as keyof typeof COMPONENT_STATE_LABELS];
  }

  return COMPONENT_STATE_LABELS.unknown_state;
}

export function aggregateStateTone(state: AggregateUiState): "neutral" | "success" | "warning" | "danger" {
  switch (state) {
    case "ready":
      return "success";
    case "degraded":
      return "warning";
    case "not_ready":
    case "disconnected":
      return "danger";
    case "loading":
    default:
      return "neutral";
  }
}

export function detailsDefaultOpen(readiness: ReadinessResponse | null): boolean {
  if (!readiness) {
    return false;
  }

  return readiness.status !== "ready";
}
