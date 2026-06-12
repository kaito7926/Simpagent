import {
  pythonArtifactTypeLabel,
  pythonDeniedBody,
  pythonDeniedTitle,
  DETAILS_LABEL_CLOSED,
  DETAILS_LABEL_OPEN,
  formatDurationLabel,
  formatFileSize,
  pythonInfraBody,
  pythonLimitLabel,
  pythonPolicyBody,
  pythonPolicyTitle,
  pythonProfileLabel,
  PYTHON_EYEBROW,
  pythonStatusLabel,
  pythonToneForStatus,
  type PythonArtifactType,
  type PythonDeniedReason,
  type PythonExecutionProfile,
  type PythonExecutionStatus,
  type PythonInfraFailureReason,
  type PythonLimitName,
  type PythonPolicyErrorCode,
  type ToolTone,
} from "@/lib/chat/tool-copy";

const APPROVED_ARTIFACT_TYPES = new Set<PythonArtifactType>(["csv", "json", "txt", "png"]);

export type PythonExecutionArtifactEnvelope = {
  artifact_id: string;
  name: string;
  artifact_type: PythonArtifactType;
  size_bytes: number;
  download_path: string;
};

export type PythonExecutionResultEnvelope = {
  execution_id: string;
  status: PythonExecutionStatus;
  summary: string;
  duration_ms: number | null;
  profile_name: PythonExecutionProfile | null;
  stdout_excerpt: string | null;
  stderr_excerpt: string | null;
  artifacts: PythonExecutionArtifactEnvelope[];
  limit_triggered: PythonLimitName | null;
  denial_reason: PythonDeniedReason | null;
  policy_error_code: PythonPolicyErrorCode | null;
  infra_failure_reason: PythonInfraFailureReason | null;
  retryable: boolean;
  correlation_id: string | null;
};

export type PresentedArtifact = {
  artifactId: string;
  name: string;
  href: string;
  typeLabel: string;
  sizeLabel: string;
};

export type PresentedExecutionDetails = {
  executionId: string;
  correlationId: string | null;
  stdout: string | null;
  stderr: string | null;
  closedLabel: string;
  openLabel: string;
};

type PresentedAnnouncement = {
  liveRole: "status" | "alert";
  liveMode: "polite" | "assertive";
  isBusy: boolean;
};

type PresentedResultBase = {
  eyebrow: string;
  summary: string;
  tone: ToolTone;
  statusLabel: string;
  durationLabel: string | null;
  profileLabel: string | null;
  artifacts: PresentedArtifact[];
  details: PresentedExecutionDetails | null;
} & PresentedAnnouncement;

export type PresentedPythonResultCard = PresentedResultBase & {
  kind: "python-result";
  status: "accepted" | "running" | "succeeded" | "policy_error" | "infra_failure";
  title: string;
  helperText: string | null;
};

export type PresentedToolDeniedCard = {
  kind: "tool-denied";
  status: "denied";
  eyebrow: string;
  statusLabel: string;
  title: string;
  message: string;
  correlationId: string | null;
} & PresentedAnnouncement;

export type PresentedLimitReachedCard = PresentedResultBase & {
  kind: "limit-reached";
  status: "limit_reached";
  title: string;
  limitLabel: string;
  helperText: string;
};

export type PresentedPythonSurface =
  | PresentedPythonResultCard
  | PresentedToolDeniedCard
  | PresentedLimitReachedCard;

export type ChatMessage =
  | {
      id: string;
      kind: "user";
      content: string;
      timestamp: string;
    }
  | {
      id: string;
      kind: "assistant";
      content: string;
      timestamp: string;
    }
  | {
      id: string;
      kind: "python";
      timestamp: string;
      result: PythonExecutionResultEnvelope;
    };

function presentArtifacts(artifacts: PythonExecutionArtifactEnvelope[]): PresentedArtifact[] {
  return artifacts
    .filter((artifact) => APPROVED_ARTIFACT_TYPES.has(artifact.artifact_type))
    .map((artifact) => ({
      artifactId: artifact.artifact_id,
      name: artifact.name,
      href: artifact.download_path,
      typeLabel: pythonArtifactTypeLabel(artifact.artifact_type),
      sizeLabel: formatFileSize(artifact.size_bytes),
    }));
}

