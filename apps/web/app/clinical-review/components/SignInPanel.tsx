"use client";

import React, { useState } from "react";
import { ReviewerProfile, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { Guard, panel } from "../types";

const EMPTY_REGISTRATION = {
  name: "",
  category: "DOCTOR",
  designation: "",
  specialty: "",
  registration_number: "",
  registration_authority: "",
  affiliation: "",
  standing_disclosures: "",
};

/** Paste an existing reviewer credential, or register and receive one (shown once). */
export function SignInPanel({
  guard,
  openWithCredential,
  onIssued,
}: {
  guard: Guard;
  openWithCredential: (token: string) => Promise<void>;
  onIssued: (token: string) => void;
}) {
  const [tokenInput, setTokenInput] = useState("");
  const [reg, setReg] = useState(EMPTY_REGISTRATION);

  const register = () =>
    guard(async () => {
      const body = Object.fromEntries(Object.entries(reg).map(([k, v]) => [k, v.trim() || null]));
      const res = await clinicalRequest<{ reviewer: ReviewerProfile; reviewer_token: string }>(clinicalPaths.reviewers(), {
        method: "POST",
        body,
      });
      onIssued(res.reviewer_token);
      await openWithCredential(res.reviewer_token);
    });

  return (
    <div className="grid-2">
      <section style={panel} aria-labelledby="use-credential">
        <h3 id="use-credential">Use your reviewer credential</h3>
        <input
          className="input-field"
          type="password"
          aria-label="Reviewer credential"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
        />
        <button type="button" className="btn btn-primary" style={{ marginTop: "0.75rem" }} disabled={!tokenInput} onClick={() => openWithCredential(tokenInput.trim())}>
          Open workspace
        </button>
      </section>
      <section style={panel} aria-labelledby="register-reviewer">
        <h3 id="register-reviewer">Register as a reviewer</h3>
        {(
          [
            ["name", "Full name"],
            ["designation", "Professional designation"],
            ["specialty", "Specialty"],
            ["registration_number", "Registration number (shown as self-declared)"],
            ["registration_authority", "Registration authority (e.g. State Medical Council)"],
            ["affiliation", "Affiliation"],
            ["standing_disclosures", "Standing disclosures (insurer/hospital ties)"],
          ] as const
        ).map(([key, label]) => (
          <div key={key} style={{ marginBottom: "0.5rem" }}>
            <label className="input-label" htmlFor={`reg-${key}`}>
              {label}
            </label>
            <input id={`reg-${key}`} className="input-field" value={reg[key]} onChange={(e) => setReg({ ...reg, [key]: e.target.value })} />
          </div>
        ))}
        <label className="input-label" htmlFor="reg-category">
          Category
        </label>
        <select id="reg-category" className="select-field" value={reg.category} onChange={(e) => setReg({ ...reg, category: e.target.value })}>
          <option value="DOCTOR">Doctor</option>
          <option value="PHARMACIST">Pharmacist</option>
          <option value="MEDICAL_TRANSCRIPTIONIST">Medical transcriptionist</option>
          <option value="TRAINED_ANNOTATOR">Trained annotator</option>
        </select>
        <button type="button" className="btn btn-secondary" style={{ marginTop: "0.75rem" }} disabled={reg.name.trim().length < 2} onClick={register}>
          Register
        </button>
      </section>
    </div>
  );
}
