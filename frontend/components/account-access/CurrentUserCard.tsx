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
    <div className="space-y-5 rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <StatusBadge tone="success">{user.role === "admin" ? "Administrator" : "Standard user"}</StatusBadge>
        <StatusBadge tone={user.is_active ? "success" : "danger"}>
          {user.is_active ? "Active" : "Inactive"}
        </StatusBadge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Email</dt>
          <dd className="text-sm leading-6 text-zinc-900">{user.email}</dd>
        </div>
        <div className="space-y-1">
          <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Account ID</dt>
          <dd className="text-sm leading-6 text-zinc-900">{user.id}</dd>
        </div>
      </div>

      <section className="space-y-3" aria-labelledby="scope-section-heading">
        <h3 className="text-sm font-semibold text-zinc-900" id="scope-section-heading">
          Granted scopes
        </h3>
        <ScopeList scopes={user.scopes} labels={scopeLabels} />
      </section>

      <div className="flex justify-end">
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
