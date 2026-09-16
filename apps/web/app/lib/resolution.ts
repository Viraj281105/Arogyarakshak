// Client contract for Kadi entity-resolution review (#31). Mirrors
// ResolutionDecisionResponse in apps/api/app/api/v1/endpoints/kadi.py.

export type SignalName = "lexical" | "phonetic" | "semantic";
export type SignalStatus = "AVAILABLE" | "UNAVAILABLE" | "NOT_APPLICABLE";

export interface ResolutionSignal {
  signal: SignalName;
  status: SignalStatus;
  score: number | null;
  detail: string;
}

export interface ResolutionDecision {
  id: string;
  entity_type: string;
  action: "MERGE" | "ASK";
  status: string;
  source: string;
  /** Similarity evidence in [0, 1] — not a probability. */
  confidence: number;
  mention_name: string | null;
  mention_entity_id: string | null;
  candidate_entity_id: string;
  candidate_name: string;
  signals: ResolutionSignal[];
  reasons: string[];
  feedback_same_entity: boolean | null;
}

export const resolutionPaths = {
  pending: (caseId: string) =>
    `/api/v1/kadi/cases/${encodeURIComponent(caseId)}/resolutions?status=pending`,
  feedback: (caseId: string, decisionId: string) =>
    `/api/v1/kadi/cases/${encodeURIComponent(caseId)}/resolutions/${encodeURIComponent(decisionId)}/feedback`,
};

export function formatScore(score: number | null | undefined): string | null {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return `${Math.round(score * 100)}%`;
}

/** One row per signal; `value` is null when the signal could not be computed. */
export function signalRows(signals: ResolutionSignal[]): { signal: SignalName; value: string | null }[] {
  return signals.map((s) => ({
    signal: s.signal,
    value: s.status === "AVAILABLE" ? formatScore(s.score) : null,
  }));
}
