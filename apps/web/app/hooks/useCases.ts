"use client";

import { useSyncExternalStore } from "react";
import {
  activeCaseSnapshot,
  guestCasesSnapshot,
  serverActiveCase,
  serverGuestCases,
  subscribeCases,
  type CaseRef,
  type GuestCase,
} from "../lib/caseStore";

/** Guest cases held by this tab (sessionStorage, decision D2). Empty on the server. */
export function useGuestCases(): GuestCase[] {
  return useSyncExternalStore(subscribeCases, guestCasesSnapshot, serverGuestCases);
}

/** The case open in the workspace (never in the URL), with its token resolved for a guest case. */
export function useActiveCase(): CaseRef | null {
  return useSyncExternalStore(subscribeCases, activeCaseSnapshot, serverActiveCase);
}
