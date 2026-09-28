"use client";

import React, { useState } from "react";
import { ReviewerProfile, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { VerificationBadge } from "./Attribution";

/**
 * Choose a reviewer: from the directory (only independently verified reviewers, or demo
 * fixtures in demo mode, are ever listed) or by the reviewer ID your own doctor or
 * pharmacist gives you. A looked-up profile is shown — with its honest verification
 * label — before it can be assigned.
 */
export const AssignReviewer: React.FC<{
  directory: ReviewerProfile[];
  disabled?: boolean;
  label?: string;
  onAssign: (reviewerId: string) => void;
}> = ({ directory, disabled, label = "Assign reviewer", onAssign }) => {
  const [selected, setSelected] = useState("");
  const [idInput, setIdInput] = useState("");
  const [looked, setLooked] = useState<ReviewerProfile | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const lookup = async () => {
    setLookupError(null);
    setLooked(null);
    try {
      setLooked(await clinicalRequest<ReviewerProfile>(`${clinicalPaths.reviewers()}/${encodeURIComponent(idInput.trim())}`));
    } catch {
      setLookupError("No reviewer with that ID. Check the ID your doctor or pharmacist gave you.");
    }
  };

  return (
    <div style={{ marginTop: "0.5rem", display: "grid", gap: "0.5rem" }}>
      {directory.length > 0 ? (
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <select className="select-field" aria-label="Choose a listed reviewer" value={selected} onChange={(e) => setSelected(e.target.value)}>
            <option value="">Choose a listed reviewer…</option>
            {directory.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} — {d.specialty ?? d.category_label} — {d.verification_label}
              </option>
            ))}
          </select>
          <button type="button" className="btn btn-secondary" disabled={disabled || !selected} onClick={() => onAssign(selected)}>
            {label}
          </button>
        </div>
      ) : (
        <p style={{ fontSize: "0.8rem", opacity: 0.85 }}>
          No independently verified reviewers are listed. Ask your own doctor or pharmacist to register at the reviewer
          workspace and give you their reviewer ID.
        </p>
      )}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <input
          className="input-field"
          style={{ maxWidth: 260 }}
          aria-label="Reviewer ID"
          placeholder="Reviewer ID (REV-…)"
          value={idInput}
          onChange={(e) => {
            setIdInput(e.target.value);
            setLooked(null);
          }}
        />
        <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} disabled={!idInput.trim()} onClick={lookup}>
          Look up
        </button>
      </div>
      {lookupError && <p style={{ fontSize: "0.8rem", color: "#fca5a5" }}>{lookupError}</p>}
      {looked && (
        <div style={{ fontSize: "0.85rem", display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          <span>
            <strong>{looked.name}</strong> · {looked.category_label}
            {looked.specialty ? ` · ${looked.specialty}` : ""} ·{" "}
            <VerificationBadge status={looked.verification_status} label={looked.verification_label} />
          </span>
          <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => onAssign(looked.id)}>
            {label}: {looked.name}
          </button>
        </div>
      )}
    </div>
  );
};
