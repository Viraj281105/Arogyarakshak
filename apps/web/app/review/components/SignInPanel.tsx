"use client";

import React, { useState } from "react";
import { ReviewerProfile, clinicalPaths, clinicalRequest } from "../../lib/clinical";
import { Guard } from "../types";
import { useT } from "../../i18n/useT";

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
  const tr = useT();
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
    <div className="rv-signin">
      <h2 className="sr-only">{tr("Reviewer access")}</h2>
      <section className="case-panel bn-card" aria-labelledby="use-credential">
        <h3 id="use-credential">{tr("Use your reviewer credential")}</h3>
        <p className="bn-fine">{tr("Paste the credential you were given when you registered. It is kept in this tab's memory only — reloading the page means pasting it again.")}</p>
        <input
          className="input-field"
          type="password"
          autoComplete="off"
          aria-label={tr("Reviewer credential")}
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && tokenInput.trim()) void openWithCredential(tokenInput.trim());
          }}
        />
        <div>
          <button type="button" className="btn btn-primary" disabled={!tokenInput} onClick={() => openWithCredential(tokenInput.trim())}>{tr("Open workspace")}</button>
        </div>
      </section>
      <section className="case-panel bn-card" aria-labelledby="register-reviewer">
        <h3 id="register-reviewer">{tr("Register as a reviewer")}</h3>
        <p className="bn-fine">{tr("Your registration number is shown to patients as self-declared: ArogyaRakshak is not connected to any council registry. You receive a credential once, at the end.")}</p>
        <div className="ds-grid">
        {(
          [
            ["name", tr("Full name")],
            ["designation", tr("Professional designation")],
            ["specialty", "Specialty"],
            ["registration_number", tr("Registration number (shown as self-declared)")],
            ["registration_authority", tr("Registration authority (e.g. State Medical Council)")],
            ["affiliation", "Affiliation"],
            ["standing_disclosures", tr("Standing disclosures (insurer/hospital ties)")],
          ] as const
        ).map(([key, label]) => (
          <div key={key} className="ds-field">
            <label className="input-label" htmlFor={`reg-${key}`}>
              {label}
            </label>
            <input id={`reg-${key}`} className="input-field" value={reg[key]} onChange={(e) => setReg({ ...reg, [key]: e.target.value })} />
          </div>
        ))}
        <div className="ds-field">
          <label className="input-label" htmlFor="reg-category">{tr("Category")}</label>
          <select id="reg-category" className="select-field" value={reg.category} onChange={(e) => setReg({ ...reg, category: e.target.value })}>
            <option value="DOCTOR">{tr("Doctor")}</option>
            <option value="PHARMACIST">{tr("Pharmacist")}</option>
            <option value="MEDICAL_TRANSCRIPTIONIST">{tr("Medical transcriptionist")}</option>
            <option value="TRAINED_ANNOTATOR">{tr("Trained annotator")}</option>
          </select>
        </div>
        </div>
        <div>
          <button type="button" className="btn btn-secondary" disabled={reg.name.trim().length < 2} onClick={register}>{tr("Register and get a credential")}</button>
        </div>
      </section>
    </div>
  );
}
