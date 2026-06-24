import type { AuthSessionController } from "@/lib/auth-session";

export type AdminPage = {
  limit: number;
  offset: number;
  has_more: boolean;
  next_offset: number | null;
};

export type SafeEvidenceSnippet = {
  kind: string;
  text: string;
  truncated: boolean;
};

export type AdminUserItem = {
  id: string;
  email: string;
  role: string;
  scopes: string[];
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminUsersPage = {
  items: AdminUserItem[];
  page: AdminPage;
};

export type SecurityEventItem = {
  id: string;
  event_type: string;
  severity: string;
  user_id: string | null;
  description: string;
  correlation_id: string | null;
  metadata: Record<string, unknown>;
  snippets: SafeEvidenceSnippet[];
  created_at: string;
};

export type SecurityEventsPage = {
  items: SecurityEventItem[];
  page: AdminPage;
};

export type ToolExecutionItem = {
  id: string;
  user_id: string;
  conversation_id: string | null;
  tool_name: string;
  input_summary: string;
  output_summary: string | null;
  status: string;
  duration_ms: number | null;
  correlation_id: string | null;
  snippets: SafeEvidenceSnippet[];
  created_at: string;
};

export type ToolExecutionsPage = {
  items: ToolExecutionItem[];
  page: AdminPage;
};

export type GatewayEvidenceItem = {
  id: string;
  evidence_type: "rate_limit" | "request_size" | "correlation_id" | "route_protection";
  source: "kong_config" | "kong_log";
  route: string | null;
  plugin: string;
  status_codes: number[];
  summary: string;
  metadata: Record<string, unknown>;
  snippets: SafeEvidenceSnippet[];
};

export type GatewayEvidenceSummary = {
  rate_limit_routes: number;
  request_size_routes: number;
  correlation_id_enabled: boolean;
  route_protection_routes: number;
};

export type GatewayEvidencePage = {
  items: GatewayEvidenceItem[];
  page: AdminPage;
  summary: GatewayEvidenceSummary;
};

export type AdminMetricsResponse = {
  generated_at: string;
  users_total: number;
  users_active: number;
  security_events_total: number;
  security_events_last_24h: number;
  tool_executions_total: number;
  tool_executions_last_24h: number;
  correlation_references_total: number;
  rate_limit_events_total: number;
};

export type WebsearchProvider = "gemini" | "firecrawl";

export type OrchestrationSettingsResponse = {
  guardrail_safety_enabled: boolean;
  websearch_provider_default: WebsearchProvider;
  websearch_provider_override: WebsearchProvider | null;
  websearch_provider_effective: WebsearchProvider;
  websearch_provider_readiness: string;
};

export type AdminPageRequest = {
  limit?: number;
  offset?: number;
};

export type AdminUserAccessUpdate = {
  role?: "user" | "admin";
  is_active?: boolean;
};

export type AdminUserUpdateResponse = {
  user: AdminUserItem;
  changed_fields: string[];
};

function pageQuery(options: AdminPageRequest = {}): string {
  const limit = options.limit ?? 25;
  const offset = options.offset ?? 0;
  return `limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`;
}

export async function getAdminMetrics(
  controller: AuthSessionController,
): Promise<AdminMetricsResponse> {
  return controller.authorizedJson<AdminMetricsResponse>("/api/admin/metrics", {
    method: "GET",
    cache: "no-store",
  });
}

export async function getAdminUsers(
  controller: AuthSessionController,
  options: AdminPageRequest = {},
): Promise<AdminUsersPage> {
  return controller.authorizedJson<AdminUsersPage>(`/api/admin/users?${pageQuery(options)}`, {
    method: "GET",
    cache: "no-store",
  });
}

export async function getSecurityEvents(
  controller: AuthSessionController,
  options: AdminPageRequest = {},
): Promise<SecurityEventsPage> {
  return controller.authorizedJson<SecurityEventsPage>(`/api/admin/security-events?${pageQuery(options)}`, {
    method: "GET",
    cache: "no-store",
  });
}

export async function getToolExecutions(
  controller: AuthSessionController,
  options: AdminPageRequest = {},
): Promise<ToolExecutionsPage> {
  return controller.authorizedJson<ToolExecutionsPage>(`/api/admin/tool-executions?${pageQuery(options)}`, {
    method: "GET",
    cache: "no-store",
  });
}

export async function getGatewayEvidence(
  controller: AuthSessionController,
  options: AdminPageRequest = {},
): Promise<GatewayEvidencePage> {
  return controller.authorizedJson<GatewayEvidencePage>(`/api/admin/gateway-evidence?${pageQuery(options)}`, {
    method: "GET",
    cache: "no-store",
  });
}

export async function getOrchestrationSettings(
  controller: AuthSessionController,
): Promise<OrchestrationSettingsResponse> {
  return controller.authorizedJson<OrchestrationSettingsResponse>("/api/admin/orchestration", {
    method: "GET",
    cache: "no-store",
  });
}

export async function updateUserAccess(
  controller: AuthSessionController,
  userId: string,
  payload: AdminUserAccessUpdate,
): Promise<AdminUserUpdateResponse> {
  return controller.authorizedJson<AdminUserUpdateResponse>(`/api/admin/users/${userId}`, {
    method: "PATCH",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function setGuardrailSafetyEnabled(
  controller: AuthSessionController,
  enabled: boolean,
): Promise<OrchestrationSettingsResponse> {
  return controller.authorizedJson<OrchestrationSettingsResponse>(
    "/api/admin/orchestration/guardrail",
    {
      method: "PATCH",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled }),
    },
  );
}

export async function setWebsearchProviderOverride(
  controller: AuthSessionController,
  provider: WebsearchProvider | null,
): Promise<OrchestrationSettingsResponse> {
  return controller.authorizedJson<OrchestrationSettingsResponse>(
    "/api/admin/orchestration/websearch-provider",
    {
      method: "PATCH",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ provider }),
    },
  );
}
