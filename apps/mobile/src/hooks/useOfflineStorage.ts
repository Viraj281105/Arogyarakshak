import { useState, useCallback } from 'react';
import * as SecureStore from 'expo-secure-store';

/**
 * ArogyaRakshak Transient Secure Session Storage Hook
 * 
 * Strict Invariant (BYOD Policy):
 * Only transient session IDs, user preferences, and offline tokens are permitted.
 * Storing raw medical documents, bills, or prescription images to permanent disk
 * is strictly prohibited by ArogyaRakshak privacy architecture.
 */

export function useOfflineStorage() {
  const [isReady, setIsReady] = useState(true);

  const getItem = useCallback(async (key: string): Promise<string | null> => {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      return null;
    }
  }, []);

  const setItem = useCallback(async (key: string, value: string): Promise<boolean> => {
    // Enforce BYOD zero-retention invariant against raw documents
    if (key.includes('doc_raw') || key.includes('patient_file') || value.length > 50000) {
      console.warn(
        '[BYOD Invariant Guard] Rejected attempt to store large or raw patient file persistently.'
      );
      return false;
    }
    try {
      await SecureStore.setItemAsync(key, value);
      return true;
    } catch {
      return false;
    }
  }, []);

  const removeItem = useCallback(async (key: string): Promise<boolean> => {
    try {
      await SecureStore.deleteItemAsync(key);
      return true;
    } catch {
      return false;
    }
  }, []);

  return {
    isReady,
    getItem,
    setItem,
    removeItem,
  };
}
