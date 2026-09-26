"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders } from "../../hooks/useApi";
import { ClinicalStatement } from "../../lib/clinical";
import { ClinicalStatementCard, ProvenanceBadge } from "../clinical/Attribution";
import { ClinicalReviewPanel } from "../clinical/ClinicalReviewPanel";

// ADR-011: whether the denial turns on clinical judgment. Never an outcome prediction.
interface ClinicalReviewTrigger {
  requires_clinical_interpretation: boolean;
  reasons: string[];
  suggested_clinical_question: string | null;
  note: string;
}

interface ClinicalStatementsResponse {
  human_clinical_statement_attached: boolean;
  statements: ClinicalStatement[];
  annex_text: string;
}

// --- API Response Types (matching backend Pydantic schemas) ---
interface RegulatoryViolation {
  statute_or_circular: string;
  clause_reference: string;
  violation_summary: string;
  legal_remedy: string;
}

interface DisputeAuditResult {
  is_wrongful_denial: boolean;
  reversal_probability_score: number;
  /** "HEURISTIC_PRIOR_NOT_HISTORICAL": a rule prior, not a probability from past outcomes. */
  probability_basis?: string;
  primary_dispute_grounds: string;
  regulatory_violations: RegulatoryViolation[];
  level_1_gro_appeal: string;
  level_2_bimabharosa_text: string;
  level_3_ombudsman_grounds: string;
  clinical_review?: ClinicalReviewTrigger | null;
}

interface GrievanceTimelineEvent {
  tier: string;
  title: string;
  deadline_date: string;
  status: string;
  instructions: string;
}

interface GrievanceTrackerResponse {
  claim_number: string | null;
  insurer_name: string;
  date_initiated: string;
  current_tier: string;
  timeline_events: GrievanceTimelineEvent[];
}

interface BimaNyayViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