function presentAnnouncement(status: PythonExecutionStatus): PresentedAnnouncement {
  switch (status) {
    case "denied":
    case "policy_error":
    case "infra_failure":
      return {
        liveRole: "alert",
        liveMode: "assertive",
        isBusy: false,
      };
    case "accepted":
    case "running":
      return {
        liveRole: "status",
        liveMode: "polite",
        isBusy: true,
      };
    case "succeeded":
    case "limit_reached":
    default:
      return {
        liveRole: "status",
        liveMode: "polite",
        isBusy: false,
      };
  }
}

function presentDetails(result: PythonExecutionResultEnvelope): PresentedExecutionDetails | null {
  if (!result.stdout_excerpt && !result.stderr_excerpt && !result.correlation_id) {
    return null;
  }

  return {
    executionId: result.execution_id,
    correlationId: result.correlation_id,
    stdout: result.stdout_excerpt,
    stderr: result.stderr_excerpt,
    closedLabel: DETAILS_LABEL_CLOSED,
    openLabel: DETAILS_LABEL_OPEN,
  };
}

function buildResultBase(result: PythonExecutionResultEnvelope): PresentedResultBase {
  return {
    eyebrow: PYTHON_EYEBROW,
    summary: result.summary,
    tone: pythonToneForStatus(result.status),
    statusLabel: pythonStatusLabel(result.status),
    durationLabel: formatDurationLabel(result.duration_ms),
    profileLabel: pythonProfileLabel(result.profile_name),
    artifacts: presentArtifacts(result.artifacts),
    details: presentDetails(result),
    ...presentAnnouncement(result.status),
  };
}

export function presentPythonToolResult(
  result: PythonExecutionResultEnvelope,
): PresentedPythonSurface {
  if (result.status === "denied") {
    return {
      kind: "tool-denied",
      status: "denied",
      eyebrow: PYTHON_EYEBROW,
      statusLabel: pythonStatusLabel("denied"),
      title: pythonDeniedTitle(result.denial_reason ?? "policy_denied"),
      message: pythonDeniedBody(result.denial_reason ?? "policy_denied"),
      correlationId: result.correlation_id,
      ...presentAnnouncement("denied"),
    };
  }

  if (result.status === "limit_reached") {
    return {
      kind: "limit-reached",
      status: "limit_reached",
      title: "Đã dừng để giữ môi trường Python trong giới hạn an toàn.",
      limitLabel: pythonLimitLabel(result.limit_triggered ?? "output_size"),
      helperText: "Hãy rút gọn dữ liệu, giảm số tiến trình, hoặc chia yêu cầu thành các bước nhỏ hơn.",
      ...buildResultBase(result),
    };
  }

  if (result.status === "policy_error") {
    return {
      kind: "python-result",
      status: "policy_error",
      title: pythonPolicyTitle(result.policy_error_code ?? "disallowed_behavior"),
      helperText: pythonPolicyBody(result.policy_error_code ?? "disallowed_behavior"),
      ...buildResultBase(result),
    };
  }

  if (result.status === "infra_failure") {
    return {
      kind: "python-result",
      status: "infra_failure",
      title: "Không thể hoàn tất phiên Python giới hạn.",
      helperText: pythonInfraBody(result.infra_failure_reason, result.retryable),
      ...buildResultBase(result),
    };
  }

  if (result.status === "accepted" || result.status === "running") {
    return {
      kind: "python-result",
      status: result.status,
      title: "Đang xử lý yêu cầu bằng Python giới hạn.",
      helperText: "Kết quả sẽ chỉ hiển thị đầu ra đã được ràng buộc và tệp đã duyệt.",
      ...buildResultBase(result),
    };
  }

  return {
    kind: "python-result",
    status: "succeeded",
    title: "Kết quả thực thi Python",
    helperText: "Thẻ này giữ raw output ở mức phụ để phần tóm tắt luôn là trọng tâm.",
    ...buildResultBase(result),
  };
}
