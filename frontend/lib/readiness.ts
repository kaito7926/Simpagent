import type { ReadinessComponentState, ReadinessResponse } from "@/lib/auth-session";

export const AGGREGATE_STATE_LABELS = {
  loading: "Đang kiểm tra hệ thống",
  ready: "Sẵn sàng",
  degraded: "Hoạt động giới hạn",
  not_ready: "Chưa sẵn sàng",
  disconnected: "Không thể kết nối",
} as const;

export const AGGREGATE_STATE_BODIES = {
  loading: "Vui lòng chờ trong giây lát.",
  ready: "Đăng ký và đăng nhập đang hoạt động.",
  degraded: "Tài khoản vẫn hoạt động; một số dịch vụ AI chưa được cấu hình hoặc đang tạm gián đoạn.",
  not_ready: "Đăng nhập tạm thời không khả dụng. Hãy đợi hệ thống hoàn tất khởi động rồi thử lại.",
  disconnected: "Không đọc được trạng thái nền tảng. Kiểm tra hệ thống đang chạy rồi thử lại.",
} as const;

export const COMPONENT_LABELS = {
  database: "Cơ sở dữ liệu",
  migrations: "Cấu trúc dữ liệu",
  llm: "Dịch vụ trò chuyện AI",
  search: "Tìm kiếm có căn cứ",
  sandbox: "Nền tảng Python giới hạn",
} as const;

export const COMPONENT_STATE_LABELS: Record<ReadinessComponentState | "unknown_state", string> = {
  ready: "Sẵn sàng",
  foundation_ready: "Nền tảng sẵn sàng",
  unconfigured: "Chưa cấu hình",
  model_unavailable: "Mô hình không khả dụng",
  unavailable: "Không khả dụng",
  out_of_date: "Chưa cập nhật",
  unknown: "Không xác định",
  unknown_state: "Không xác định",
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
