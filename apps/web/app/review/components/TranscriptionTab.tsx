"use client";

import React, { useEffect, useState } from "react";
import { clinicalPaths } from "../../lib/clinical";
import { StatePanel } from "../../components/clinical/StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";
import { Guard, ReviewerCall, TranscriptionView } from "../types";
import { useT } from "../../i18n/useT";

type ReadingInput = { value: string; unreadable: boolean; confidence: string };

/** Blind transcription tasks assigned to this reviewer. Loads when the tab opens. */
export function TranscriptionTab({ guard, call }: { guard: Guard; call: ReviewerCall }) {
  const tr = useT();
  const [tasks, setTasks] = useState<TranscriptionView[]>([]);
  const [readings, setReadings] = useState<Record<string, ReadingInput>>({});

  const loadTasks = () => guard(async () => setTasks(await call<TranscriptionView[]>(clinicalPaths.myTranscriptions())));

  useEffect(() => {
    void loadTasks();
    // Load once per opening of the tab, as the tab button did before.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitReading = (taskId: string) =>
    guard(async () => {
      const r = readings[taskId] ?? { value: "", unreadable: false, confidence: "HIGH" };
      await call(clinicalPaths.transcriptionReadings(taskId), "POST", {
        value: r.unreadable ? null : r.value,
        unreadable: r.unreadable,
        reviewer_confidence: r.confidence,
      });
      await loadTasks();
    }, tr("Reading submitted. Other readers cannot see it."));

  return (
    <section className="case-panel bn-card">
      <h3>{tr("Transcription tasks")}</h3>
      <p style={{ fontSize: "0.85rem" }}>{tr("You are reading as a transcription reviewer. For possible-medication fields you cannot see the software's guess or any other reader's answer. If you cannot read it with confidence, mark it unreadable.")}</p>
      {tasks.length === 0 && <StatePanel kind="empty">{tr("No transcription tasks are assigned to you.")}</StatePanel>}
      {tasks.map((t) => (
        <div key={t.task_id} style={{ borderTop: "1px solid var(--border-subtle)", padding: "0.75rem 0" }}>
          <p>
            <strong>{tr(humanizeEnum(t.field_type))}</strong> ·{" "}
            <span className={TONE_CLASS.warning}>{t.risk_level === "HIGH" ? tr("Two independent readers required") : tr("One reader required")}</span>
          </p>
          <p>{tr("Context:")}{" "}<code>{t.masked_context}</code>
          </p>
          {typeof t.location_hint?.segment_index === "number" && (
            <p style={{ fontSize: "0.8rem" }}>{tr("Where to look on the patient's original: text line")}{" "}{t.location_hint.segment_index + 1}{" "}{tr("from the top (as the scanner counted it; the patient can point to it).")}</p>
          )}
          {t.ocr_candidate && <p style={{ fontSize: "0.8rem" }}>{tr("Software reading: {ocr_candidate}", { ocr_candidate: t.ocr_candidate })}</p>}
          {t.ocr_candidate_hidden && <p style={{ fontSize: "0.8rem" }}>{tr("Software reading hidden (blind review).")}</p>}
          <p style={{ fontSize: "0.75rem", opacity: 0.8 }}>{t.instructions}</p>
          {t.your_reading ? (
            <p>{tr("Your reading:")}{" "}{t.your_reading.unreadable ? tr("unreadable") : t.your_reading.value}</p>
          ) : t.accepting_readings ? (
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
              <input
                className="input-field"
                style={{ maxWidth: 280 }}
                aria-label={tr("What is written")}
                maxLength={200}
                disabled={readings[t.task_id]?.unreadable}
                value={readings[t.task_id]?.value ?? ""}
                onChange={(e) => setReadings({ ...readings, [t.task_id]: { ...(readings[t.task_id] ?? { unreadable: false, confidence: "HIGH" }), value: e.target.value } })}
              />
              <label>
                <input
                  type="checkbox"
                  checked={readings[t.task_id]?.unreadable ?? false}
                  onChange={(e) => setReadings({ ...readings, [t.task_id]: { ...(readings[t.task_id] ?? { value: "", confidence: "HIGH" }), unreadable: e.target.checked } })}
                />{" "}{tr("Unreadable")}</label>
              <select
                className="select-field"
                aria-label={tr("Your confidence")}
                value={readings[t.task_id]?.confidence ?? "HIGH"}
                onChange={(e) => setReadings({ ...readings, [t.task_id]: { ...(readings[t.task_id] ?? { value: "", unreadable: false }), confidence: e.target.value } })}
              >
                <option value="HIGH">{tr("High confidence")}</option>
                <option value="MEDIUM">{tr("Medium confidence")}</option>
                <option value="LOW">{tr("Low confidence")}</option>
              </select>
              <button type="button" className="btn btn-primary" onClick={() => submitReading(t.task_id)}>{tr("Submit reading")}</button>
            </div>
          ) : (
            <p>{tr("This task is closed.")}</p>
          )}
        </div>
      ))}
    </section>
  );
}
