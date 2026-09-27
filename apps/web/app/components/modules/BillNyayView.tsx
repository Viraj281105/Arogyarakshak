"use client";

import React, { useState } from "react";
import { Language, translations } from "../../translations";
import { useApi, caseAuthHeaders, API_BASE } from "../../hooks/useApi";
import { ClinicalStatement, EvidenceItem, SafetyEscalation, clinicalPaths } from "../../lib/clinical";
import { ClinicalStatementCard, ProvenanceBadge } from "../clinical/Attribution";
import { ClinicalReviewPanel } from "../clinical/ClinicalReviewPanel";
import { StatePanel } from "../clinical/StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";

// --- Clinical plausibility (ADR-011): bounded, never a necessity determination ---
interface PlausibilityResponse {
  case_id: string;
  assessment: {
    status: "PLAUSIBLE" | "INSUFFICIENT_INFORMATION" | "POTENTIAL_INCONSISTENCY" | "CLINICAL_REVIEW_RECOMMENDED";
    summary: string;
    disclaimer: string;
    clinical_review_required: boolean;
    review_reasons: string[];
    evidence_used: EvidenceItem[];
    not_assessed_items: string[];
    conflicting_items?: string[];
    excluded_administrative_items: string[];
    coverage: "FULL" | "PARTIAL" | "NONE";
    references: { name: string; type: string; version: string; icd10_code: string; diagnosis_label: string }[];
    guideline_citations: unknown[];
    guideline_note: string;
    method: string;
    safety_check_status?: "EVALUATED" | "UNAVAILABLE";
  };
  safety_escalations: SafetyEscalation[];
  safety_check?: { status: "EVALUATED" | "UNAVAILABLE"; note: string | null };
  clinical_review: { required: boolean; status: string; human_statement_exists: boolean };
}

// --- API Response Types (matching backend AuditResponse schema) ---
type AuditItemStatus =
  | "overcharged"
  | "within_benchmark"
  | "bundled"
  | "not_benchmarked";

interface AuditResultItem {
  item_name: string;
  charged: number;
  // null when the item has no CGHS counterpart — it must never render as "Fair".
  cghs_benchmark: number | null;
  deviation_percentage: number;
  is_deviation: boolean;
  benchmarked: boolean;
  status: AuditItemStatus;
  /** What the reference covers for this line, e.g. "₹4,500 per day × 3 days". */
  benchmark_basis?: string | null;
  /** Why a matched line was not compared (e.g. a per-day rate and no day count). */
  not_benchmarked_reason?: string | null;
}

interface AuditResponse {
  case_id: string;
  total_charged: number;
  total_benchmark: number;
  benchmarked_charged: number;
  potential_savings: number;
  deviations_count: number;
  benchmarked_count: number;
  unmatched_count: number;
  unmatched_amount: number;
  audit_items: AuditResultItem[];
}

// --- Appeal Response Types (matching backend AppealResponse schema, #18/#66) ---
interface AppealResponse {
  case_id: string;
  appeal_letter: string;
  scorecard: { overall_score: number; status: string; confidence_estimate: number };
  status: string;
  denial_facts_extracted: boolean;
  llm_backed: boolean;
  consensus: { final_verdict: string; weighted_score: number; is_unanimous: boolean };
  revision_count: number;
  document_sha256: string;
  pdf_download_url: string;
  language: string;
  // ADR-011: attributed human statements, appended verbatim — never LLM-written.
  human_clinical_statement_attached: boolean;
  clinical_statements: ClinicalStatement[];
  clinical_annex: string;
  clinical_statement_notice: string;
}

interface BillNyayViewProps {
  currentLang: Language;
  caseId?: string;
  caseToken?: string;
}

