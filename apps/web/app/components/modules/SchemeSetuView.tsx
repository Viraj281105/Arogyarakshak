"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";
import { StatePanel } from "../clinical/StatePanel";

// --- API Response Type (matching backend SchemeResult schema) ---
interface SchemeSource {
  url: string;
  document: string;
  publisher: string;
  date: string | null;
}

interface SchemeResult {
  scheme_name: string;
  estimated_eligibility: "eligible" | "ineligible" | "ambiguous";
  reason: string;
  /** How to claim when eligible; how to verify when ambiguous. */
  claim_guide_steps: string[];
  criteria_evaluated: string[];
  /** Recorded but never decisive: neither scheme defines an official income ceiling. */
  non_determinative_factors: string[];
  /** Factors the engine does not check; the determination stays provisional. */
  criteria_not_evaluated: string[];
  is_provisional: boolean;
  criteria_provenance: string;
  sources: SchemeSource[];
}

// PUT /api/v1/schemesetu/cases/{case_id}/income-profile (#92)
interface IncomeProfileSaveResult {
  background_eligibility: "queued" | "not_ready" | "not_triggered";
  missing_context: string[];
  trigger: { status: "FIRE" | "NO_CHANGE" | "INSUFFICIENT_EVIDENCE"; income_role: string };
}

interface SchemeSetuViewProps {
  currentLang: Language;
  caseId?: string | null;
  caseToken?: string;
}

// The engine normalises state names itself (schemesetu.dialect_normalizer); only
// Maharashtra changes the result today (MJPJAY), PM-JAY applies everywhere.
const STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

// What is checked, from schemesetu/thresholds.py (sources retrieved 2026-09-13).
const SCHEMES_CHECKED = [
  {
    name: "AB PM-JAY (Ayushman Bharat)",
    where: "All states",
    basis:
      "Families listed under SECC-2011 or a state-verified database, ASHA / Anganwadi families, and everyone aged 70 or above. No income ceiling.",
    decided: "Cannot be decided here — none of these facts is asked for, so the result is always “verification needed”.",
    source: "PIB, written reply in the Lok Sabha, 28 Mar 2025",
  },
  {
    name: "MJPJAY (Mahatma Jyotirao Phule Jan Arogya Yojana)",
    where: "Maharashtra",
    basis: "All families in Maharashtra since the integrated scheme of 1 July 2024, with ₹5 lakh cover per family per year.",
    decided: "Decided by your stated state of residence, which is not checked against documents.",
    source: "Government of Maharashtra district portals restating the GR of 28 July 2023",
  },
];

/** "state_of_residence" -> "State of residence"; prose entries pass through. */
const humanize = (s: string) => (/^[a-z_]+$/.test(s) ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : s);

