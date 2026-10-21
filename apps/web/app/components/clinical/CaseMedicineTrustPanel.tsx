"use client";

import React, { useCallback, useEffect, useState } from "react";
import { clinicalPaths, clinicalRequest, Provenance } from "../../lib/clinical";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";
import { describePriceCheck, PriceCheck } from "../../lib/dawacheck";
import { ProvenanceBadge } from "./Attribution";
import { StatePanel } from "./StatePanel";
import { PriceBar } from "../modules/dawacheck/PriceBar";
import { ExplainTrail } from "../ExplainTrail";
import type { Explanation } from "../../lib/explanation";
import type { Language } from "../../translations";

export interface CaseMedicineRow {
  entity_id: string;
  brand_name: string;
  benchmark: PriceCheck | null;
  note: string | null;
  name_provenance: Provenance;
  transcription_task_id: string | null;
  transcription_status: string | null;
  trust: { state?: string; label?: string; benchmarkable?: boolean; reasons?: string[] };
  /** "Why am I seeing this?" trail (ADR-017). */
  explanation?: Explanation | null;
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
  lang?: Language;
}> = ({ caseId, caseToken, refreshKey = 0, onChanged, lang = "en" }) => {
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
    <section aria-labelledby="case-medicines-title" className="case-panel bn-card">
      <div className="case-panel-head">
        <h3 id="case-medicines-title">Medicines from your documents</h3>
        {rows && rows.length > 0 && <span className="timeline-count">{rows.length} found</span>}
      </div>
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
        <ul className="dc-meds">
          {rows.map((r) => {
            const state = r.trust?.state ?? "";
            const isBlocked = BLOCKED_STATES.has(state);
            const price = r.benchmark ? describePriceCheck(r.benchmark) : null;
            return (
              <li key={r.entity_id} className={`dc-med ${isBlocked ? "is-blocked" : ""}`}>
                <div className="bn-badges">
                  <strong className="dc-med-name">{r.brand_name}</strong>
                  {isBlocked ? (
                    <span className={TONE_CLASS.warning}>{r.trust?.label ?? humanizeEnum(state)}</span>
                  ) : (
                    <ProvenanceBadge provenance={r.name_provenance} />
                  )}
                  {price && <span className={TONE_CLASS[price.tone]}>{price.badge}</span>}
                </div>
                {(r.trust?.reasons ?? []).length > 0 && (
                  <div className="bn-fine">
                    {(r.trust?.reasons ?? []).map(humanizeEnum).join(" · ")}
                  </div>
                )}
                <div className="dc-med-body">
                  {r.benchmark && price ? (
                    <>
                      <PriceBar check={r.benchmark} view={price} />
                      <div className="bn-fine">
                        {price.billed} · {price.ceiling} (reference: {r.benchmark.active_ingredient})
                      </div>
                      {price.reason && <div className="dc-med-reason">{price.reason}</div>}
                      {price.basisNote && <div className="bn-fine">{price.basisNote}</div>}
                    </>
                  ) : (
                    <span className="bn-fine">{r.note ?? "Not price-checked."}</span>
                  )}
                </div>
                <ExplainTrail explanation={r.explanation} lang={lang} />
                {isBlocked && FLAGGABLE_STATES.has(state) && (
                  <div>
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
