/**
 * The patient's active case, shared by every module tab.
 *
 * Tabs are separate screens: navigating from BillNyay to the DaaviSetu or DawaCheck tab
 * used to arrive with no caseId, so the patient had to scan again ("Scan first") and the
 * pre-authorization readiness flow was effectively unreachable for a scanned bill. The
 * scan flow now records the case here; a screen uses its route caseId when one is given
 * and falls back to this.
 *
 * In memory only: the case token itself is managed by api/caseAuth (ADR-009). No document
 * data is held here (ADR-003) — only the case identifier.
 */

type Listener = () => void;

let activeCaseId: string | null = null;
const listeners = new Set<Listener>();

export function getActiveCaseId(): string | null {
  return activeCaseId;
}

export function setActiveCaseId(caseId: string | null): void {
  if (caseId === activeCaseId) return;
  activeCaseId = caseId;
  listeners.forEach((l) => l());
}

/** Clears the active case only if it is the given one (e.g. after deleting it). */
export function clearActiveCase(caseId: string): void {
  if (activeCaseId === caseId) setActiveCaseId(null);
}

export function subscribeActiveCase(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Route param wins (the scan that brought the patient here); otherwise the active case. */
export function resolveCaseId(routeCaseId: string | null | undefined, active: string | null): string | null {
  return routeCaseId || active || null;
}
