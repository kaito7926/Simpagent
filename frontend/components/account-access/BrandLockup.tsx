import Image from "next/image";

import { Card } from "@/components/ui/card";

const COPY = {
  signedOutTitle: "Secure AI assistance for internal work.",
  signedInTitle: "Your protected workspace is ready.",
  body: "SimpAgent keeps session access protected while giving you a modern workspace for direct chat, grounded search, limited Python, and administrative evidence.",
};

type BrandLockupProps = {
  authenticated: boolean;
};

export function BrandLockup({ authenticated }: BrandLockupProps) {
  return (
    <Card className="auth-brand-panel" aria-label="About SimpAgent">
      <p className="auth-eyebrow">Protected workspace</p>
      <div className="hero-copy">
        <div className="brand-row">
          <span className="inline-flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-white shadow-sm">
            <Image
              alt="SimpAgent logo"
              className="h-10 w-10 object-contain"
              height={40}
              priority
              src="/brand/auroraguard-logo-mark-white.png"
              width={40}
            />
          </span>
          <div className="brand-copy">
            <span className="brand-name">SimpAgent</span>
            <span className="body-copy">Intelligent. Secure. Always by your side.</span>
          </div>
        </div>
        <h1 className="page-heading">
          {authenticated ? COPY.signedInTitle : COPY.signedOutTitle}
        </h1>
        <p className="body-copy max-copy">{COPY.body}</p>
      </div>
    </Card>
  );
}
