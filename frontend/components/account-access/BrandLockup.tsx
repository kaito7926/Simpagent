import React from "react";

type BrandLockupProps = {
  authenticated: boolean;
};

export function BrandLockup({ authenticated }: BrandLockupProps) {
  return (
    <section className="brand-hero" aria-label="About SimpAgent">
      <p className="eyebrow">PROTECTED ACCESS</p>
      <div className="brand-hero-copy">
        <div className="brand-row">
          <span className="brand-mark-wrap" aria-hidden="true">
            <span className="brand-mark brand-mark-primary" />
            <span className="brand-mark brand-mark-secondary" />
          </span>
          <span className="brand-name">SimpAgent</span>
        </div>
        <h1 className="page-heading">
          {authenticated
            ? "A clear entry point for your protected workspace."
            : "A clear entry point for your account and session."}
        </h1>
        <p className="body-copy max-copy">
          Sign in with a local account while SimpAgent keeps access tokens in memory and refresh
          sessions protected from JavaScript.
        </p>
      </div>
    </section>
  );
}
