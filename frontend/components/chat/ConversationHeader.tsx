import { StatusBadge } from "@/components/account-access/StatusBadge";
import type { CurrentUser, ReadinessResponse } from "@/lib/auth-session";
import type { WebsearchProvider } from "@/lib/chat-session";

type ConversationHeaderProps = {
  currentUser: CurrentUser | null;
  readiness: ReadinessResponse | null;
  searchEnabled: boolean;
  provider?: WebsearchProvider | null;
};

export function ConversationHeader({
  currentUser,
  readiness,
  searchEnabled,
  provider = null,
}: ConversationHeaderProps) {
  const searchReady = readiness?.components.search === "ready";
  const providerName = provider === "gemini" ? "Google Search" : provider === "firecrawl" ? "Firecrawl" : "Websearch";

  return (
    <header className="conversation-header">
      <div>
        <p className="eyebrow">Phiên trò chuyện</p>
        <h1 className="page-heading">Chat bảo mật với websearch có kiểm soát</h1>
        <p className="body-copy max-copy">
          Chọn cách trả lời cho từng lượt hỏi để phân biệt rõ câu trả lời bình thường và kết quả có nguồn dẫn.
        </p>
      </div>
      <div className="conversation-badges">
        <StatusBadge tone={currentUser ? "success" : "warning"}>
          {currentUser ? currentUser.email : "Chưa xác thực"}
        </StatusBadge>
        <StatusBadge tone={searchEnabled && searchReady ? "success" : "neutral"}>
          {searchEnabled && searchReady ? `${providerName} sẵn sàng` : `${providerName} chưa sẵn sàng`}
        </StatusBadge>
      </div>
    </header>
  );
}
