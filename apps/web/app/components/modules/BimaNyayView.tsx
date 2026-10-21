"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";
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

  // Every field feeds a legal appeal letter, so none may be blank or invented.
  const bimaNyayFormComplete =
    policyNumber.trim() !== "" &&
    insurerName.trim() !== "" &&
    policyAgeYears.trim() !== "" &&
    claimedAmount.trim() !== "" &&
    deniedAmount.trim() !== "" &&
    denialReason.trim() !== "" &&
    diagnosis.trim() !== "";

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

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Input Form */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          padding: "1.25rem",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-subtle)",
          marginBottom: "1.5rem",
        }}
      >
        <h3 style={{ marginBottom: "1rem" }}>{t.formTitle}</h3>

        <div className="grid-2" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.policyNumber}</label>
            <input type="text" className="input-field" value={policyNumber} onChange={(e) => setPolicyNumber(e.target.value)} />
          </div>
          <div>
            <label className="input-label">{t.insurerName}</label>
            <input type="text" className="input-field" value={insurerName} onChange={(e) => setInsurerName(e.target.value)} />
          </div>
        </div>

        <div className="grid-3" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.policyAgeYears}</label>
            <input type="number" step="0.5" className="input-field" value={policyAgeYears} onChange={(e) => setPolicyAgeYears(e.target.value)} />
          </div>
          <div>
            <label className="input-label">{t.claimedAmount}</label>
            <input type="number" className="input-field" value={claimedAmount} onChange={(e) => setClaimedAmount(e.target.value)} />
          </div>
          <div>
            <label className="input-label">{t.deniedAmount}</label>
            <input type="number" className="input-field" value={deniedAmount} onChange={(e) => setDeniedAmount(e.target.value)} />
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.denialCategory}</label>
            <select className="select-field" value={denialCategory} onChange={(e) => setDenialCategory(e.target.value)}>
              <option value="PED_NON_DISCLOSURE">{t.denialCategoryPedNonDisclosure}</option>
              <option value="ROOM_RENT_CAPPING">{t.denialCategoryRoomRentCapping}</option>
              <option value="INVESTIGATION_ONLY">{t.denialCategoryInvestigationOnly}</option>
              <option value="DELAYED_INTIMATION">{t.denialCategoryDelayedIntimation}</option>
            </select>
          </div>
          <div>
            <label className="input-label">{t.diagnosis}</label>
            <input type="text" className="input-field" value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} />
          </div>
        </div>

        <div style={{ marginBottom: "1.25rem" }}>
          <label className="input-label">{t.denialReason}</label>
          <textarea className="textarea-field" rows={2} value={denialReason} onChange={(e) => setDenialReason(e.target.value)} />
        </div>

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={handleAnalyze}
          disabled={isLoading || !bimaNyayFormComplete}
        >
          {isLoading ? (
            <>
              <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
              {t.analyzing}
            </>
          ) : (
            <>⚖️ {t.analyzeBtn}</>
          )}
        </button>
      </div>

      {/* Error State */}
      {analyzeApi.error && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1.5rem",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid var(--status-danger)",
            borderRadius: "var(--radius-md)",
            color: "#fca5a5",
            fontSize: "0.9rem",
          }}
        >
          ⚠️ {analyzeApi.error}
        </div>
      )}

      {/* Real Audit Results */}
      {result && (
        <div>
          <ClinicalSection result={result} caseId={caseId} caseToken={caseToken} insurerName={insurerName} />
          <DisputeSummary result={result} currentLang={currentLang} />
          <AppealDrafts result={result} currentLang={currentLang} />
          {/* Real Statutory SLA Tracker */}
          <SlaTimeline timeline={timelineApi.data} loading={timelineApi.loading} insurerName={insurerName} currentLang={currentLang} />
        </div>
      )}
    </div>
  );
};
