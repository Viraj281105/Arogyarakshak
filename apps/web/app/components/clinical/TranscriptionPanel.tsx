"use client";

import React, { useCallback, useEffect, useState } from "react";
import { API_BASE, caseAuthHeaders } from "../../hooks/useApi";
import { ReviewerProfile, TranscriptionTask, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { ProvenanceBadge } from "./Attribution";

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
export const TranscriptionPanel: React.FC<{ caseId: string; caseToken?: string }> = ({ caseId, caseToken }) => {
  const [tasks, setTasks] = useState<TranscriptionTask[]>([]);
  const [medicines, setMedicines] = useState<MedicineEntity[]>([]);
  const [readers, setReaders] = useState<ReviewerProfile[]>([]);
  const [selected, setSelected] = useState<Record<string, string>>({});
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
  }, [fetchAll]);

  const load = async () => apply(await fetchAll());

  const act = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      await load();
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

  const assign = (taskId: string) =>
    act(() =>
      clinicalRequest(clinicalPaths.assignTranscription(caseId, taskId), {
        method: "POST",
        caseToken,
        body: { reviewer_id: selected[taskId], share_with_reviewer_consent: shareConsent },
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
      {error && (
        <div role="alert" style={{ color: "#fca5a5", fontSize: "0.85rem", marginBottom: "0.75rem" }}>
          ⚠️ {error}
        </div>
      )}

      {medicines.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div className="stat-label">Does a medicine look misread? Flag it:</div>
          {medicines.map((m) => (
            <button
              key={m.id}
              type="button"
              className="btn"
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
              {task.field_type.replace("_", " ")} · <span className={`badge ${task.risk_level === "HIGH" ? "badge-danger" : "badge-info"}`}>{task.risk_level} risk</span>
            </strong>
            <span className={`badge ${task.status === "RESOLVED" ? "badge-success" : task.status === "HUMAN_ESCALATION_REQUIRED" ? "badge-danger" : "badge-warning"}`}>
              {STATUS_TEXT[task.status]}
            </span>
          </div>
          <p style={{ fontSize: "0.8rem", margin: "0.35rem 0" }}>
            Context: <code>{task.masked_context}</code> · readings {task.readings_received}/{task.required_reviews} · readers assigned{" "}
            {task.assigned_reviewer_count}
          </p>
          {task.final_value && (
            <p>
              Human-confirmed reading: <strong>{task.final_value}</strong> <ProvenanceBadge provenance={task.final_value_provenance} />
            </p>
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
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
              <select
                className="select-field"
                aria-label="Choose a reader"
                value={selected[task.task_id] ?? ""}
                onChange={(e) => setSelected((prev) => ({ ...prev, [task.task_id]: e.target.value }))}
              >
                <option value="">Choose a reader…</option>
                {readers.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} — {r.category_label} — {r.verification_label}
                  </option>
                ))}
              </select>
              <button type="button" className="btn btn-secondary" disabled={!selected[task.task_id] || !shareConsent} onClick={() => assign(task.task_id)}>
                Assign reader
              </button>
            </div>
          )}
        </div>
      ))}
    </section>
  );
};
