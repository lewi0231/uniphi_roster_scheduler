export interface AppConfig {
  env: "development" | "production" | "test";
  appUrl: string;
  analytics: {
    enabled: boolean;
    id?: string;
  };
  features: {
    debugMode: boolean;
    consoleLogs: boolean;
  };
}

const getConfig = (): AppConfig => {
  const env = (process.env.NEXT_PUBLIC_APP_ENV ||
    process.env.NODE_ENV ||
    "development") as AppConfig["env"];

  const baseConfig: AppConfig = {
    env,
    appUrl: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
    analytics: {
      enabled: process.env.NEXT_PUBLIC_ANALYTICS_ENABLED === "true",
      id: process.env.NEXT_PUBLIC_ANALYTICS_ID,
    },
    features: {
      debugMode: process.env.NEXT_PUBLIC_ENABLE_DEBUG_MODE === "true",
      consoleLogs: process.env.NEXT_PUBLIC_ENABLE_CONSOLE_LOGS === "true",
    },
  };

  // Environment-specific overrides
  if (env === "production") {
    return {
      ...baseConfig,
      features: {
        debugMode: false,
        consoleLogs: false,
      },
    };
  }

  return baseConfig;
};

export const config = getConfig();
