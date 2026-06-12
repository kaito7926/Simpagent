import React from "react";
import { ShieldCheck, SquareDashedMousePointer, UserRoundCog } from "lucide-react";

const ITEMS = [
  {
    heading: "Short-lived access",
    body: "The access token stays only in browser memory.",
    icon: SquareDashedMousePointer,
  },
  {
    heading: "Protected refresh cookie",
    body: "The refresh session is unavailable to JavaScript.",
    icon: ShieldCheck,
  },
  {
    heading: "Server-side authority",
    body: "The server rechecks roles, scopes, and account status.",
    icon: UserRoundCog,
  },
] as const;

export function SecuritySummary() {
  return (
    <section className="security-summary" aria-labelledby="security-summary-heading">
      <h2 className="visually-hidden" id="security-summary-heading">
        Session protection summary
      </h2>
      {ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <article className="security-summary-item" key={item.heading}>
            <span className="security-node" aria-hidden="true" />
            <div className="security-summary-copy">
              <div className="security-summary-title-row">
                <Icon aria-hidden="true" size={18} strokeWidth={1.75} />
                <h3 className="label-heading">{item.heading}</h3>
              </div>
              <p className="body-copy max-copy">{item.body}</p>
            </div>
          </article>
        );
      })}
    </section>
  );
}
