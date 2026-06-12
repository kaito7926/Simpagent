export type PythonExecutionStatus =
  | "accepted"
  | "running"
  | "succeeded"
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

export type PythonDeniedReason = "missing_permission" | "search_required" | "policy_denied";

export type PythonPolicyErrorCode = "blocked_import" | "disallowed_behavior";

export type PythonInfraFailureReason = "worker_start_failed" | "worker_unavailable";

export type ToolTone = "neutral" | "success" | "warning" | "danger";

const DURATION_FORMATTER = new Intl.NumberFormat("vi-VN", {
  maximumFractionDigits: 1,
});

const SIZE_FORMATTER = new Intl.NumberFormat("vi-VN", {
  maximumFractionDigits: 1,
});

export const PYTHON_EYEBROW = "Python giới hạn";
export const DETAILS_LABEL_CLOSED = "Xem chi tiết thực thi";
export const DETAILS_LABEL_OPEN = "Ẩn chi tiết thực thi";
export const ARTIFACT_SECTION_LABEL = "Tệp đầu ra";

export function pythonStatusLabel(status: PythonExecutionStatus): string {
  switch (status) {
    case "accepted":
      return "Đã nhận lệnh";
    case "running":
      return "Đang thực thi";
    case "succeeded":
      return "Hoàn tất";
    case "denied":
      return "Bị từ chối";
    case "policy_error":
      return "Lỗi chính sách";
    case "limit_reached":
      return "Vượt giới hạn";
    case "infra_failure":
      return "Không thể chạy";
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
      return "thời gian chạy";
    case "cpu":
      return "CPU";
    case "memory":
      return "bộ nhớ";
    case "pid_count":
      return "PID";
    case "process_count":
      return "số tiến trình";
    case "file_size":
      return "kích thước tệp";
    case "output_size":
      return "kích thước đầu ra";
  }
}

export function pythonArtifactTypeLabel(artifactType: PythonArtifactType): string {
  return artifactType.toUpperCase();
}

export function pythonDeniedTitle(reason: PythonDeniedReason): string {
  switch (reason) {
    case "missing_permission":
      return "Tài khoản này chưa có quyền dùng Python giới hạn.";
    case "search_required":
      return "Yêu cầu này cần thêm dữ liệu trước khi chạy Python.";
    case "policy_denied":
      return "Yêu cầu bị chặn trước khi thực thi.";
  }
}

export function pythonDeniedBody(reason: PythonDeniedReason): string {
  switch (reason) {
    case "missing_permission":
      return "Chỉ quản trị viên mới có thể cấp quyền `tool:python` cho tài khoản này.";
    case "search_required":
      return "Yêu cầu này cần cả dữ liệu tìm kiếm và Python. Ở phiên bản hiện tại, hệ thống chỉ cho phép một công cụ trong mỗi lượt.";
    case "policy_denied":
      return "Nội dung yêu cầu không phù hợp với chính sách an toàn của môi trường Python giới hạn.";
  }
}

export function pythonPolicyTitle(code: PythonPolicyErrorCode): string {
  switch (code) {
    case "blocked_import":
      return "Import này không được phép trong môi trường Python giới hạn.";
    case "disallowed_behavior":
      return "Đoạn mã này yêu cầu hành vi không được phép.";
  }
}

export function pythonPolicyBody(code: PythonPolicyErrorCode): string {
  switch (code) {
    case "blocked_import":
      return "Hãy dùng các gói đã được duyệt sẵn hoặc đổi sang cách xử lý không cần import bị chặn.";
    case "disallowed_behavior":
      return "Môi trường này không cho phép cài gói, gọi lệnh ngoài, hay truy cập bề mặt hệ thống chưa được duyệt.";
  }
}

export function pythonInfraBody(
  reason: PythonInfraFailureReason | null | undefined,
  retryable: boolean,
): string {
  if (retryable && reason === "worker_start_failed") {
    return "Worker khởi động không thành công. Bạn có thể thử lại khi hạ tầng sẵn sàng.";
  }
  if (reason === "worker_unavailable") {
    return "Hạ tầng Python tạm thời chưa sẵn sàng. Hãy thử lại sau.";
  }
  return "Hệ thống đã dừng an toàn trước khi có thể trả kết quả thực thi.";
}

export function formatDurationLabel(durationMs: number | null | undefined): string | null {
  if (durationMs == null) {
    return null;
  }
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }
  if (durationMs < 60_000) {
    return `${DURATION_FORMATTER.format(durationMs / 1000)} giây`;
  }
  return `${DURATION_FORMATTER.format(durationMs / 60_000)} phút`;
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
