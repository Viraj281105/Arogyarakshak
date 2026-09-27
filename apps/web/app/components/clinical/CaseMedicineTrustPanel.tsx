"use client";

import React, { useCallback, useEffect, useState } from "react";
import { clinicalPaths, clinicalRequest, Provenance } from "../../lib/clinical";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";
import { ProvenanceBadge } from "./Attribution";
import { StatePanel } from "./StatePanel";

export interface CaseMedicineRow {
  entity_id: string;
  brand_name: string;
  benchmark: {
    active_ingredient: string;
    mrp: number;
    nppa_ceiling_price: number;
    is_overcharged: boolean;
    deviation_percentage: number;
    reference_entry_count: number;
  } | null;
  note: string | null;
  name_provenance: Provenance;
  transcription_task_id: string | null;
  transcription_status: string | null;
  trust: { state?: string; label?: string; benchmarkable?: boolean; reasons?: string[] };
}

const BLOCKED_STATES = new Set(["AWAITING_HUMAN_READING", "READERS_DISAGREED", "READING_NOT_APPLIED", "OCR_UNCERTAIN"]);
// States a whole-entry human reading can settle (an open task is already being read).
const FLAGGABLE_STATES = new Set(["READERS_DISAGREED", "READING_NOT_APPLIED", "OCR_UNCERTAIN"]);

/**
 * DawaCheck for the case's own medicines. Every row shows the single trust decision the
 * server made: a medicine whose OCR reading is not settled by humans is NOT price-checked,
 * and the row says why and how to settle it.
 */
export const CaseMedicineTrustPanel: React.FC<{
  caseId: string;
  caseToken?: string;
  refreshKey?: number;
  onChanged?: () => void;
}> = ({ caseId, caseToken, refreshKey = 0, onChanged }) => {
  const [reloadTick, setReloadTick] = useState(0);
  const requestKey = `${caseId}|${refreshKey}|${reloadTick}`;
  // The latest settled response and the request it answers; "loading" is derived from it,
  // so a slow earlier response can never be shown as the answer to a newer request.
  const [result, setResult] = useState<{ key: string; rows: CaseMedicineRow[] | null; error: string | null } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    clinicalRequest<CaseMedicineRow[]>(`/api/v1/dawacheck/cases/${encodeURIComponent(caseId)}/benchmark`, { caseToken })
      .then((data) => {
        if (!cancelled) setResult({ key: requestKey, rows: data, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setResult((prev) => ({ key: requestKey, rows: prev?.rows ?? null, error: err instanceof Error ? err.message : String(err) }));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, caseToken, requestKey]);

  const loading = result?.key !== requestKey;
  const rows = result?.rows ?? null;
  const error = actionError ?? (loading ? null : result?.error ?? null);

  const retry = useCallback(() => {
    setActionError(null);
    setReloadTick((n) => n + 1);
  }, []);

  const askForReading = async (entityId: string) => {
    setBusy(entityId);
    setActionError(null);
    try {
      await clinicalRequest(clinicalPaths.transcriptions(caseId), {
        method: "POST",
        caseToken,
        body: { entity_id: entityId, field_type: "MEDICINE_NAME" },
      });
      onChanged?.();
      retry();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const blocked = (rows ?? []).filter((r) => BLOCKED_STATES.has(r.trust?.state ?? ""));

  return (
    <section aria-labelledby="case-medicines-title" style={{ marginBottom: "1.5rem" }}>
      <h3 id="case-medicines-title">💊 Medicines from your documents</h3>
      {loading && !rows && <StatePanel kind="loading">Checking the medicines extracted from your documents…</StatePanel>}
      {error && (
        <StatePanel kind="error" onRetry={retry}>
          Could not load the medicine price check: {error}
        </StatePanel>
      )}
      {rows && rows.length === 0 && (
        <StatePanel kind="empty">
          No medicines were extracted from this case&apos;s documents. You can still check a medicine by name below.
        </StatePanel>
      )}
      {blocked.length > 0 && (
        <StatePanel kind="warning">
          {blocked.length} medicine{blocked.length === 1 ? " was" : "s were"} not price-checked because part of the entry is not
          settled. ArogyaRakshak never price-checks a medicine it may have misread.
        </StatePanel>
      )}
      {rows && rows.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "0.6rem" }}>
          {rows.map((r) => {
            const state = r.trust?.state ?? "";
            const isBlocked = BLOCKED_STATES.has(state);
            return (
              <li
                key={r.entity_id}
                style={{
                  border: `1px solid ${isBlocked ? "var(--status-warning)" : "var(--border-subtle)"}`,
                  borderRadius: "var(--radius-md)",
                  padding: "0.75rem 0.9rem",
                  minWidth: 0,
                }}
              >
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                  <strong style={{ overflowWrap: "anywhere" }}>{r.brand_name}</strong>
                  {isBlocked ? (
                    <span className={TONE_CLASS.warning}>{r.trust?.label ?? humanizeEnum(state)}</span>
                  ) : (
                    <ProvenanceBadge provenance={r.name_provenance} />
                  )}
                  {r.benchmark &&
                    (r.benchmark.is_overcharged ? (
                      <span className={TONE_CLASS.danger}>Above ceiling (+{r.benchmark.deviation_percentage}%)</span>
                    ) : (
                      <span className={TONE_CLASS.success}>Within ceiling</span>
                    ))}
                </div>
                {(r.trust?.reasons ?? []).length > 0 && (
                  <div style={{ fontSize: "0.78rem", marginTop: "0.3rem", opacity: 0.9 }}>
                    {(r.trust?.reasons ?? []).map(humanizeEnum).join(" · ")}
                  </div>
                )}
                <div style={{ fontSize: "0.85rem", marginTop: "0.35rem" }}>
                  {r.benchmark ? (
                    <>
                      ₹{r.benchmark.mrp.toFixed(2)} per unit vs NPPA ceiling ₹{r.benchmark.nppa_ceiling_price.toFixed(2)} (reference:{" "}
                      {r.benchmark.active_ingredient})
                    </>
                  ) : (
                    <span>{r.note ?? "Not price-checked."}</span>
                  )}
                </div>
                {isBlocked && FLAGGABLE_STATES.has(state) && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-compact"
                      disabled={busy === r.entity_id}
                      onClick={() => askForReading(r.entity_id)}
                    >
                      {busy === r.entity_id ? "Requesting…" : "Ask for a human reading of this entry"}
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
};
