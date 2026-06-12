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
          <StatusBadge tone="success">{user.role === "admin" ? "Administrator" : "Standard User"}</StatusBadge>
        </div>
        <StatusBadge tone={user.is_active ? "success" : "danger"}>
          {user.is_active ? "Active" : "Inactive"}
        </StatusBadge>
      </div>

      <dl className="identity-grid">
        <div>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </div>
        <div>
          <dt>Account ID</dt>
          <dd>{user.id}</dd>
        </div>
      </dl>

      <section className="scope-section" aria-labelledby="scope-section-heading">
        <h3 className="label-heading" id="scope-section-heading">
          Granted scopes
        </h3>
        <ScopeList scopes={user.scopes} labels={scopeLabels} />
      </section>

      <section className="phase-note" aria-labelledby="phase-note-heading">
        <h3 className="label-heading" id="phase-note-heading">
          Account foundation ready
        </h3>
        <p className="body-copy max-copy">
          Your protected account session is active.
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
