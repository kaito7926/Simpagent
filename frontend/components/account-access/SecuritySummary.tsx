import React from "react";
import { ShieldCheck, Sparkles, UserRoundCog } from "lucide-react";

const ITEMS = [
  {
    heading: "Memory-only access",
    body: "The active access token stays in browser memory instead of durable local storage.",
    icon: Sparkles,
  },
  {
    heading: "Protected refresh cookie",
    body: "Refresh state remains outside normal JavaScript access and is revalidated by the server.",
    icon: ShieldCheck,
  },
  {
    heading: "Server-side authority",
    body: "Roles, scopes, and account status are checked again before protected actions run.",
    icon: UserRoundCog,
  },
] as const;

export function SecuritySummary() {
  return (
    <section className="space-y-4 rounded-3xl border border-zinc-200 bg-white/90 p-6 shadow-sm">
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Trust signals</p>
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900">Security is part of the product experience.</h2>
      </div>
      <div className="space-y-4">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <article className="grid grid-cols-[12px_minmax(0,1fr)] gap-3" key={item.heading}>
              <span className="mt-2 h-3 w-3 rounded-sm bg-zinc-200" aria-hidden="true" />
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <Icon aria-hidden="true" size={16} strokeWidth={1.75} className="text-zinc-500" />
                  <h3 className="text-sm font-semibold text-zinc-900">{item.heading}</h3>
                </div>
                <p className="text-sm leading-6 text-zinc-600">{item.body}</p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
