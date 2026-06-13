import { StatusBadge } from "@/components/account-access/StatusBadge";
import type { CurrentUser, ReadinessResponse } from "@/lib/auth-session";

type ConversationHeaderProps = {
  currentUser: CurrentUser | null;
  readiness: ReadinessResponse | null;
  searchEnabled: boolean;
};

export function ConversationHeader({
  currentUser,
  readiness,
  searchEnabled,
}: ConversationHeaderProps) {
  const searchReady = readiness?.components.search === "ready";

  return (
    <header className="conversation-header">
      <div>
        <p className="eyebrow">Phiên trò chuyện</p>
        <h1 className="page-heading">Chat bảo mật với Google Search có kiểm soát</h1>
        <p className="body-copy max-copy">
          Chọn cách trả lời cho từng lượt hỏi để phân biệt rõ câu trả lời bình thường và kết quả có nguồn dẫn.
        </p>
      </div>
      <div className="conversation-badges">
        <StatusBadge tone={currentUser ? "success" : "warning"}>
          {currentUser ? currentUser.email : "Chưa xác thực"}
        </StatusBadge>
        <StatusBadge tone={searchEnabled && searchReady ? "success" : "neutral"}>
          {searchEnabled && searchReady ? "Google Search sẵn sàng" : "Google Search chưa sẵn sàng"}
        </StatusBadge>
      </div>
    </header>
  );
}
