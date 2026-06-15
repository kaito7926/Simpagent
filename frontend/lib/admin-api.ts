import type { AuthSessionController } from "@/lib/auth-session";

export type OrchestrationSettingsResponse = {
  guardrail_safety_enabled: boolean;
  trusted_supervisor_enabled: boolean;
};

export async function getOrchestrationSettings(
  controller: AuthSessionController,
): Promise<OrchestrationSettingsResponse> {
  return controller.authorizedJson<OrchestrationSettingsResponse>("/api/admin/orchestration", {
    method: "GET",
    cache: "no-store",
  });
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
