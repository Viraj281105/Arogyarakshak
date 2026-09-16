"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";

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

export const SchemeSetuView: React.FC<SchemeSetuViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.schemesetu;
  const api = useApi<SchemeResult[]>();
  // Empty by default: pre-filled values were submitted verbatim by users who did not
  // edit them, producing determinations about a fabricated person.
  const [income, setIncome] = useState("");
  const [state, setState] = useState("");
  const [category, setCategory] = useState("General");
  const [medicalNeed, setMedicalNeed] = useState("");
  const [hasChecked, setHasChecked] = useState(false);
  // Opt-in, unchecked by default: income is stored against a case only when the patient asks.
  const [saveToCase, setSaveToCase] = useState(false);
  const profileApi = useApi<IncomeProfileSaveResult>();

  const handleCheck = async () => {
    const incomeVal = parseFloat(income);
    if (isNaN(incomeVal) || !state.trim() || !medicalNeed.trim()) return;
    setHasChecked(true);
    await api.execute("/api/v1/schemesetu/eligibility", {
      body: {
        income: incomeVal,
        location_state: state,
        category,
        medical_need: medicalNeed,
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
  const showExample = !hasChecked;

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Intake Form */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          padding: "1.25rem",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-subtle)",
          marginBottom: "1.5rem",
        }}
      >
        <div className="grid-2" style={{ marginBottom: "1rem" }}>
          <div>
            <label className="input-label">{t.annualIncome}</label>
            <input
              type="number"
              className="input-field"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
            />
          </div>
          <div>
            <label className="input-label">{t.state}</label>
            <select
              className="select-field"
              value={state}
              onChange={(e) => setState(e.target.value)}
            >
              <option value="Maharashtra">Maharashtra</option>
              <option value="Delhi">Delhi</option>
              <option value="Karnataka">Karnataka</option>
              <option value="Uttar Pradesh">Uttar Pradesh</option>
              <option value="Gujarat">Gujarat</option>
              <option value="Tamil Nadu">Tamil Nadu</option>
              <option value="Rajasthan">Rajasthan</option>
              <option value="West Bengal">West Bengal</option>
              <option value="Kerala">Kerala</option>
            </select>
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: "1.25rem" }}>
          <div>
            <label className="input-label">{t.socialCategory}</label>
            <select
              className="select-field"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="General">General</option>
              <option value="OBC">OBC</option>
              <option value="SC">SC</option>
              <option value="ST">ST</option>
              <option value="EWS">EWS</option>
            </select>
          </div>
          <div>
            <label className="input-label">{t.medicalNeed}</label>
            <input
              type="text"
              className="input-field"
              value={medicalNeed}
              onChange={(e) => setMedicalNeed(e.target.value)}
            />
          </div>
        </div>

        {caseId && (
          <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", fontSize: "0.85rem", marginBottom: "1rem" }}>
            <input type="checkbox" checked={saveToCase} onChange={(e) => setSaveToCase(e.target.checked)} />
            <span>{t.saveToCaseLabel}</span>
          </label>
        )}

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: "100%" }}
          onClick={handleCheck}
          disabled={api.loading || !income.trim() || !state.trim() || !medicalNeed.trim()}
        >
          {api.loading ? "Checking eligibility..." : `🔍 ${t.checkBtn}`}
        </button>
      </div>

      {profileApi.data && (
        <div
          role="status"
          style={{
            padding: "0.75rem 1rem",
            marginBottom: "1rem",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            fontSize: "0.85rem",
          }}
        >
          {profileApi.data.background_eligibility === "queued"
            ? t.savedTriggered
            : profileApi.data.background_eligibility === "not_ready"
            ? t.savedNotReady
            : t.savedNoChange}
        </div>
      )}
      {profileApi.error && (
        <div role="alert" style={{ color: "#fca5a5", fontSize: "0.85rem", marginBottom: "1rem" }}>
          ⚠️ {typeof profileApi.error === "string" ? profileApi.error : "Could not save the income profile."}
        </div>
      )}

      {/* Error State */}
      {api.error && (
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
          ⚠️ {api.error}
        </div>
      )}

      {/* Real Results */}
      {results && results.length > 0 && (
        <div>
          <h3 style={{ marginBottom: "1rem" }}>{t.eligibleSchemes}</h3>
          <div className="grid-2">
            {results.map((scheme, idx) => {
              const isEligible = scheme.estimated_eligibility === "eligible";
              // "ambiguous" means the engine could not decide — never render it as "Not Eligible".
              const isAmbiguous = scheme.estimated_eligibility === "ambiguous";
              const borderColor = isEligible
                ? "rgba(16, 185, 129, 0.3)"
                : isAmbiguous
                ? "rgba(245, 158, 11, 0.3)"
                : "rgba(239, 68, 68, 0.2)";
              const badgeClass = isEligible ? "badge-success" : isAmbiguous ? "badge-warning" : "badge-danger";
              const badgeText = isEligible
                ? t.provisionallyEligible
                : isAmbiguous
                ? t.verificationNeeded
                : t.notEligible;

              return (
                <div
                  key={idx}
                  style={{
                    background: "var(--bg-base)",
                    padding: "1.25rem",
                    borderRadius: "var(--radius-md)",
                    border: `1px solid ${borderColor}`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                    <strong style={{ color: isEligible ? "var(--brand-emerald)" : "var(--text-secondary)", fontSize: "1.05rem" }}>
                      {scheme.scheme_name}
                    </strong>
                    <span className={`badge ${badgeClass}`}>{badgeText}</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem", color: "var(--text-secondary)" }}>
                    {scheme.reason}
                  </p>

                  {(isEligible || isAmbiguous) && scheme.claim_guide_steps.length > 0 && (
                    <div style={{ fontSize: "0.8rem", marginTop: "0.5rem" }}>
                      <strong style={{ color: "var(--text-primary)" }}>{isEligible ? t.howToClaim : t.howToVerify}</strong>
                      <ol style={{ paddingLeft: "1.25rem", marginTop: "0.25rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                        {scheme.claim_guide_steps.map((step, sIdx) => (
                          <li key={sIdx}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}

                  {scheme.is_provisional && (
                    <div
                      style={{
                        marginTop: "0.75rem",
                        paddingTop: "0.75rem",
                        borderTop: "1px solid var(--border-subtle)",
                        fontSize: "0.75rem",
                        color: "var(--status-warning)",
                      }}
                    >
                      ⓘ {t.provisionalNotice}
                      {scheme.criteria_not_evaluated.length > 0 && (
                        <div style={{ marginTop: "0.35rem", color: "var(--text-secondary)" }}>
                          <strong>{t.criteriaNotEvaluated}:</strong> {scheme.criteria_not_evaluated.join(", ")}
                        </div>
                      )}
                      {scheme.criteria_evaluated.length > 0 && (
                        <div style={{ marginTop: "0.25rem", color: "var(--text-secondary)" }}>
                          <strong>{t.criteriaEvaluated}:</strong> {scheme.criteria_evaluated.join(", ")}
                        </div>
                      )}
                      {scheme.non_determinative_factors.length > 0 && (
                        <div style={{ marginTop: "0.25rem", color: "var(--text-secondary)" }}>
                          <strong>{t.nonDeterminative}:</strong> {scheme.non_determinative_factors.join(", ")}
                        </div>
                      )}
                    </div>
                  )}

                  {scheme.sources.length > 0 && (
                    <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      <strong>{t.officialSources}:</strong>
                      <ul style={{ paddingLeft: "1.25rem", marginTop: "0.25rem", lineHeight: 1.5 }}>
                        {scheme.sources.map((source) => (
                          <li key={source.url}>
                            <a href={source.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--brand-cyan)" }}>
                              {source.document}
                            </a>
                            {` — ${source.publisher}${source.date ? ` (${source.date})` : ""}`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty Results */}
      {results && results.length === 0 && (
        <div
          style={{
            padding: "1rem",
            textAlign: "center",
            color: "var(--text-secondary)",
            fontSize: "0.9rem",
          }}
        >
          No government health scheme matches found for the given criteria.
        </div>
      )}

      {/* Example (before first check) */}
      {showExample && (
        <>
          <div
            style={{
              padding: "0.5rem 0.75rem",
              marginBottom: "1rem",
              background: "rgba(245, 158, 11, 0.08)",
              borderRadius: "var(--radius-sm, 4px)",
              fontSize: "0.8rem",
              color: "var(--status-warning)",
              fontWeight: 600,
            }}
          >
            ⓘ Example — Fill in your details and check eligibility for a live assessment
          </div>

          <h3 style={{ marginBottom: "1rem" }}>{t.eligibleSchemes}</h3>
          <div className="grid-2" style={{ opacity: 0.7 }}>
            <div
              style={{
                background: "var(--bg-base)",
                padding: "1.25rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid rgba(6, 182, 212, 0.3)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <strong style={{ color: "var(--brand-cyan)", fontSize: "1.05rem" }}>Ayushman Bharat PM-JAY</strong>
                <span className="badge badge-warning">{t.verificationNeeded}</span>
              </div>
              <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
                National flagship cashless secondary and tertiary hospitalization cover.
              </p>
              <div style={{ fontSize: "0.85rem" }}>
                <span style={{ color: "var(--text-secondary)" }}>{t.maxCoverage}:</span>{" "}
                <strong>₹5,00,000 / family / year</strong>
              </div>
            </div>

            <div
              style={{
                background: "var(--bg-base)",
                padding: "1.25rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <strong style={{ color: "var(--brand-emerald)", fontSize: "1.05rem" }}>{t.mjpjayCard}</strong>
                <span className="badge badge-success">State Scheme</span>
              </div>
              <p style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
                Universal coverage for Maharashtra residents covering 1,356 medical/surgical procedures.
              </p>
              <div style={{ fontSize: "0.85rem" }}>
                <span style={{ color: "var(--text-secondary)" }}>{t.maxCoverage}:</span>{" "}
                <strong>₹5,00,000 / family / year</strong>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
