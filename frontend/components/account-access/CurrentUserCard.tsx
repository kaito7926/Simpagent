import type { CurrentUser } from "@/lib/auth-session";

import { ActionButton } from "./ActionButton";
import { ScopeList } from "./ScopeList";
import { StatusBadge } from "./StatusBadge";

type CurrentUserCardProps = {
  user: CurrentUser;
  scopeLabels: Record<string, string>;
  onLogout: () => void;
  logoutLabel: string;
  isSubmitting: boolean;
  logoutRetryVisible: boolean;
};

export function CurrentUserCard({
  user,
  scopeLabels,
  onLogout,
  logoutLabel,
  isSubmitting,
  logoutRetryVisible,
}: CurrentUserCardProps) {
  return (
    <div className="identity-card">
      <div className="identity-header-row">
        <div>
          <StatusBadge tone="success">{user.role === "admin" ? "Quản trị viên" : "Người dùng"}</StatusBadge>
        </div>
        <StatusBadge tone={user.is_active ? "success" : "danger"}>
          {user.is_active ? "Đang hoạt động" : "Không hoạt động"}
        </StatusBadge>
      </div>

      <dl className="identity-grid">
        <div>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </div>
        <div>
          <dt>Mã tài khoản</dt>
          <dd>{user.id}</dd>
        </div>
      </dl>

      <section className="scope-section" aria-labelledby="scope-section-heading">
        <h3 className="label-heading" id="scope-section-heading">
          Quyền được cấp
        </h3>
        <ScopeList scopes={user.scopes} labels={scopeLabels} />
      </section>

      <section className="phase-note" aria-labelledby="phase-note-heading">
        <h3 className="label-heading" id="phase-note-heading">
          Nền tảng tài khoản đã sẵn sàng
        </h3>
        <p className="body-copy max-copy">
          Giao diện trò chuyện và các công cụ tác tử sẽ được bổ sung ở giai đoạn sau.
        </p>
      </section>

      <div className="logout-row">
        <ActionButton
          type="button"
          variant={logoutRetryVisible ? "secondary" : "quiet"}
          onClick={onLogout}
          disabled={isSubmitting}
          fullWidth={false}
        >
          {logoutLabel}
        </ActionButton>
      </div>
    </div>
  );
}
