"use client";

import { useEffect, useSyncExternalStore } from "react";
import { ensureAccountChecked, getAccountState, getServerAccountState, subscribeAccount, type AccountState } from "../lib/session";

/** What the API last said about the signed-in account; asks once per page load. */
export function useAccount(): AccountState {
  const state = useSyncExternalStore(subscribeAccount, getAccountState, getServerAccountState);
  useEffect(() => {
    ensureAccountChecked();
  }, []);
  return state;
}
