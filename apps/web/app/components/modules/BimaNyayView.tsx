"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";
import { StatePanel } from "../clinical/StatePanel";
import { AppealDrafts } from "./bimanyay/AppealDrafts";
import { ClinicalSection } from "./bimanyay/ClinicalSection";
import { DisputeSummary } from "./bimanyay/DisputeSummary";
import { SlaTimeline } from "./bimanyay/SlaTimeline";
import type { DisputeAuditResult, GrievanceTrackerResponse } from "./bimanyay/types";

interface BimaNyayViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

/** BimaNyay: audit a claim denial against IRDAI rules, draft the three-tier appeals and
 *  track the statutory deadlines. The dossier form lives here; results are composed. */
export const BimaNyayView: React.FC<BimaNyayViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.bimanyay;
  const analyzeApi = useApi<DisputeAuditResult>();
  const timelineApi = useApi<GrievanceTrackerResponse>();

  // SEC-04: when a case is active, the dispute record is linked to it (and becomes
  // evidence a clinical reviewer can see, labelled PATIENT_PROVIDED).
  const caseQuery = caseId ? `&case_id=${encodeURIComponent(caseId)}` : "";

  // Form State
  // Empty by default: pre-filled values were submitted verbatim by users who did not
  // edit them, producing determinations about a fabricated person.
  const [policyNumber, setPolicyNumber] = useState("");
  const [insurerName, setInsurerName] = useState("");
  const [policyAgeYears, setPolicyAgeYears] = useState("");
  const [claimedAmount, setClaimedAmount] = useState("");
  const [deniedAmount, setDeniedAmount] = useState("");
  const [denialCategory, setDenialCategory] = useState("PED_NON_DISCLOSURE");
  const [denialReason, setDenialReason] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  // The day the deadlines are counted from (the timeline request's date_initiated).
  const [countedFrom, setCountedFrom] = useState<string | null>(null);

  // Every field feeds a legal appeal letter, so none may be blank or invented.
  const bimaNyayFormComplete =
    policyNumber.trim() !== "" &&
    insurerName.trim() !== "" &&
    policyAgeYears.trim() !== "" &&
    claimedAmount.trim() !== "" &&
    deniedAmount.trim() !== "" &&
    denialReason.trim() !== "" &&
    diagnosis.trim() !== "";
  const missingCount = [policyNumber, insurerName, policyAgeYears, claimedAmount, deniedAmount, denialReason, diagnosis].filter(
    (v) => v.trim() === ""
  ).length;

  const handleAnalyze = async () => {
    if (!bimaNyayFormComplete) return;
    await analyzeApi.execute(`/api/v1/bimanyay/analyze?language=${currentLang}${caseQuery}`, {
      headers: caseAuthHeaders(caseToken),
      body: {
        policy_number: policyNumber,
        insurer_name: insurerName,
        policy_age_years: parseFloat(policyAgeYears) || 0,
        claimed_amount: parseFloat(claimedAmount) || 0,
        denied_or_deducted_amount: parseFloat(deniedAmount) || 0,
        denial_category: denialCategory,
        denial_reason_raw: denialReason,
        diagnosis,
      },
    });

    // Also fetch timeline
    const today = new Date().toISOString().split("T")[0];
    setCountedFrom(today);
    await timelineApi.execute("/api/v1/bimanyay/timeline", {
      body: {
        insurer_name: insurerName,
        date_initiated: today,
        claim_number: policyNumber,
        current_tier: "LEVEL_1_GRO",
      },
    });
  };

  const result = analyzeApi.data;
  const isLoading = analyzeApi.loading || timelineApi.loading;
  const claimed = parseFloat(claimedAmount);
  const denied = parseFloat(deniedAmount);
  const deniedShare = claimed > 0 && denied >= 0 ? Math.min(1, denied / claimed) : null;

  const text = (id: string, label: string, value: string, set: (v: string) => void, number = false, step?: string) => (
    <div className="ds-field">
      <label className="input-label" htmlFor={id}>
        {label}
        <span className="ds-required">required</span>
      </label>
      <input
        id={id}
        type={number ? "number" : "text"}
        inputMode={number ? "decimal" : undefined}
        min={number ? 0 : undefined}
        step={step}
        className="input-field"
        value={value}
        onChange={(e) => set(e.target.value)}
      />
    </div>
  );

  return (
    <div className="module-panel">
      <header className="module-head">
        <p className="lp-kicker">BimaNyay · after an insurance denial</p>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </header>

      <section className="case-panel bn-card" aria-labelledby="bm-form-title">
        <div className="case-panel-head">
          <h3 id="bm-form-title">{t.formTitle}</h3>
          <span className="timeline-count">
            {caseId ? "Linked to your case" : "Not linked to a case — works from what you type"}
          </span>
        </div>
        <p className="bn-fine">
          Copy these from the insurer&apos;s denial letter. Every field goes into the appeal drafts, so nothing is guessed or
          filled in for you.
        </p>

        <fieldset className="bm-group">
          <legend>The policy</legend>
          <div className="bm-grid-3">
            {text("bm-policy", t.policyNumber, policyNumber, setPolicyNumber)}
            {text("bm-insurer", t.insurerName, insurerName, setInsurerName)}
            {text("bm-tenure", t.policyAgeYears, policyAgeYears, setPolicyAgeYears, true, "0.5")}
          </div>
        </fieldset>

        <fieldset className="bm-group">
          <legend>The money</legend>
          <div className="ds-grid">
            {text("bm-claimed", t.claimedAmount, claimedAmount, setClaimedAmount, true)}
            {text("bm-denied", t.deniedAmount, deniedAmount, setDeniedAmount, true)}
          </div>
          {deniedShare !== null && (
            <div className="bm-share" aria-live="polite">
              <div className="bm-share-bar" aria-hidden="true">
                <span style={{ width: `${(deniedShare * 100).toFixed(1)}%` }} />
              </div>
              <span>
                {inr(denied)} of {inr(claimed)} denied — {(deniedShare * 100).toFixed(0)}% of the claim
                {denied > claimed && " (the denied amount is larger than the claim — check the figures)"}
              </span>
            </div>
          )}
        </fieldset>

        <fieldset className="bm-group">
          <legend>The denial</legend>
          <div className="ds-grid">
            <div className="ds-field">
              <label className="input-label" htmlFor="bm-category">
                {t.denialCategory}
                <span className="ds-required">required</span>
              </label>
              <select id="bm-category" className="select-field" value={denialCategory} onChange={(e) => setDenialCategory(e.target.value)}>
                <option value="PED_NON_DISCLOSURE">{t.denialCategoryPedNonDisclosure}</option>
                <option value="ROOM_RENT_CAPPING">{t.denialCategoryRoomRentCapping}</option>
                <option value="INVESTIGATION_ONLY">{t.denialCategoryInvestigationOnly}</option>
                <option value="DELAYED_INTIMATION">{t.denialCategoryDelayedIntimation}</option>
              </select>
            </div>
            {text("bm-diagnosis", t.diagnosis, diagnosis, setDiagnosis)}
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="bm-reason">
              {t.denialReason}
              <span className="ds-required">required</span>
            </label>
            <textarea id="bm-reason" className="textarea-field" rows={3} value={denialReason} onChange={(e) => setDenialReason(e.target.value)} />
          </div>
        </fieldset>

        <div className="ds-form-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAnalyze}
            disabled={isLoading || !bimaNyayFormComplete}
          >
            {isLoading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                {t.analyzing}
              </>
            ) : (
              t.analyzeBtn
            )}
          </button>
          {!bimaNyayFormComplete && (
            <span className="ds-hint">
              {missingCount} field{missingCount === 1 ? "" : "s"} still empty.
            </span>
          )}
        </div>
        {analyzeApi.error && (
          <StatePanel kind="error" onRetry={handleAnalyze}>
            Could not check the denial: {analyzeApi.error}
          </StatePanel>
        )}
      </section>

      {/* Real Audit Results */}
      {result && (
        <div className="bm-results">
          <DisputeSummary result={result} currentLang={currentLang} />
          <ClinicalSection result={result} caseId={caseId} caseToken={caseToken} insurerName={insurerName} />
          <AppealDrafts result={result} currentLang={currentLang} />
          {/* Real Statutory SLA Tracker */}
          <SlaTimeline
            timeline={timelineApi.data}
            loading={timelineApi.loading}
            error={timelineApi.error}
            countedFrom={countedFrom}
            insurerName={insurerName}
            currentLang={currentLang}
          />
        </div>
      )}
    </div>
  );
};
