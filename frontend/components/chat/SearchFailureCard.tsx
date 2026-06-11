import React from "react";

import { ActionButton } from "@/components/account-access/ActionButton";
import { InlineAlert } from "@/components/account-access/InlineAlert";
import type { AssistantTurnState } from "@/lib/chat-session";

type SearchFailureCardProps = {
  state: Extract<AssistantTurnState, "denied" | "search_unavailable" | "provider_failed" | "timeout">;
  correlationId: string | null;
  retryDisabled: boolean;
  onRetry: () => void;
};

const COPY = {
  denied: {
    tone: "warning" as const,
    title: "Tìm kiếm đã bị chặn",
    body: "Yêu cầu này không được phép dùng Google Search. Không có lượt tìm kiếm nào được thực hiện.",
    retry: false,
  },
  search_unavailable: {
    tone: "danger" as const,
    title: "Tìm kiếm hiện không khả dụng",
    body: "Gemini Google Search chưa sẵn sàng cho lượt này. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.",
    retry: true,
  },
  provider_failed: {
    tone: "danger" as const,
    title: "Tìm kiếm đã thất bại",
    body: "Không thể hoàn tất lượt tìm kiếm này từ dịch vụ tìm kiếm. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.",
    retry: true,
  },
  timeout: {
    tone: "danger" as const,
    title: "Tìm kiếm đã quá thời gian chờ",
    body: "Không nhận được kết quả từ Google Search trong thời gian cho phép. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.",
    retry: true,
  },
};

export function SearchFailureCard({
  state,
  correlationId,
  retryDisabled,
  onRetry,
}: SearchFailureCardProps) {
  const copy = COPY[state];

  return (
    <div className="search-failure-card">
      <InlineAlert
        tone={copy.tone}
        title={copy.title}
        message={copy.body}
        detail={correlationId ? `Mã tham chiếu: ${correlationId}` : null}
        urgent
      />
      {copy.retry ? (
        <ActionButton
          type="button"
          variant="secondary"
          fullWidth={false}
          className="search-retry-button"
          disabled={retryDisabled}
          onClick={onRetry}
        >
          {retryDisabled ? "Đang thử lại..." : "Thử lại tìm kiếm"}
        </ActionButton>
      ) : null}
    </div>
  );
}
