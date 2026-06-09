import { AccountAccessShell } from "@/components/account-access/AccountAccessShell";
import { getDemoConfig } from "@/lib/demo-config";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function HomePage({ searchParams }: PageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  const rawMode = resolvedSearchParams.mode;
  const initialMode = Array.isArray(rawMode) ? rawMode[0] ?? null : rawMode ?? null;
  const demoConfig = getDemoConfig();

  return <AccountAccessShell initialMode={initialMode} demoConfig={demoConfig} />;
}
