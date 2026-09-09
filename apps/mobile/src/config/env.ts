/**
 * ArogyaRakshak Mobile Environment Configuration
 */

// Determine platform safely across native runtime and testing environments
let platformOS: string = 'unknown';
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { Platform } = require('react-native');
  platformOS = Platform?.OS ?? 'unknown';
} catch {
  platformOS = 'unknown';
}

let appName = 'ArogyaRakshak';
let appVersion = '1.0.0';
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const Constants = require('expo-constants');
  const config = Constants.default?.expoConfig || Constants.expoConfig;
  if (config?.name) appName = config.name;
  if (config?.version) appVersion = config.version;
} catch {
  // fallback defaults
}

// Determine default host based on runtime platform
const getDefaultApiUrl = (): string => {
  if (platformOS === 'android') {
    // 10.0.2.2 connects the Android emulator to the host machine's localhost
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const ENV = {
  API_BASE_URL: process.env.EXPO_PUBLIC_API_URL || getDefaultApiUrl(),
  USE_MOCK_DATA: process.env.EXPO_PUBLIC_USE_MOCK_DATA === 'true',
  APP_NAME: appName,
  APP_VERSION: appVersion,
  TIMEOUT_MS: 15000,
};