export const SchemeSetuView: React.FC<SchemeSetuViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.schemesetu;
  const api = useApi<SchemeResult[]>();
  // Empty by default: pre-filled values were submitted verbatim by users who did not
  // edit them, producing determinations about a fabricated person.
  const [income, setIncome] = useState("");
  const [state, setState] = useState("");
  const [category, setCategory] = useState("");
  const [medicalNeed, setMedicalNeed] = useState("");
  const [hasChecked, setHasChecked] = useState(false);
  // Opt-in, unchecked by default: income is stored against a case only when the patient asks.
  const [saveToCase, setSaveToCase] = useState(false);
  const profileApi = useApi<IncomeProfileSaveResult>();

  const incomeVal = parseFloat(income);
  const canCheck = !Number.isNaN(incomeVal) && incomeVal >= 0 && !!state.trim();

  const handleCheck = async () => {
    if (!canCheck) return;
    setHasChecked(true);
    await api.execute("/api/v1/schemesetu/eligibility", {
      body: {
        income: incomeVal,
        location_state: state,
        // Neither decides eligibility; a category is sent only when the person chose one.
        ...(category ? { category } : {}),
        medical_need: medicalNeed.trim(),
      },
    });
    if (caseId && saveToCase) {
      await profileApi.execute(`/api/v1/schemesetu/cases/${encodeURIComponent(caseId)}/income-profile`, {
        method: "PUT",
        headers: caseAuthHeaders(caseToken),
        body: { annual_income_inr: incomeVal, state },
      });
    }
  };

  const results = api.data;

  return (
    <div className="module-panel">
      <header className="module-head">
        <p className="lp-kicker">SchemeSetu · government health schemes</p>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </header>

      <section className="case-panel bn-card" aria-labelledby="ss-form-title">
        <h3 id="ss-form-title">Your details</h3>
        <p className="bn-fine">
          Only your state changes the result today. Income is recorded but never decides eligibility, because neither scheme
          sets an official income ceiling. Category and medical need are optional and not used to decide.
        </p>
        <div className="ds-grid">
          <div className="ds-field">
            <label className="input-label" htmlFor="ss-income">
              {t.annualIncome}
              <span className="ds-required">required</span>
            </label>
            <input id="ss-income" type="number" inputMode="decimal" min={0} className="input-field" value={income} onChange={(e) => setIncome(e.target.value)} />
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="ss-state">
              {t.state}
              <span className="ds-required">required</span>
            </label>
            <select id="ss-state" className="select-field" value={state} onChange={(e) => setState(e.target.value)}>
              <option value="" disabled>
                Choose your state or union territory
              </option>
              {STATES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="ss-category">
              {t.socialCategory}
              <span className="ds-optional">optional · not used to decide</span>
            </label>
            <select id="ss-category" className="select-field" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">Prefer not to say</option>
              <option value="General">General</option>
              <option value="OBC">OBC</option>
              <option value="SC">SC</option>
              <option value="ST">ST</option>
              <option value="EWS">EWS</option>
            </select>
          </div>
          <div className="ds-field">
            <label className="input-label" htmlFor="ss-need">
              {t.medicalNeed}
              <span className="ds-optional">optional · not used to decide</span>
            </label>
            <input id="ss-need" type="text" className="input-field" value={medicalNeed} onChange={(e) => setMedicalNeed(e.target.value)} />
          </div>
        </div>

        {caseId && (
          <label className="consent-wrapper ds-protect">
            <input type="checkbox" className="consent-checkbox" checked={saveToCase} onChange={(e) => setSaveToCase(e.target.checked)} />
            <span>{t.saveToCaseLabel}</span>
          </label>
        )}

        <div className="ds-form-actions">
          <button type="button" className="btn btn-primary" onClick={handleCheck} disabled={api.loading || !canCheck}>
            {api.loading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Checking eligibility…
              </>
            ) : (
              t.checkBtn
            )}
          </button>
          {!canCheck && <span className="ds-hint">Enter your annual income and choose your state.</span>}
        </div>

        {api.error && (
          <StatePanel kind="error" onRetry={handleCheck}>
            Could not check eligibility: {api.error}
          </StatePanel>
        )}
        {profileApi.data && (
          <StatePanel kind="success">
            {profileApi.data.background_eligibility === "queued"
              ? t.savedTriggered
              : profileApi.data.background_eligibility === "not_ready"
                ? t.savedNotReady
                : t.savedNoChange}
          </StatePanel>
        )}
        {profileApi.error && <StatePanel kind="error">Could not save the income profile: {profileApi.error}</StatePanel>}
      </section>

      {/* Real Results */}
      {results && results.length > 0 && (
        <section aria-labelledby="ss-results-title" className="ss-results">
          <h3 id="ss-results-title" className="bn-lines-head">
            {t.eligibleSchemes}
          </h3>
          {results.map((scheme, idx) => {
            const isEligible = scheme.estimated_eligibility === "eligible";
            // "ambiguous" means the engine could not decide — never render it as "Not Eligible".
            const isAmbiguous = scheme.estimated_eligibility === "ambiguous";
            const tone = isEligible ? "is-eligible" : isAmbiguous ? "is-ambiguous" : "is-ineligible";
            const badgeClass = isEligible ? "badge-success" : isAmbiguous ? "badge-warning" : "badge-danger";
            const badgeText = isEligible ? t.provisionallyEligible : isAmbiguous ? t.verificationNeeded : t.notEligible;

            return (
              <article key={idx} className={`case-panel bn-card ss-scheme ${tone}`}>
                <div className="case-panel-head">
                  <h4 className="ss-scheme-name">{scheme.scheme_name}</h4>
                  <span className="bn-badges">
                    <span className={`badge ${badgeClass}`}>{badgeText}</span>
                    <span className="badge badge-demo" title="How the rule behind this result is sourced">
                      {scheme.criteria_provenance === "OFFICIAL_SOURCE_CITED" ? "Official source cited" : "Official restatement cited"}
                    </span>
                  </span>
                </div>
                <p className="bn-summary">{scheme.reason}</p>

                <div className="ss-basis" aria-label="What this result is based on">
                  <div className="ss-basis-col is-decided">
                    <span className="ss-basis-head">{t.criteriaEvaluated}</span>
                    {scheme.criteria_evaluated.length > 0 ? (
                      <ul>{scheme.criteria_evaluated.map((c) => <li key={c}>{humanize(c)}</li>)}</ul>
                    ) : (
                      <p>Nothing — no deciding fact is collected here.</p>
                    )}
                  </div>
                  <div className="ss-basis-col is-recorded">
                    <span className="ss-basis-head">{t.nonDeterminative}</span>
                    {scheme.non_determinative_factors.length > 0 ? (
                      <ul>{scheme.non_determinative_factors.map((c) => <li key={c}>{humanize(c)}</li>)}</ul>
                    ) : (
                      <p>—</p>
                    )}
                  </div>
                  <div className="ss-basis-col is-unchecked">
                    <span className="ss-basis-head">{t.criteriaNotEvaluated}</span>
                    <ul>{scheme.criteria_not_evaluated.map((c) => <li key={c}>{humanize(c)}</li>)}</ul>
                  </div>
                </div>

                {scheme.is_provisional && <p className="bn-notice is-warning">{t.provisionalNotice}</p>}

                {(isEligible || isAmbiguous) && scheme.claim_guide_steps.length > 0 && (
                  <div className="ss-steps">
                    <strong>{isEligible ? t.howToClaim : t.howToVerify}</strong>
                    <ol>
                      {scheme.claim_guide_steps.map((step, sIdx) => (
                        <li key={sIdx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {scheme.sources.length > 0 && (
                  <div className="ss-sources">
                    <strong>{t.officialSources}</strong>
                    <ul>
                      {scheme.sources.map((source) => (
                        <li key={source.url}>
                          <a href={source.url} target="_blank" rel="noopener noreferrer">
                            {source.document}
                          </a>
                          <span>{` — ${source.publisher}${source.date ? ` (${source.date})` : ""}`}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            );
          })}
        </section>
      )}

      {/* Empty Results */}
      {results && results.length === 0 && (
        <StatePanel kind="empty">No government health scheme matches found for the given criteria.</StatePanel>
      )}

      {/* Before the first check: what is checked, from the cited records — not a result. */}
      {!hasChecked && (
        <section className="ss-explainer" aria-labelledby="ss-explainer-title">
          <h3 id="ss-explainer-title" className="bn-lines-head">
            What SchemeSetu checks
          </h3>
          <div className="ss-explainer-grid">
            {SCHEMES_CHECKED.map((s) => (
              <article key={s.name} className="case-panel bn-card">
                <div className="case-panel-head">
                  <h4 className="ss-scheme-name">{s.name}</h4>
                  <span className="badge badge-demo">{s.where}</span>
                </div>
                <p className="bn-fine">{s.basis}</p>
                <p className="ss-decided">{s.decided}</p>
                <p className="bn-fine">Source: {s.source}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