export const BimaNyayView: React.FC<BimaNyayViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.bimanyay;
  const analyzeApi = useApi<DisputeAuditResult>();
  const timelineApi = useApi<GrievanceTrackerResponse>();
  const statementsApi = useApi<ClinicalStatementsResponse>();

  // SEC-04: when a case is active, the dispute record is linked to it (and becomes
  // evidence a clinical reviewer can see, labelled PATIENT_PROVIDED).
  const caseQuery = caseId ? `&case_id=${encodeURIComponent(caseId)}` : "";

  const loadClinicalStatements = async () => {
    if (!caseId) return;
    await statementsApi.execute(`/api/v1/bimanyay/cases/${encodeURIComponent(caseId)}/clinical-statements`, {
      method: "GET",
      headers: caseAuthHeaders(caseToken),
    });
  };

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

  // UI State
  const [activeTab, setActiveTab] = useState<"gro" | "bimabharosa" | "ombudsman">("gro");
  const [copied, setCopied] = useState(false);

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

  const handleCopy = () => {
    const result = analyzeApi.data;
    if (!result) return;

    let textToCopy = result.level_1_gro_appeal;
    if (activeTab === "bimabharosa") textToCopy = result.level_2_bimabharosa_text;
    if (activeTab === "ombudsman") textToCopy = result.level_3_ombudsman_grounds;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const result = analyzeApi.data;
  const timeline = timelineApi.data;
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
          {/* ADR-011: clinical-interpretation trigger (machine-derived) */}
          {result.clinical_review?.requires_clinical_interpretation && (
            <div
              style={{
                padding: "1rem 1.25rem",
                marginBottom: "1.25rem",
                border: "1px solid var(--status-warning)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                <strong>🩺 Clinical review required</strong>
                <ProvenanceBadge provenance="AI_DERIVED" />
              </div>
              <ul style={{ fontSize: "0.85rem", paddingLeft: "1.1rem", margin: "0.5rem 0" }}>
                {result.clinical_review.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
              <p style={{ fontSize: "0.8rem" }}>{result.clinical_review.note}</p>
              {!caseId && (
                <p style={{ fontSize: "0.8rem" }}>
                  Upload your records above to create a case, then request a statement from a named doctor here.
                </p>
              )}
            </div>
          )}
          {caseId && (
            <ClinicalReviewPanel
              caseId={caseId}
              caseToken={caseToken}
              sourceModule="bimanyay"
              trigger={result.clinical_review?.requires_clinical_interpretation ? "DENIAL_CATEGORY" : "MANUAL"}
              recommendationReason={result.clinical_review?.reasons.join(" ") || null}
              suggestedQuestion={result.clinical_review?.suggested_clinical_question}
              insurerName={insurerName}
            />
          )}
          {caseId && (
            <div style={{ marginBottom: "1.5rem" }}>
              <button type="button" className="btn btn-secondary" onClick={loadClinicalStatements}>
                Attach finalized clinician statements to these appeals
              </button>
              {statementsApi.data &&
                (statementsApi.data.human_clinical_statement_attached ? (
                  <div style={{ marginTop: "0.75rem" }}>
                    {statementsApi.data.statements.map((s) => (
                      <ClinicalStatementCard key={s.statement_id} statement={s} />
                    ))}
                    <button
                      type="button"
                      className="btn"
                      style={{ border: "1px solid var(--border-subtle)" }}
                      onClick={() => navigator.clipboard.writeText(statementsApi.data!.annex_text)}
                    >
                      📋 Copy attributed annex (verbatim)
                    </button>
                  </div>
                ) : (
                  <p style={{ fontSize: "0.85rem", marginTop: "0.5rem", color: "var(--status-warning)" }}>
                    No finalized statement from a named clinician exists for this case. Do not describe any appeal
                    reasoning as a doctor&apos;s opinion.
                  </p>
                ))}
            </div>
          )}
          {/* Summary Stats */}
          <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-box" style={{ borderLeft: `4px solid ${result.is_wrongful_denial ? "var(--status-success)" : "var(--status-danger)"}` }}>
              <div className="stat-label">{t.reversalScore}</div>
              <div className="stat-val" style={{ color: result.is_wrongful_denial ? "var(--brand-emerald)" : "var(--status-danger)" }}>
                {(result.reversal_probability_score * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: "0.75rem", opacity: 0.8, marginTop: "0.35rem" }}>{t.heuristicDisclosure}</div>
              {result.is_wrongful_denial && (
                <span className="badge badge-success" style={{ marginTop: "0.5rem" }}>
                  ✓ {t.wrongfulBadge}
                </span>
              )}
            </div>

            <div className="stat-box" style={{ borderLeft: "4px solid var(--brand-cyan)" }}>
              <div className="stat-label">{t.violationsTitle}</div>
              {result.regulatory_violations.length > 0 ? (
                <ul style={{ listStyle: "none", marginTop: "0.5rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                  {result.regulatory_violations.map((v, idx) => (
                    <li key={idx}>
                      <strong style={{ color: "var(--brand-cyan)" }}>{v.statute_or_circular}:</strong>{" "}
                      {v.clause_reference} — {v.violation_summary}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: "0.85rem", marginTop: "0.5rem", color: "var(--text-secondary)" }}>
                  {result.primary_dispute_grounds}
                </p>
              )}
            </div>
          </div>

          {/* Appeals Tab Selector */}
          <div style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.5rem", marginBottom: "1rem", overflowX: "auto" }}>
            <button
              type="button"
              className={`btn ${activeTab === "gro" ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
              onClick={() => setActiveTab("gro")}
            >
              {t.groTab}
            </button>
            <button
              type="button"
              className={`btn ${activeTab === "bimabharosa" ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
              onClick={() => setActiveTab("bimabharosa")}
            >
              {t.bimaBharosaTab}
            </button>
            <button
              type="button"
              className={`btn ${activeTab === "ombudsman" ? "btn-primary" : "btn-secondary"}`}
              style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
              onClick={() => setActiveTab("ombudsman")}
            >
              {t.ombudsmanTab}
            </button>
          </div>

          {/* Appeal Content */}
          <div style={{ position: "relative", marginBottom: "1.5rem" }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ position: "absolute", top: "0.75rem", right: "0.75rem", fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
              onClick={handleCopy}
            >
              {copied ? `✓ ${t.copied}` : `📋 ${t.copyDraft}`}
            </button>

            <pre
              style={{
                background: "var(--bg-base)",
                padding: "1rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                fontSize: "0.85rem",
                fontFamily: "monospace",
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
                lineHeight: 1.6,
                maxHeight: "340px",
                overflowY: "auto",
              }}
            >
              {activeTab === "gro" && result.level_1_gro_appeal}
              {activeTab === "bimabharosa" && result.level_2_bimabharosa_text}
              {activeTab === "ombudsman" && result.level_3_ombudsman_grounds}
            </pre>
          </div>

          {/* Real Statutory SLA Tracker */}
          <div>
            <h3>⏳ {t.timelineTitle}</h3>
            {timeline && timeline.timeline_events.length > 0 ? (
              <div className="timeline-list">
                {timeline.timeline_events.map((event, idx) => {
                  const isActive = event.status === "ACTIVE";
                  const isOverdue = event.status === "OVERDUE";
                  const badgeClass = isActive ? "badge-info" : isOverdue ? "badge-danger" : "";
                  const badgeBg = !isActive && !isOverdue ? { background: "rgba(255,255,255,0.08)", color: "var(--text-muted)" } : {};

                  return (
                    <div className="timeline-item" key={idx}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong style={{ color: isActive ? "var(--text-primary)" : "var(--text-secondary)" }}>
                            {event.title}
                          </strong>
                          <span className={`badge ${badgeClass}`} style={badgeBg}>
                            {event.status}
                          </span>
                        </div>
                        <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                          {event.instructions} <strong>Deadline: {event.deadline_date}</strong>
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : timelineApi.loading ? (
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", padding: "1rem 0" }}>
                Calculating statutory SLA milestones...
              </p>
            ) : (
              <div className="timeline-list">
                <div className="timeline-item">
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: "var(--text-primary)" }}>{t.tier1Label}</strong>
                      <span className="badge badge-info">{t.activeBadge}</span>
                    </div>
                    <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                      {t.tier1Desc.replace("{insurer}", insurerName || t.insurerName)}
                    </p>
                  </div>
                </div>
                <div className="timeline-item">
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: "var(--text-secondary)" }}>{t.tier2Label}</strong>
                      <span className="badge" style={{ background: "rgba(255,255,255,0.08)", color: "var(--text-muted)" }}>{t.pendingBadge}</span>
                    </div>
                    <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                      {t.tier2Desc}
                    </p>
                  </div>
                </div>
                <div className="timeline-item">
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: "var(--text-secondary)" }}>{t.tier3Label}</strong>
                      <span className="badge" style={{ background: "rgba(255,255,255,0.08)", color: "var(--text-muted)" }}>{t.pendingBadge}</span>
                    </div>
                    <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                      {t.tier3Desc}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
