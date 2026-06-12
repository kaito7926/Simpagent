import { FlaskConical, ShieldCheck, Sparkles } from "lucide-react";

import { ActionButton } from "@/components/account-access/ActionButton";
import { StatusBadge } from "@/components/account-access/StatusBadge";
import { MessageBubble } from "@/components/chat/MessageBubble";
import type { ChatMessage } from "@/lib/chat/tool-results";

type ChatPreviewShellProps = {
  messages: ChatMessage[];
};

export function ChatPreviewShell({ messages }: ChatPreviewShellProps) {
  return (
    <main className="page-shell chat-page-shell">
      <section className="chat-shell-grid">
        <div className="chat-column">
          <header className="chat-hero-panel">
            <div className="chat-hero-copy">
              <p className="eyebrow">Bản xem trước Next.js</p>
              <h1 className="page-heading">Luồng chat phân biệt rõ phản hồi trợ lý và Python giới hạn</h1>
              <p className="body-copy max-copy">
                Giao diện này giữ nhập liệu ở dạng ngôn ngữ tự nhiên, dùng thẻ Python riêng cho
                kết quả công cụ, và để raw output ở mức phụ thay vì biến màn hình thành notebook.
              </p>
            </div>

            <div className="chat-hero-badges" aria-label="Tín hiệu giao diện">
              <StatusBadge tone="success">Python riêng biệt</StatusBadge>
              <StatusBadge tone="warning">Không có toggle Python</StatusBadge>
              <StatusBadge tone="neutral">CSV · JSON · TXT · PNG</StatusBadge>
            </div>
          </header>

          <section className="chat-stage-panel">
            <div className="chat-stage-header">
              <div>
                <p className="eyebrow">Khung chat</p>
                <h2 className="section-heading">Bản xem trước luồng hội thoại</h2>
              </div>
              <div className="chat-stage-signals">
                <span className="chat-signal-chip">
                  <Sparkles size={16} strokeWidth={1.75} aria-hidden="true" />
                  <span>Trợ lý</span>
                </span>
                <span className="chat-signal-chip">
                  <FlaskConical size={16} strokeWidth={1.75} aria-hidden="true" />
                  <span>Python</span>
                </span>
              </div>
            </div>

            <div className="chat-timeline" aria-label="Bản xem các trạng thái Python">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </div>

            <form className="chat-composer-panel">
              <label className="form-label" htmlFor="chat-preview-input">
                Nhập yêu cầu bằng ngôn ngữ tự nhiên
              </label>
              <textarea
                className="chat-composer-input"
                disabled
                id="chat-preview-input"
                placeholder="Ví dụ: Tính tổng doanh thu theo quý và xuất CSV."
                rows={4}
              />
              <div className="chat-composer-footer">
                <p className="chat-composer-note">
                  Khi backend sẵn sàng, trình điều phối sẽ tự chọn trả lời trực tiếp hoặc Python mà không
                  thêm một chế độ nhập riêng.
                </p>
                <ActionButton disabled fullWidth={false} icon={<ShieldCheck size={16} strokeWidth={1.75} />}>
                  Chờ backend điều phối
                </ActionButton>
              </div>
            </form>
          </section>
        </div>

        <aside className="chat-sidebar">
          <section className="chat-sidebar-card">
            <p className="eyebrow">Giới hạn đã duyệt</p>
            <h2 className="section-heading">Các đầu ra an toàn cho người dùng</h2>
            <ul className="chat-sidebar-list">
              <li>Mặc định chỉ hiển thị tóm tắt, trạng thái, thời lượng, và liên kết tải tệp.</li>
              <li>Raw `stdout` và `stderr` nằm sau nút mở rộng, không chiếm toàn bộ mặt chat.</li>
              <li>Chỉ các loại `csv`, `json`, `txt`, và `png` được gắn thành artifact hiển thị.</li>
            </ul>
          </section>

          <section className="chat-sidebar-card">
            <p className="eyebrow">Điều không xuất hiện</p>
            <h2 className="section-heading">Không có notebook, shell, hay file browser</h2>
            <ul className="chat-sidebar-list">
              <li>Không có nút “Run Python”.</li>
              <li>Không có điều khiển cài package hoặc gọi lệnh ngoài.</li>
              <li>Không có đường dẫn host, container id, hay runtime internals trong UI.</li>
            </ul>
          </section>
        </aside>
      </section>
    </main>
  );
}
