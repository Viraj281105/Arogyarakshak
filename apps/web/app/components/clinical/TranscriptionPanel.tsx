"use client";

import React, { useCallback, useEffect, useState } from "react";
import { API_BASE, caseAuthHeaders } from "../../hooks/useApi";
import { ReviewerProfile, TranscriptionTask, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { AssignReviewer } from "./AssignReviewer";
import { ProvenanceBadge } from "./Attribution";
import { StatePanel } from "./StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";

interface MedicineEntity {
  id: string;
  name: string;
  type: string;
}

const STATUS_TEXT: Record<TranscriptionTask["status"], string> = {
  OPEN: "Awaiting a human reading",
  AWAITING_SECOND_REVIEW: "One reading in — a second independent reading is required",
  RESOLVED: "Resolved by independent human readings",
  HUMAN_ESCALATION_REQUIRED: "Readers disagreed or could not read it — confirm with the prescriber or pharmacist",
  CANCELLED: "Cancelled",
};

/**
 * DawaCheck: uncertain prescription readings go to human transcription reviewers
 * (pharmacists, medical transcriptionists, trained annotators) — not to "doctors", and
 * never silently into a medication fact. Possible-medication fields need two agreeing
 * independent readings.
 */
function statusText(task: TranscriptionTask): string {
  if (task.status === "RESOLVED" && task.outcome === "NOT_APPLIED") {
    return "Readers agreed, but the reading could not be applied — the entry stays unsettled";
  }
  return STATUS_TEXT[task.status];
}

function statusTone(task: TranscriptionTask): string {
  if (task.status === "RESOLVED" && task.outcome !== "NOT_APPLIED") return TONE_CLASS["human-reviewed"];
  if (task.status === "HUMAN_ESCALATION_REQUIRED") return TONE_CLASS.danger;
  return TONE_CLASS.warning;
}

export const TranscriptionPanel: React.FC<{ caseId: string; caseToken?: string; refreshKey?: number; onChanged?: () => void }> = ({
  caseId,
  caseToken,
  refreshKey = 0,
  onChanged,
}) => {
  const [tasks, setTasks] = useState<TranscriptionTask[]>([]);
  const [medicines, setMedicines] = useState<MedicineEntity[]>([]);
  const [readers, setReaders] = useState<ReviewerProfile[]>([]);
  const [shareConsent, setShareConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(
    () =>
      Promise.all([
        clinicalRequest<TranscriptionTask[]>(clinicalPaths.transcriptions(caseId), { caseToken }),
        fetch(`${API_BASE}/api/v1/kadi/cases/${encodeURIComponent(caseId)}`, { headers: caseAuthHeaders(caseToken) }).then((r) =>
          r.ok ? (r.json() as Promise<{ entities: MedicineEntity[] }>) : { entities: [] as MedicineEntity[] }
        ),
        clinicalRequest<ReviewerProfile[]>(clinicalPaths.reviewers()),
      ]),
    [caseId, caseToken]
  );

  const apply = ([list, caseRes, directory]: [TranscriptionTask[], { entities: MedicineEntity[] }, ReviewerProfile[]]) => {
    setTasks(list);
    setMedicines(caseRes.entities.filter((e) => e.type === "medicine"));
    setReaders(directory);
  };

  useEffect(() => {
    let cancelled = false;
    fetchAll()
      .then((result) => {
        if (!cancelled) apply(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
    // refreshKey: a sibling panel (DawaCheck's case medicines) created a task.
  }, [fetchAll, refreshKey]);

  const load = async () => apply(await fetchAll());

  const act = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const flag = (entityId: string) =>
    act(() =>
      clinicalRequest(clinicalPaths.transcriptions(caseId), {
        method: "POST",
        caseToken,
        body: { entity_id: entityId, field_type: "MEDICINE_NAME" },
      })
    );

  const assign = (taskId: string, reviewerId: string) =>
    act(() =>
      clinicalRequest(clinicalPaths.assignTranscription(caseId, taskId), {
        method: "POST",
        caseToken,
        body: { reviewer_id: reviewerId, share_with_reviewer_consent: shareConsent },
      })
    );

  const flaggedEntities = new Set(tasks.filter((t) => t.status !== "CANCELLED").map((t) => t.entity_id));

  return (
    <section
      aria-labelledby="transcription-title"
      style={{ border: "1px solid var(--border-medium)", borderRadius: "var(--radius-md)", padding: "1.25rem", marginBottom: "1.5rem" }}
    >
      <h3 id="transcription-title">✍️ Unclear prescription text — human reading</h3>
      <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
        When the software is unsure what a prescription says, it asks trained human readers instead of guessing. A medicine
        name, strength, frequency, route or duration needs two independent readings that agree. ArogyaRakshak never stores
        the document image — readers look at the original you hold.
      </p>
      {error && <StatePanel kind="error">{error}</StatePanel>}
      {tasks.length === 0 && !error && (
        <StatePanel kind="empty">
          No unclear readings are waiting for a human reader. If a medicine below looks misread, flag it.
        </StatePanel>
      )}

      {medicines.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div className="stat-label">Does a medicine look misread? Flag it:</div>
          {medicines.map((m) => (
            <button
              key={m.id}
              type="button"
              className="btn btn-compact"
              style={{ border: "1px solid var(--border-subtle)", margin: "0.25rem 0.5rem 0 0" }}
              disabled={flaggedEntities.has(m.id)}
              onClick={() => flag(m.id)}
            >
              {flaggedEntities.has(m.id) ? `✓ ${m.name} flagged` : `Flag “${m.name}”`}
            </button>
          ))}
        </div>
      )}

      {tasks.length > 0 && (
        <label className="consent-wrapper" style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", margin: "0.5rem 0" }}>
          <input type="checkbox" checked={shareConsent} onChange={(e) => setShareConsent(e.target.checked)} />
          <span style={{ fontSize: "0.85rem" }}>I agree to share the masked, redacted text of these readings with the readers I assign.</span>
        </label>
      )}

      {tasks.map((task) => (
        <div key={task.task_id} style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.75rem", marginTop: "0.75rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
            <strong>
              {humanizeEnum(task.field_type)} ·{" "}
              <span className={task.risk_level === "HIGH" ? TONE_CLASS.danger : TONE_CLASS.neutral}>
                {task.risk_level === "HIGH" ? "Two readers required" : "One reader required"}
              </span>
            </strong>
            <span className={statusTone(task)}>{statusText(task)}</span>
          </div>
          <p style={{ fontSize: "0.8rem", margin: "0.35rem 0" }}>
            Context: <code>{task.masked_context}</code> · readings {task.readings_received}/{task.required_reviews} · readers assigned{" "}
            {task.assigned_reviewer_count}
          </p>
          {task.final_value && task.outcome !== "NOT_APPLIED" && (
            <p>
              Human-confirmed reading: <strong>{task.final_value}</strong> <ProvenanceBadge provenance={task.final_value_provenance} />
            </p>
          )}
          {task.final_value && task.outcome === "NOT_APPLIED" && (
            <p style={{ fontSize: "0.85rem" }}>
              Readers agreed on <strong>{task.final_value}</strong>, but it could not be placed into the extracted entry, so the
              medicine is <strong>not</strong> treated as settled or price-checked.
            </p>
          )}
          {task.resolution_reason && task.status !== "OPEN" && (
            <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>{task.resolution_reason}</p>
          )}
          {task.readings.length > 0 && (
            <ul style={{ fontSize: "0.8rem", paddingLeft: "1.1rem" }}>
              {task.readings.map((r, i) => (
                <li key={i}>
                  {r.reviewer_role ?? "Reader"}: {r.unreadable ? "could not read it" : r.value}
                </li>
              ))}
            </ul>
          )}
          {(task.status === "OPEN" || task.status === "AWAITING_SECOND_REVIEW") && (
            <AssignReviewer
              directory={readers}
              disabled={!shareConsent}
              label="Assign reader"
              onAssign={(reviewerId) => assign(task.task_id, reviewerId)}
            />
          )}
        </div>
      ))}
    </section>
  );
};