export const BillNyayView: React.FC<BillNyayViewProps> = ({ currentLang, caseId, caseToken }) => {
  const t = translations[currentLang].modules.billnyay;
  const api = useApi<AuditResponse>();
  const appealApi = useApi<AppealResponse>();
  const plausibilityApi = useApi<PlausibilityResponse>();
  const [hasRun, setHasRun] = useState(false);

  const handleCheckPlausibility = async () => {
    if (!caseId) return;
    await plausibilityApi.execute(clinicalPaths.plausibility(caseId), {
      method: "GET",
      headers: caseAuthHeaders(caseToken),
    });
  };
  const [appealDownloadError, setAppealDownloadError] = useState<string | null>(null);

  const handleRunAudit = async () => {
    if (!caseId) return;
    setHasRun(true);
    await api.execute(`/api/v1/billnyay/cases/${caseId}/audit`, {
      headers: caseAuthHeaders(caseToken),
    });
  };

  // Runs the 5-agent appeal pipeline (#18) — does not require a prior audit call,
  // since it reads the case's document text directly.
  const handleDraftAppeal = async () => {
    if (!caseId) return;
    await appealApi.execute(`/api/v1/billnyay/cases/${caseId}/appeal?language=${currentLang}`, {
      headers: caseAuthHeaders(caseToken),
    });
  };

  // Downloads the exact signed PDF the appeal drafted (#66) — served from stored
  // bytes, never regenerated, so it always matches what was hashed and signed.
  const handleDownloadAppealPdf = async () => {
    if (!caseId) return;
    setAppealDownloadError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/billnyay/cases/${caseId}/appeal/pdf`, {
        headers: caseAuthHeaders(caseToken),
      });
      if (!res.ok) {
        setAppealDownloadError(`Could not download the appeal PDF (HTTP ${res.status}).`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `appeal_${caseId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      setAppealDownloadError("Could not download the appeal PDF. Is the backend reachable?");
    }
  };

  const auditData = api.data;
  const appealData = appealApi.data;
  const showExample = !hasRun && !caseId;

  // Example data shown only when no case is active, clearly labeled
  const exampleItems = [
    { item: "ICU Day Charges (Deluxe Wing)", charged: 18500, cghs: 6500, overcharge: 12000, status: "Overcharged (184%)" },
    { item: "Disposable PPE Kit (per shift)", charged: 2400, cghs: 650, overcharge: 1750, status: "Exceeds Ceiling" },
    { item: "Syringe Infusion Pump Hire", charged: 1200, cghs: 350, overcharge: 850, status: "Bundled in ICU Tariff" },
    { item: "Paracetamol IV Infusion 100ml", charged: 450, cghs: 42, overcharge: 408, status: "Violates NPPA Ceiling" },
  ];

  return (
    <div className="card">
      <div style={{ marginBottom: "1.5rem" }}>
        <h2>{t.title}</h2>
        <p>{t.desc}</p>
      </div>

      {/* Action Buttons */}
      {caseId && (
        <div style={{ marginBottom: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-primary"
            style={{ flex: 1, minWidth: "220px" }}
            onClick={handleRunAudit}
            disabled={api.loading}
          >
            {api.loading ? (
              <>
                <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
                Auditing bill against CGHS benchmarks...
              </>
            ) : (
              <>⚖️ Run CGHS Benchmark Audit</>
            )}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ flex: 1, minWidth: "220px" }}
            onClick={handleDraftAppeal}
            disabled={appealApi.loading}
          >
            {appealApi.loading ? (
              <>
                <span className="step-indicator active" style={{ display: "inline-block", marginRight: "0.25rem" }} />
                Running 5-agent appeal pipeline...
              </>
            ) : (
              <>📝 Draft IRDAI Appeal Letter</>
            )}
          </button>
          <button
            type="button"
            className="btn"
            style={{ flex: 1, minWidth: "220px", border: "1px solid var(--border-medium)" }}
            onClick={handleCheckPlausibility}
            disabled={plausibilityApi.loading}
          >
            {plausibilityApi.loading ? "Checking plausibility…" : "🩺 Check clinical plausibility"}
          </button>
        </div>
      )}

      {/* Clinical plausibility (ADR-011) — machine-derived, bounded, not a necessity verdict */}
      {plausibilityApi.loading && <StatePanel kind="loading">Comparing the documented diagnosis and interventions…</StatePanel>}
      {plausibilityApi.error && (
        <StatePanel kind="error" onRetry={handleCheckPlausibility}>
          Could not run the plausibility check: {plausibilityApi.error}
        </StatePanel>
      )}
      {plausibilityApi.data && (
        <div
          style={{
            padding: "1rem 1.25rem",
            marginBottom: "1.5rem",
            border: "1px solid var(--border-medium)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap", marginBottom: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>Clinical plausibility check</h3>
            <ProvenanceBadge provenance="AI_DERIVED" />
            <span
              className={
                plausibilityApi.data.assessment.status === "PLAUSIBLE"
                  ? TONE_CLASS.success
                  : plausibilityApi.data.assessment.status === "POTENTIAL_INCONSISTENCY"
                  ? TONE_CLASS.danger
                  : TONE_CLASS.warning
              }
            >
              {humanizeEnum(plausibilityApi.data.assessment.status)}
            </span>
            {plausibilityApi.data.clinical_review.required && plausibilityApi.data.assessment.status !== "CLINICAL_REVIEW_RECOMMENDED" && (
              <span className={TONE_CLASS.warning}>Clinical review recommended</span>
            )}
            <span className={TONE_CLASS.neutral} title="How much of the bill the curated reference could assess">
              {humanizeEnum(plausibilityApi.data.assessment.coverage)}
            </span>
          </div>
          {plausibilityApi.data.safety_check?.status === "UNAVAILABLE" && (
            <StatePanel kind="warning">
              <strong>Safety check unavailable.</strong> The clinical safety rules could not be evaluated for this case, so no
              safety assessment was made — this is not the same as &quot;no escalation&quot;.
            </StatePanel>
          )}
          <p style={{ fontSize: "0.9rem" }}>{plausibilityApi.data.assessment.summary}</p>
          <p style={{ fontSize: "0.8rem" }}>
            Evidence used:{" "}
            {plausibilityApi.data.assessment.evidence_used.map((e) => `${humanizeEnum(e.kind)}: ${e.value}`).join("; ") || "none"}
          </p>
          {plausibilityApi.data.assessment.references.map((r) => (
            <p key={r.icd10_code} style={{ fontSize: "0.75rem", opacity: 0.85 }}>
              Reference: {r.name} (project-curated table, {r.version} — not a published clinical guideline) — {r.icd10_code}{" "}
              {r.diagnosis_label}
            </p>
          ))}
          {(plausibilityApi.data.assessment.conflicting_items ?? []).length > 0 && (
            <p style={{ fontSize: "0.8rem", color: "var(--status-danger)" }}>
              Expected for a diagnosis that is not documented: {(plausibilityApi.data.assessment.conflicting_items ?? []).join(", ")}
            </p>
          )}
          {plausibilityApi.data.assessment.not_assessed_items.length > 0 && (
            <p style={{ fontSize: "0.8rem", color: "var(--status-warning)" }}>
              Not assessed (outside the reference): {plausibilityApi.data.assessment.not_assessed_items.join(", ")}
            </p>
          )}
          {plausibilityApi.data.assessment.excluded_administrative_items.length > 0 && (
            <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>
              Set aside as administrative charges, not interventions:{" "}
              {plausibilityApi.data.assessment.excluded_administrative_items.join(", ")}
            </p>
          )}
          <p style={{ fontSize: "0.75rem", opacity: 0.85 }}>{plausibilityApi.data.assessment.guideline_note}</p>
          <p style={{ fontSize: "0.75rem", fontWeight: 600 }}>{plausibilityApi.data.assessment.disclaimer}</p>
        </div>
      )}
      {caseId && (
        <ClinicalReviewPanel
          caseId={caseId}
          caseToken={caseToken}
          sourceModule="billnyay"
          trigger={plausibilityApi.data?.clinical_review.required ? "PLAUSIBILITY_FLAG" : "MANUAL"}
          recommendationReason={plausibilityApi.data?.assessment.review_reasons.join(" ") || null}
        />
      )}

      {/* No Case Active Prompt */}
      {!caseId && !hasRun && (
        <div
          style={{
            padding: "1.25rem",
            marginBottom: "1.5rem",
            background: "rgba(6, 182, 212, 0.06)",
            border: "1px solid rgba(6, 182, 212, 0.2)",
            borderRadius: "var(--radius-md)",
            textAlign: "center",
            color: "var(--text-secondary)",
            fontSize: "0.9rem",
          }}
        >
          📤 Upload a hospital bill above to run a live CGHS benchmark audit.
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

      {appealApi.loading && <StatePanel kind="loading">Drafting the appeal letter and signing the PDF…</StatePanel>}
      {appealApi.error && (
        <StatePanel kind="error" onRetry={handleDraftAppeal}>
          Could not draft the appeal: {appealApi.error}
        </StatePanel>
      )}

      {/* Appeal Letter (5-agent pipeline, #18/#66) */}
      {appealData && (
        <div
          style={{
            background: "var(--bg-base)",
            padding: "1.25rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            marginBottom: "1.5rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <h3>📝 Appeal Letter Drafted</h3>
            <span style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
              <ProvenanceBadge provenance="AI_DERIVED" />
              {/* "Judge" is an automated scoring agent — never shown as a human or legal approval. */}
              <span className={appealData.status === "approve" ? TONE_CLASS.neutral : TONE_CLASS.warning}>
                {appealData.status === "approve" ? "Passed automated quality check" : "Automated check suggests revision"}
              </span>
            </span>
          </div>
          <p style={{ fontSize: "0.8rem", opacity: 0.85, marginTop: "-0.5rem" }}>
            This letter is drafted by software. It is not legal advice and not a clinician&apos;s opinion; review it before sending.
          </p>

          {!appealData.llm_backed && (
            <div
              style={{
                padding: "0.75rem 1rem",
                marginBottom: "1rem",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.25)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--status-warning)",
              }}
            >
              ⓘ Offline template: no AI backend is configured, so this is a static statutory draft, not a
              case-specific analysis. Review carefully before sending.
            </div>
          )}
          {!appealData.denial_facts_extracted && (
            <div
              style={{
                padding: "0.75rem 1rem",
                marginBottom: "1rem",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.25)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--status-warning)",
              }}
            >
              ⓘ Denial details could not be extracted from your document. Fill in the denial code, insurer
              reason, and policy clause yourself before sending.
            </div>
          )}

          <pre
            style={{
              whiteSpace: "pre-wrap",
              fontFamily: "inherit",
              fontSize: "0.875rem",
              lineHeight: 1.6,
              color: "var(--text-primary)",
              marginBottom: "1.25rem",
            }}
          >
            {appealData.appeal_letter}
          </pre>

          {/* ADR-011: the human clinical annex is appended verbatim; when absent, say so. */}
          <div style={{ marginBottom: "1.25rem" }}>
            <h4 style={{ marginBottom: "0.5rem" }}>Attributed clinical statement</h4>
            {appealData.human_clinical_statement_attached ? (
              appealData.clinical_statements.map((s) => <ClinicalStatementCard key={s.statement_id} statement={s} />)
            ) : (
              <p style={{ fontSize: "0.85rem", color: "var(--status-warning)" }}>
                No statement from a named clinician is attached. Any clinical reasoning in the letter above is general,
                software-drafted reasoning — not a doctor&apos;s opinion. Use &ldquo;Request Clinical Review&rdquo; to get one.
                (This note is for you only; it is not printed in the PDF.)
              </p>
            )}
            <p style={{ fontSize: "0.75rem", opacity: 0.8 }}>
              The downloadable PDF is re-generated whenever a clinician finalizes, withdraws or you cancel a statement, so
              always download it again right before sending. An older copy will fail integrity verification.
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigator.clipboard.writeText(`${appealData.appeal_letter}\n\n${appealData.clinical_annex}`)}
            >
              📋 Copy Appeal Letter
            </button>
            <button type="button" className="btn btn-primary" onClick={handleDownloadAppealPdf}>
              📥 Download Signed Appeal PDF
            </button>
          </div>
          {appealDownloadError && (
            <p style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "0.5rem" }}>⚠️ {appealDownloadError}</p>
          )}
        </div>
      )}

      {/* Real Audit Results */}
      {auditData && (
        <>
          <div className="grid-3" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-box">
              <div className="stat-label">{t.chargedTotal}</div>
              <div className="stat-val" style={{ color: "var(--text-primary)" }}>
                ₹{auditData.total_charged.toLocaleString("en-IN")}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.cghsBenchmark}</div>
              <div className="stat-val" style={{ color: "var(--brand-cyan)" }}>
                ₹{auditData.total_benchmark.toLocaleString("en-IN")}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.potentialSavings}</div>
              <div className="stat-val" style={{ color: "var(--status-danger)" }}>
                ₹{auditData.potential_savings.toLocaleString("en-IN")}
              </div>
            </div>
          </div>

          {/* Coverage disclosure: the patient must be able to see how much of the
              bill was actually compared against a benchmark. */}
          {auditData.unmatched_count > 0 && (
            <div
              style={{
                padding: "0.75rem 1rem",
                marginBottom: "1.5rem",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.25)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--status-warning)",
              }}
            >
              ⓘ {t.unmatchedNotice
                .replace("{count}", String(auditData.unmatched_count))
                .replace("{amount}", `₹${auditData.unmatched_amount.toLocaleString("en-IN")}`)}
            </div>
          )}

          {auditData.audit_items.length > 0 ? (
            <>
              <div style={{ marginBottom: "1rem" }}>
                <h3>{t.overchargesTitle} ({auditData.deviations_count} flagged)</h3>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>{t.itemCol}</th>
                      <th>{t.chargedCol}</th>
                      <th>{t.cghsCol}</th>
                      <th>{t.varianceCol}</th>
                      <th>{t.statusCol}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditData.audit_items.map((row, idx) => {
                      const benchmarked = row.benchmarked && row.cghs_benchmark !== null;
                      return (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{row.item_name}</td>
                          <td>₹{row.charged.toLocaleString("en-IN")}</td>
                          <td style={{ color: benchmarked ? "var(--brand-cyan)" : "var(--text-secondary)" }}>
                            {benchmarked
                              ? `₹${(row.cghs_benchmark as number).toLocaleString("en-IN")}`
                              : "—"}
                            {row.benchmark_basis && (
                              <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", fontWeight: 400 }}>
                                {row.benchmark_basis}
                              </div>
                            )}
                          </td>
                          <td
                            style={{
                              color: !benchmarked
                                ? "var(--text-secondary)"
                                : row.is_deviation
                                ? "var(--status-danger)"
                                : "var(--status-success)",
                              fontWeight: 700,
                            }}
                          >
                            {!benchmarked
                              ? row.not_benchmarked_reason ?? t.notBenchmarked
                              : row.is_deviation
                              ? `+₹${(row.charged - (row.cghs_benchmark as number)).toLocaleString("en-IN")} (${row.deviation_percentage}%)`
                              : t.withinBenchmark}
                          </td>
                          <td>
                            <span
                              className={`badge ${
                                !benchmarked
                                  ? "badge-warning"
                                  : row.is_deviation
                                  ? "badge-danger"
                                  : "badge-success"
                              }`}
                            >
                              {!benchmarked
                                ? `ⓘ ${t.notBenchmarkedBadge}`
                                : row.status === "bundled"
                                ? `⚠️ ${t.bundledBadge}`
                                : row.is_deviation
                                ? `⚠️ ${t.overchargedBadge} (${row.deviation_percentage}%)`
                                : `✓ ${t.fairBadge}`}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div
              style={{
                padding: "1rem",
                textAlign: "center",
                color: "var(--text-secondary)",
                fontSize: "0.9rem",
              }}
            >
              No billing line items were found in the uploaded document for audit comparison.
            </div>
          )}

          {auditData.deviations_count > 0 && (
            <div
              style={{
                marginTop: "1.5rem",
                padding: "1rem",
                backgroundColor: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.2)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.85rem",
                color: "var(--status-warning)",
              }}
            >
              <strong>⚖️ {t.disputeGrounds}</strong>
            </div>
          )}
        </>
      )}

      {/* Example Data (only when no case active) */}
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
            ⓘ Example — Upload a real document to see live audit results
          </div>

          <div className="grid-3" style={{ marginBottom: "1.5rem", opacity: 0.7 }}>
            <div className="stat-box">
              <div className="stat-label">{t.chargedTotal}</div>
              <div className="stat-val" style={{ color: "var(--text-primary)" }}>₹72,550</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.cghsBenchmark}</div>
              <div className="stat-val" style={{ color: "var(--brand-cyan)" }}>₹34,500</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">{t.potentialSavings}</div>
              <div className="stat-val" style={{ color: "var(--status-danger)" }}>₹38,050</div>
            </div>
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <h3>{t.overchargesTitle}</h3>
          </div>

          <div className="table-wrapper" style={{ opacity: 0.7 }}>
            <table>
              <thead>
                <tr>
                  <th>{t.itemCol}</th>
                  <th>{t.chargedCol}</th>
                  <th>{t.cghsCol}</th>
                  <th>{t.varianceCol}</th>
                  <th>{t.statusCol}</th>
                </tr>
              </thead>
              <tbody>
                {exampleItems.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{row.item}</td>
                    <td>₹{row.charged.toLocaleString("en-IN")}</td>
                    <td style={{ color: "var(--brand-cyan)" }}>₹{row.cghs.toLocaleString("en-IN")}</td>
                    <td style={{ color: "var(--status-danger)", fontWeight: 700 }}>
                      +₹{row.overcharge.toLocaleString("en-IN")}
                    </td>
                    <td>
                      <span className="badge badge-danger">{row.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
