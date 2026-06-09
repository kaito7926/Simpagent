export type DemoConfig =
  | { enabled: false }
  | {
      enabled: true;
      userEmail: string;
      userPassword: string;
      adminEmail: string;
      adminPassword: string;
    };

export function getDemoConfig(env: NodeJS.ProcessEnv = process.env): DemoConfig {
  const isDevelopmentRuntime = env.NODE_ENV !== "production";
  const isDevelopmentApp = env.SIMPAGENT_APP_ENV === "development";
  const demoSeedEnabled = env.SIMPAGENT_DEMO_SEED_ENABLED === "true";

  if (!isDevelopmentRuntime || !isDevelopmentApp || !demoSeedEnabled) {
    return { enabled: false };
  }

  const userEmail = env.SIMPAGENT_DEMO_USER_EMAIL;
  const userPassword = env.SIMPAGENT_DEMO_USER_PASSWORD;
  const adminEmail = env.SIMPAGENT_DEMO_ADMIN_EMAIL;
  const adminPassword = env.SIMPAGENT_DEMO_ADMIN_PASSWORD;

  if (!userEmail || !userPassword || !adminEmail || !adminPassword) {
    return { enabled: false };
  }

  return {
    enabled: true,
    userEmail,
    userPassword,
    adminEmail,
    adminPassword,
  };
}
