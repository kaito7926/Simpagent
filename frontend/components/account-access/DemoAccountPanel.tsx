import React from "react";

import { ActionButton } from "./ActionButton";

type DemoAccountPanelProps = {
  onFillUser: () => void;
  onFillAdmin: () => void;
};

export function DemoAccountPanel({ onFillUser, onFillAdmin }: DemoAccountPanelProps) {
  return (
    <section className="demo-panel" aria-labelledby="demo-panel-heading">
      <h3 className="label-heading" id="demo-panel-heading">
        Local demo accounts
      </h3>
      <p className="body-copy max-copy">
        Use these only for the local development demo. Do not use these credentials in a real
        environment.
      </p>
      <div className="demo-actions">
        <ActionButton type="button" variant="secondary" onClick={onFillUser}>
          Fill Standard User
        </ActionButton>
        <ActionButton type="button" variant="secondary" onClick={onFillAdmin}>
          Fill Administrator
        </ActionButton>
      </div>
    </section>
  );
}
