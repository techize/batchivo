// Runtime configuration helper
// Reads from window.__RUNTIME_CONFIG__ (set at container startup) with fallback to import.meta.env

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: {
      VITE_API_URL?: string;
      VITE_API_BASE_URL?: string;
      VITE_OTEL_ENDPOINT?: string;
      VITE_SERVICE_NAME?: string;
      VITE_SERVICE_VERSION?: string;
    };
  }
}

function getConfig(key: string): string {
  // First check runtime config (set by container entrypoint)
  const runtimeValue = window.__RUNTIME_CONFIG__?.[key as keyof typeof window.__RUNTIME_CONFIG__];
  if (runtimeValue && runtimeValue !== `\${${key}}`) {
    return runtimeValue;
  }
  // Fall back to build-time env vars
  return (import.meta.env[key] as string) || '';
}

export const config = {
  apiUrl: getConfig('VITE_API_URL'),
  apiBaseUrl: getConfig('VITE_API_BASE_URL'),
  otelEndpoint: getConfig('VITE_OTEL_ENDPOINT') || '/v1/traces',
  serviceName: getConfig('VITE_SERVICE_NAME') || 'batchivo-frontend',
  serviceVersion: getConfig('VITE_SERVICE_VERSION') || '1.0.0',
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
};

export default config;
