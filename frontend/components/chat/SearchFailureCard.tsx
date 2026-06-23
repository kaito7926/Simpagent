import React from "react";

import { ActionButton } from "@/components/account-access/ActionButton";
import { InlineAlert } from "@/components/account-access/InlineAlert";
import type { AssistantTurnState, WebsearchProvider } from "@/lib/chat-session";

type SearchFailureCardProps = {
  state: Extract<AssistantTurnState, "denied" | "search_unavailable" | "provider_failed" | "timeout">;
  provider: WebsearchProvider | null;
  correlationId: string | null;
  retryDisabled: boolean;
  onRetry: () => void;
};

function providerLabel(provider: WebsearchProvider | null): string {
  return provider === "firecrawl" ? "Firecrawl" : "Gemini Google Search";
}

function copyFor(
  state: SearchFailureCardProps["state"],
  provider: WebsearchProvider | null,
) {
  const activeProvider = providerLabel(provider);

  switch (state) {
    case "denied":
      return {
        tone: "warning" as const,
        title: "Tìm kiếm đã bị chặn",
        body: "Yêu cầu này không được phép dùng dịch vụ tìm kiếm. Không có lượt tìm kiếm nào được thực hiện.",
        retry: false,
      };
    case "search_unavailable":
      return {
        tone: "danger" as const,
        title: "Tìm kiếm hiện không khả dụng",
        body: `${activeProvider} chưa sẵn sàng cho lượt này. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.`,
        retry: true,
      };
    case "provider_failed":
      return {
        tone: "danger" as const,
        title: "Tìm kiếm đã thất bại",
        body: "Không thể hoàn tất lượt tìm kiếm này từ dịch vụ tìm kiếm. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.",
        retry: true,
      };
    case "timeout":
      return {
        tone: "danger" as const,
        title: "Tìm kiếm đã quá thời gian chờ",
        body: `Không nhận được kết quả từ ${activeProvider} trong thời gian cho phép. Hãy thử lại tìm kiếm hoặc chuyển sang câu hỏi bình thường.`,
        retry: true,
      };
  }
}

export function SearchFailureCard({
  state,
  provider,
  correlationId,
  retryDisabled,
  onRetry,
}: SearchFailureCardProps) {
  const copy = copyFor(state, provider);

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
