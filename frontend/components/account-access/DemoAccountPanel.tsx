import React from "react";

import { ActionButton } from "./ActionButton";

type DemoAccountPanelProps = {
  onFillUser: () => void;
  onFillAdmin: () => void;
};

export function DemoAccountPanel({ onFillUser, onFillAdmin }: DemoAccountPanelProps) {
  return (
    <section className="space-y-4 rounded-2xl border border-zinc-200 bg-zinc-50 p-4" aria-labelledby="demo-panel-heading">
      <h3 className="text-sm font-semibold text-zinc-900" id="demo-panel-heading">
        Local demo accounts
      </h3>
      <p className="text-sm leading-6 text-zinc-600">
        Use these shortcuts only for the local development stack. Do not reuse demo credentials in a real deployment.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <ActionButton type="button" variant="secondary" onClick={onFillUser}>
          Fill standard user
        </ActionButton>
        <ActionButton type="button" variant="secondary" onClick={onFillAdmin}>
          Fill administrator
        </ActionButton>
      </div>
    </section>
  );
}
