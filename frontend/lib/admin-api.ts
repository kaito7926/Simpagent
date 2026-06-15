import type { AuthSessionController } from "@/lib/auth-session";

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

export type OrchestrationSettingsResponse = {
  guardrail_safety_enabled: boolean;
  trusted_supervisor_enabled: boolean;
};

export async function getAdminMetrics(
  controller: AuthSessionController,
): Promise<AdminMetricsResponse> {
  return controller.authorizedJson<AdminMetricsResponse>("/api/admin/metrics", {
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

export async function setTrustedSupervisorEnabled(
  controller: AuthSessionController,
  enabled: boolean,
): Promise<OrchestrationSettingsResponse> {
  return controller.authorizedJson<OrchestrationSettingsResponse>(
    "/api/admin/orchestration/trusted-supervisor",
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
