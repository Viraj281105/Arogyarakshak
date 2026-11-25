/**
 * Downloads a case file (appeal PDF, pre-authorisation PDF or package) with the session in a
 * header, hands it to the device's share sheet, and deletes the temporary copy afterwards: the
 * file holds patient details and is the user's to keep, not the app's.
 */
import { ENV } from '../config/env';
import { noteUnauthorized, sessionHeaders } from './session';
import { tr } from '../translations/tr';

export async function downloadCaseFile(path: string, filename: string): Promise<void> {
  // Loaded lazily so screens stay importable in the Node test environment.
  const { Platform } = require('react-native') as typeof import('react-native');
  const url = `${ENV.API_BASE_URL}${path}`;

  if (Platform.OS === 'web') {
    const res = await fetch(url, { headers: sessionHeaders() });
    if (res.status === 401) noteUnauthorized(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const objectUrl = URL.createObjectURL(await res.blob());
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(objectUrl);
    return;
  }

  const FileSystem = require('expo-file-system') as typeof import('expo-file-system');
  const Sharing = require('expo-sharing') as typeof import('expo-sharing');
  const target = `${FileSystem.cacheDirectory}${filename}`;
  try {
    const result = await FileSystem.downloadAsync(url, target, { headers: sessionHeaders() });
    if (result.status === 401) noteUnauthorized(path);
    if (result.status !== 200) throw new Error(`HTTP ${result.status}`);
    if (!(await Sharing.isAvailableAsync())) throw new Error(tr('This device cannot share files.'));
    await Sharing.shareAsync(result.uri);
  } finally {
    await FileSystem.deleteAsync(target, { idempotent: true });
  }
}
