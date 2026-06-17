export type PythonExecutionStatus =
  | "accepted"
  | "running"
  | "succeeded"
  | "failed"
  | "denied"
  | "policy_error"
  | "limit_reached"
  | "infra_failure";

export type PythonExecutionProfile = "python-basic-v1" | "python-data-v1";

export type PythonArtifactType = "csv" | "json" | "txt" | "png";

export type PythonLimitName =
  | "wall_time"
  | "cpu"
  | "memory"
  | "pid_count"
  | "process_count"
  | "file_size"
  | "output_size";

export type PythonDeniedReason =
  | "missing_permission"
  | "search_required"
  | "policy_denied";

export type PythonPolicyErrorCode = "blocked_import" | "disallowed_behavior";

export type PythonInfraFailureReason = "worker_start_failed" | "worker_unavailable";

export type ToolTone = "neutral" | "success" | "warning" | "danger";

const DURATION_FORMATTER = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

const SIZE_FORMATTER = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

export const PYTHON_EYEBROW = "Limited Python";
export const DETAILS_LABEL_CLOSED = "View execution details";
export const DETAILS_LABEL_OPEN = "Hide execution details";
export const ARTIFACT_SECTION_LABEL = "Output files";

export function pythonStatusLabel(status: PythonExecutionStatus): string {
  switch (status) {
    case "accepted":
      return "Accepted";
    case "running":
      return "Running";
    case "succeeded":
      return "Completed";
    case "failed":
      return "Python failed";
    case "denied":
      return "Denied";
    case "policy_error":
      return "Policy error";
    case "limit_reached":
      return "Limit reached";
    case "infra_failure":
      return "Could not run";
  }
}

export function pythonToneForStatus(status: PythonExecutionStatus): ToolTone {
  switch (status) {
    case "accepted":
    case "running":
    case "limit_reached":
      return "warning";
    case "succeeded":
      return "success";
    case "failed":
      return "danger";
    case "denied":
    case "policy_error":
    case "infra_failure":
      return "danger";
  }
}

export function pythonProfileLabel(profileName: PythonExecutionProfile | null | undefined): string | null {
  if (!profileName) {
    return null;
  }
  return profileName;
}

export function pythonLimitLabel(limitName: PythonLimitName): string {
  switch (limitName) {
    case "wall_time":
      return "wall time";
    case "cpu":
      return "CPU";
    case "memory":
      return "memory";
    case "pid_count":
      return "PID count";
    case "process_count":
      return "process count";
    case "file_size":
      return "file size";
    case "output_size":
      return "output size";
  }
}

export function pythonArtifactTypeLabel(artifactType: PythonArtifactType): string {
  return artifactType.toUpperCase();
}

export function pythonDeniedTitle(reason: PythonDeniedReason): string {
  switch (reason) {
    case "missing_permission":
      return "This account is not allowed to use limited Python.";
    case "search_required":
      return "This request needs additional data before Python can run.";
    case "policy_denied":
      return "The request was blocked before execution.";
  }
}

export function pythonDeniedBody(reason: PythonDeniedReason): string {
  switch (reason) {
    case "missing_permission":
      return "Only an administrator can grant the `tool:python` permission to this account.";
    case "search_required":
      return "This request needs both search data and Python. In the current version, the system still allows only one tool per turn.";
    case "policy_denied":
      return "The request content does not satisfy the safety policy for the limited Python environment.";
  }
}

export function pythonPolicyTitle(code: PythonPolicyErrorCode): string {
  switch (code) {
    case "blocked_import":
      return "This import is not allowed in the limited Python environment.";
    case "disallowed_behavior":
      return "This code requested behavior that is not allowed.";
  }
}

export function pythonPolicyBody(code: PythonPolicyErrorCode): string {
  switch (code) {
    case "blocked_import":
      return "Use approved built-in packages or switch to an approach that does not need the blocked import.";
    case "disallowed_behavior":
      return "This environment does not allow package installation, external commands, or low-level system access.";
  }
}

export function pythonInfraBody(
  reason: PythonInfraFailureReason | null | undefined,
  retryable: boolean,
): string {
  if (retryable && reason === "worker_start_failed") {
    return "The worker could not start successfully. You can try again when the infrastructure is ready.";
  }
  if (reason === "worker_unavailable") {
    return "The Python infrastructure is temporarily unavailable. Please try again later.";
  }
  return "The system stopped safely before it could return execution output.";
}

export function formatDurationLabel(durationMs: number | null | undefined): string | null {
  if (durationMs == null) {
    return null;
  }
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }
  if (durationMs < 60_000) {
    return `${DURATION_FORMATTER.format(durationMs / 1000)} s`;
  }
  return `${DURATION_FORMATTER.format(durationMs / 60_000)} min`;
}

export function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${SIZE_FORMATTER.format(sizeBytes / 1024)} KB`;
  }
  return `${SIZE_FORMATTER.format(sizeBytes / (1024 * 1024))} MB`;
}
