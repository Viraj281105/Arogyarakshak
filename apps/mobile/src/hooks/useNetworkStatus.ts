import { useState, useEffect, useCallback } from 'react';
import { ENV } from '../config/env';

export interface NetworkStatus {
  isOnline: boolean;
  isChecking: boolean;
  lastChecked: number | null;
  checkConnection: () => Promise<boolean>;
}

export function useNetworkStatus(): NetworkStatus {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<number | null>(null);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    setIsChecking(true);
    try {
      // Smoke check backend health endpoint or DNS fallback
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);
      const res = await fetch(`${ENV.API_BASE_URL}/health`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      const online = res.ok;
      setIsOnline(online);
      setLastChecked(Date.now());
      return online;
    } catch {
      setIsOnline(false);
      setLastChecked(Date.now());
      return false;
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    // Initial check
    checkConnection();

    // Periodic heartbeat every 30s
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  return {
    isOnline,
    isChecking,
    lastChecked,
    checkConnection,
  };
}
