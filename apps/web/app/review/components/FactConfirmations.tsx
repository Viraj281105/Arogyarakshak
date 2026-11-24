"use client";

import React from "react";
import { FactDecision } from "../../lib/clinical";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";
import { FactInput, ReviewerDetail } from "../types";

/** Clinical facts the reviewer confirms, rejects or cannot determine from the records. */
export function FactConfirmations({
  detail,
  factInput,
  setFactInput,
  onDecide,
}: {
  detail: ReviewerDetail;
  factInput: FactInput;
  setFactInput: (value: FactInput) => void;
  onDecide: (fact: FactDecision) => void;
}) {
  return (
    <div style={{ marginTop: "1rem" }}>
      <h4>Facts to confirm</h4>
      {detail.facts.map((f) => (
        <div key={f.fact_id} style={{ borderTop: "1px solid var(--border-subtle)", padding: "0.75rem 0" }}>
          <p>{f.fact_question}</p>
          {f.decision !== "PENDING" ? (
            <p>
              <span className={f.decision === "CONFIRMED" ? TONE_CLASS["human-reviewed"] : TONE_CLASS.warning}>
                {humanizeEnum(f.decision)}
              </span>{" "}
              {f.reviewer_note}
            </p>
          ) : (
            <>
              <select
                className="select-field"
                aria-label="Decision"
                value={factInput[f.fact_id]?.decision ?? ""}
                onChange={(e) => setFactInput({ ...factInput, [f.fact_id]: { ...(factInput[f.fact_id] ?? { note: "", confirm: false }), decision: e.target.value } })}
              >
                <option value="">Decide…</option>
                <option value="CONFIRMED">Confirmed by the records</option>
                <option value="REJECTED">Not supported by the records</option>
                <option value="CANNOT_DETERMINE">Cannot determine from the records</option>
              </select>
              <textarea
                className="textarea-field"
                placeholder="Note (optional)"
                value={factInput[f.fact_id]?.note ?? ""}
                onChange={(e) => setFactInput({ ...factInput, [f.fact_id]: { ...(factInput[f.fact_id] ?? { decision: "", confirm: false }), note: e.target.value } })}
              />
              <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", marginTop: "0.5rem" }}>
                <input
                  type="checkbox"
                  checked={factInput[f.fact_id]?.confirm ?? false}
                  onChange={(e) => setFactInput({ ...factInput, [f.fact_id]: { ...(factInput[f.fact_id] ?? { decision: "", note: "" }), confirm: e.target.checked } })}
                />
                <span>{detail.fact_decision_confirmation_text}</span>
              </label>
              <button
                type="button"
                className="btn btn-primary"
                style={{ marginTop: "0.5rem" }}
                disabled={!factInput[f.fact_id]?.decision || !factInput[f.fact_id]?.confirm}
                onClick={() => onDecide(f)}
              >
                Record decision
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
