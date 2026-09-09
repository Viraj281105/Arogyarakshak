import { Platform } from 'react-native';
import Constants from 'expo-constants';

/**
 * ArogyaRakshak Mobile Environment Configuration
 */

// Determine default host based on runtime platform
const getDefaultApiUrl = (): string => {
  if (Platform.OS === 'android') {
    // 10.0.2.2 connects the Android emulator to the host machine's localhost
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const ENV = {
  API_BASE_URL: process.env.EXPO_PUBLIC_API_URL || getDefaultApiUrl(),
  USE_MOCK_DATA: process.env.EXPO_PUBLIC_USE_MOCK_DATA === 'true',
  APP_NAME: Constants.expoConfig?.name ?? 'ArogyaRakshak',
  APP_VERSION: Constants.expoConfig?.version ?? '1.0.0',
  TIMEOUT_MS: 15000,
};
