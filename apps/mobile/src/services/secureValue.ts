/**
 * One value in the device's secure store. Loaded lazily (like api/caseAuth.ts) so modules that
 * use it stay importable in the Node test environment and in the web preview, where the native
 * store does not exist: there the value simply lasts until the app is closed.
 */
type SecureStoreModule = typeof import('expo-secure-store');

function secureStore(): SecureStoreModule {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  return require('expo-secure-store') as SecureStoreModule;
}

export async function readSecure(key: string): Promise<string | null> {
  try {
    return await secureStore().getItemAsync(key);
  } catch {
    return null;
  }
}

export async function writeSecure(key: string, value: string | null): Promise<void> {
  try {
    if (value === null) await secureStore().deleteItemAsync(key);
    else await secureStore().setItemAsync(key, value);
  } catch {
    // Unavailable (web preview, tests): memory only.
  }
}
