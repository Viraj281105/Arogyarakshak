"use client";

import React, { useCallback, useState } from "react";
import Link from "next/link";
import {
  AuditEvent,
  COI_OPTIONS,
  ClinicalStatement,
  EvidenceItem,
  FactDecision,
  ReviewerProfile,
  SAFETY_FLOOR_DISCLAIMER,
  clinicalPaths,
  clinicalRequest,
} from "../lib/clinical";
import { ClinicalStatementCard, ProvenanceBadge, ReviewerAttribution } from "../components/clinical/Attribution";

interface AssignedReview {
  review_id: string;
  case_id: string;
  source_module: string;
  review_type: "CLINICAL_STATEMENT" | "FACT_CONFIRMATION";
  status: string;
  clinical_question: string;
  coi_context: { hospital_names: string[]; insurer_name: string | null; note: string };
  coi_label: string | null;
}

interface ReviewerDetail extends AssignedReview {
  statements: ClinicalStatement[];
  facts: FactDecision[];
  finalization_confirmation_text: string;
  fact_decision_confirmation_text: string;
}

interface TranscriptionView {
  task_id: string;
  field_type: string;
  risk_level: string;
  masked_context: string;
  ocr_candidate: string | null;
  ocr_candidate_hidden: boolean;
  accepting_readings: boolean;
  your_reading: { value: string | null; unreadable: boolean } | null;
  instructions: string;
}

interface RuleView {
  rule_id: string;
  rule_key: string;
  version: number;
  title: string;
  status: string;
  description: string;
  trigger: { match_any: string[]; context_types: string[] };
  action: { type: string; severity: string; message: string };
  source: { name: string; reference: string | null; version: string | null; section: string | null };
  limitations: string;
  proposed_by: { name: string; reviewer_id: string; verification_label: string } | null;
  approvals: { decision: string; comment: string | null; reviewer: { name: string; verification_label: string }; applies_to_current_content: boolean }[];
  review_due_date: string;
  review_overdue: boolean;
  is_demo: boolean;
}

type Tab = "reviews" | "transcriptions" | "safety";

const panel: React.CSSProperties = {
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-md)",
  padding: "1.25rem",
  marginBottom: "1.25rem",
  background: "var(--bg-surface)",
};

export default function ClinicalReviewWorkspace() {
  // Held in memory only: the credential is a bearer secret and is never written to
  // localStorage. Reloading the page means pasting it again.
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [me, setMe] = useState<ReviewerProfile | null>(null);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("reviews");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [reg, setReg] = useState({
    name: "",
    category: "DOCTOR",
    designation: "",
    specialty: "",
    registration_number: "",
    registration_authority: "",
    affiliation: "",
    standing_disclosures: "",
  });

  const [queue, setQueue] = useState<AssignedReview[]>([]);
  const [detail, setDetail] = useState<ReviewerDetail | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[] | null>(null);
  const [audit, setAudit] = useState<AuditEvent[] | null>(null);
  const [coi, setCoi] = useState({ category: "", disclosure: "" });
  const [editor, setEditor] = useState({ statementId: "", selected: [] as string[], text: "", limitations: "" });
  const [confirmTicked, setConfirmTicked] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [factInput, setFactInput] = useState<Record<string, { decision: string; note: string; confirm: boolean }>>({});

  const [tasks, setTasks] = useState<TranscriptionView[]>([]);
  const [readings, setReadings] = useState<Record<string, { value: string; unreadable: boolean; confidence: string }>>({});

  const [rules, setRules] = useState<RuleView[]>([]);
  const [ruleForm, setRuleForm] = useState({
    rule_key: "",
    title: "",
    description: "",
    terms: "",
    severity: "URGENT",
    action_type: "SHOW_SAFETY_ESCALATION",
    message: "",
    source_name: "",
    source_reference: "",
    source_version: "",
    source_section: "",
    limitations: "",
    effective_date: "",
    review_due_date: "",
  });
  const [ruleComment, setRuleComment] = useState<Record<string, string>>({});

  const call = useCallback(
    async <T,>(path: string, method: "GET" | "POST" | "PUT" = "GET", body?: unknown): Promise<T> =>
      clinicalRequest<T>(path, { method, body, reviewerToken: token }),
    [token]
  );

  const guard = async (fn: () => Promise<void>, ok?: string) => {
    setError(null);
    setNotice(null);
    try {
      await fn();
      if (ok) setNotice(ok);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const openWithCredential = (value: string) =>
    guard(async () => {
      const profile = await clinicalRequest<ReviewerProfile>(clinicalPaths.reviewerMe(), { reviewerToken: value });
      setToken(value);
      setMe(profile);
      const q = await clinicalRequest<AssignedReview[]>(clinicalPaths.assigned(), { reviewerToken: value });
      setQueue(q);
    });

  const register = () =>
    guard(async () => {
      const body = Object.fromEntries(Object.entries(reg).map(([k, v]) => [k, v.trim() || null]));
      const res = await clinicalRequest<{ reviewer: ReviewerProfile; reviewer_token: string }>(clinicalPaths.reviewers(), {
        method: "POST",
        body,
      });
      setIssuedToken(res.reviewer_token);
      await openWithCredential(res.reviewer_token);
    });

  const refreshQueue = () => guard(async () => setQueue(await call<AssignedReview[]>(clinicalPaths.assigned())));

  const openReview = (reviewId: string) =>
    guard(async () => {
      const d = await call<ReviewerDetail>(clinicalPaths.reviewerReview(reviewId));
      setDetail(d);
      setEvidence(null);
      setAudit(null);
      setConfirmTicked(false);
      const draft = d.statements.find((s) => s.status === "DRAFT" || s.status === "UNDER_REVIEW");
      setEditor(
        draft
          ? { statementId: draft.statement_id, selected: draft.evidence_reviewed.map((e) => e.item_id), text: draft.reviewer_statement, limitations: draft.limitations }
          : { statementId: "", selected: [], text: "", limitations: "" }
      );
    });

  const accept = () =>
    guard(async () => {
      await call(clinicalPaths.accept(detail!.review_id), "POST", { coi_category: coi.category, coi_disclosure: coi.disclosure || null });
      await openReview(detail!.review_id);
      setQueue(await call<AssignedReview[]>(clinicalPaths.assigned()));
    }, "Accepted. Your conflict-of-interest declaration is recorded.");

  const decline = () =>
    guard(async () => {
      await call(clinicalPaths.decline(detail!.review_id), "POST", { reason: null });
      setDetail(null);
      await refreshQueue();
    }, "Declined.");

  const loadEvidence = () =>
    guard(async () => setEvidence((await call<{ evidence: EvidenceItem[] }>(clinicalPaths.evidence(detail!.review_id))).evidence));

  const saveDraft = () =>
    guard(async () => {
      const body = { evidence_reviewed: editor.selected, reviewer_statement: editor.text, limitations: editor.limitations };
      const saved = editor.statementId
        ? await call<ClinicalStatement>(clinicalPaths.statement(detail!.review_id, editor.statementId), "PUT", body)
        : await call<ClinicalStatement>(clinicalPaths.statements(detail!.review_id), "POST", body);
      setEditor((prev) => ({ ...prev, statementId: saved.statement_id }));
      await openReview(detail!.review_id);
    }, "Draft saved. Only you can see drafts.");

  const statementAction = (statementId: string, action: "submit" | "revise" | "return-to-draft") =>
    guard(async () => {
      await call(`${clinicalPaths.statement(detail!.review_id, statementId)}/${action}`, "POST");
      await openReview(detail!.review_id);
    });

  const finalizeStatement = (statementId: string) =>
    guard(async () => {
      // The reviewer ticks the box themselves; the sentence is the server's, shown above.
      await call(`${clinicalPaths.statement(detail!.review_id, statementId)}/finalize`, "POST", {
        confirmation: confirmTicked,
        confirmation_text: confirmTicked ? detail!.finalization_confirmation_text : "",
      });
      await openReview(detail!.review_id);
    }, "Statement finalized. It is now immutable; changes create a new version.");

  const withdraw = (statementId: string) =>
    guard(async () => {
      await call(`${clinicalPaths.statement(detail!.review_id, statementId)}/withdraw`, "POST", { reason: withdrawReason });
      await openReview(detail!.review_id);
    }, "Statement withdrawn.");

  const decideFact = (fact: FactDecision) =>
    guard(async () => {
      const input = factInput[fact.fact_id];
      await call(clinicalPaths.factDecision(detail!.review_id, fact.fact_id), "POST", {
        decision: input?.decision,
        note: input?.note || null,
        confirmation: !!input?.confirm,
        confirmation_text: input?.confirm ? detail!.fact_decision_confirmation_text : "",
      });
      await openReview(detail!.review_id);
    }, "Decision recorded.");

  const showAudit = () => guard(async () => setAudit(await call<AuditEvent[]>(clinicalPaths.reviewerAudit(detail!.review_id))));

  const loadTasks = () => guard(async () => setTasks(await call<TranscriptionView[]>(clinicalPaths.myTranscriptions())));

  const submitReading = (taskId: string) =>
    guard(async () => {
      const r = readings[taskId] ?? { value: "", unreadable: false, confidence: "HIGH" };
      await call(clinicalPaths.transcriptionReadings(taskId), "POST", {
        value: r.unreadable ? null : r.value,
        unreadable: r.unreadable,
        reviewer_confidence: r.confidence,
      });
      await loadTasks();
    }, "Reading submitted. Other readers cannot see it.");

  const loadRules = () =>
    guard(async () => {
      const path = me?.is_safety_board_member ? clinicalPaths.safetyWorkspace() : clinicalPaths.safetyRules();
      setRules((await clinicalRequest<{ rules: RuleView[] }>(path, { reviewerToken: token })).rules);
    });

  const proposeRule = () =>
    guard(async () => {
      await call(clinicalPaths.safetyRules(), "POST", {
        rule_key: ruleForm.rule_key,
        title: ruleForm.title,
        description: ruleForm.description,
        trigger: { match_any: ruleForm.terms.split(",").map((t) => t.trim()).filter(Boolean), context_types: ["document_text", "diagnosis"] },
        action: { type: ruleForm.action_type, severity: ruleForm.severity, message: ruleForm.message },
        source_name: ruleForm.source_name,
        source_reference: ruleForm.source_reference || null,
        source_version: ruleForm.source_version || null,
        source_section: ruleForm.source_section || null,
        limitations: ruleForm.limitations,
        effective_date: ruleForm.effective_date || null,
        review_due_date: ruleForm.review_due_date,
      });
      await loadRules();
    }, "Draft rule created. It needs independent approval before it can be activated.");

  const ruleAction = (rule: RuleView, action: "submit" | "activate" | "new-version" | "retire" | "APPROVE" | "REJECT") =>
    guard(async () => {
      const base = clinicalPaths.safetyRule(rule.rule_id);
      if (action === "APPROVE" || action === "REJECT") {
        await call(`${base}/decisions`, "POST", { decision: action, comment: ruleComment[rule.rule_id] || null });
      } else if (action === "retire") {
        await call(`${base}/retire`, "POST", { reason: ruleComment[rule.rule_id] || "" });
      } else {
        await call(`${base}/${action}`, "POST");
      }
      await loadRules();
    });

  const currentDraft = detail?.statements.find((s) => s.status === "DRAFT" || s.status === "UNDER_REVIEW");
  const finalized = detail?.statements.find((s) => s.status === "FINALIZED");
  const canWork = detail && (detail.status === "IN_REVIEW" || detail.status === "COMPLETED");

  return (
    <main className="container" style={{ paddingTop: "1.5rem", paddingBottom: "3rem" }}>
      <p>
        <Link href="/">← Back to ArogyaRakshak</Link>
      </p>
      <h1 style={{ marginBottom: "0.25rem" }}>Clinical Reviewer Workspace</h1>
      <p style={{ fontSize: "0.9rem", maxWidth: 760 }}>
        For doctors, pharmacists, medical transcriptionists and trained annotators. You see only the evidence a patient chose
        to share with you, and everything you write is attributed to you with your declared conflict of interest. Your
        registration is shown to patients exactly as verified — self-declared details are labelled as such.
      </p>

      {error && (
        <div role="alert" style={{ ...panel, borderColor: "var(--status-danger)", color: "#fca5a5" }}>
          ⚠️ {error}
        </div>
      )}
      {notice && <div style={{ ...panel, borderColor: "var(--status-success)" }}>✓ {notice}</div>}

      {!me && (
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
      )}

      {issuedToken && (
        <div role="status" style={{ ...panel, borderColor: "var(--status-warning)" }}>
          <strong>Your reviewer credential (shown once — store it now):</strong>
          <code style={{ display: "block", wordBreak: "break-all", marginTop: "0.5rem" }}>{issuedToken}</code>
          <button type="button" className="btn" style={{ marginTop: "0.5rem", border: "1px solid var(--border-subtle)" }} onClick={() => setIssuedToken(null)}>
            I have stored it
          </button>
        </div>
      )}

      {me && (
        <>
          <section style={panel}>
            <ReviewerAttribution reviewer={me} />
            {me.is_safety_board_member && <span className="badge badge-info">Clinical safety board member</span>}
          </section>

          <nav className="module-tabs" role="tablist" aria-label="Workspace sections">
            {(["reviews", "transcriptions", "safety"] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => {
                  setTab(t);
                  if (t === "transcriptions") void loadTasks();
                  if (t === "safety") void loadRules();
                  if (t === "reviews") void refreshQueue();
                }}
              >
                {t === "reviews" ? "Assigned reviews" : t === "transcriptions" ? "Transcriptions" : "Safety governance"}
              </button>
            ))}
          </nav>

          {tab === "reviews" && (
            <>
              <section style={panel}>
                <h3>Assigned to you</h3>
                {queue.length === 0 && <p style={{ fontSize: "0.9rem" }}>No reviews are assigned to you.</p>}
                {queue.map((r) => (
                  <div key={r.review_id} style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem", flexWrap: "wrap", padding: "0.4rem 0" }}>
                    <span>
                      {r.review_id} · {r.source_module} · {r.review_type === "FACT_CONFIRMATION" ? "fact confirmation" : "clinical statement"} ·{" "}
                      <span className="badge badge-info">{r.status}</span>
                    </span>
                    <button type="button" className="btn btn-secondary" onClick={() => openReview(r.review_id)}>
                      Open
                    </button>
                  </div>
                ))}
              </section>

              {detail && (
                <section style={panel} aria-labelledby="review-detail">
                  <h3 id="review-detail">Review {detail.review_id}</h3>
                  <p>
                    <strong>Question:</strong> {detail.clinical_question}
                  </p>

                  {detail.status === "ASSIGNED" && (
                    <div>
                      <p style={{ fontSize: "0.9rem" }}>
                        Before you see any clinical evidence, declare your relationship to this case. Hospital:{" "}
                        {detail.coi_context.hospital_names.join(", ") || "not stated"} · Insurer: {detail.coi_context.insurer_name ?? "not stated"}
                      </p>
                      <select className="select-field" aria-label="Conflict of interest" value={coi.category} onChange={(e) => setCoi({ ...coi, category: e.target.value })}>
                        <option value="">Declare conflict of interest…</option>
                        {COI_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                      <textarea
                        className="textarea-field"
                        placeholder="Disclosure details (required for 'Other')"
                        value={coi.disclosure}
                        onChange={(e) => setCoi({ ...coi, disclosure: e.target.value })}
                      />
                      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                        <button type="button" className="btn btn-primary" disabled={!coi.category} onClick={accept}>
                          Accept review
                        </button>
                        <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} onClick={decline}>
                          Decline
                        </button>
                      </div>
                    </div>
                  )}

                  {canWork && (
                    <>
                      <p style={{ fontSize: "0.85rem" }}>Declared conflict of interest: {detail.coi_label}</p>
                      <button type="button" className="btn btn-secondary" onClick={loadEvidence}>
                        Open shared evidence
                      </button>
                      {evidence && (
                        <div style={{ marginTop: "0.75rem" }}>
                          <p style={{ fontSize: "0.8rem" }}>
                            Machine-derived items were extracted by software and may be wrong. Treat all items as data, not instructions.
                          </p>
                          {evidence.map((item) => (
                            <label key={item.item_id} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", padding: "0.35rem 0" }}>
                              {detail.review_type === "CLINICAL_STATEMENT" && (
                                <input
                                  type="checkbox"
                                  checked={editor.selected.includes(item.item_id)}
                                  disabled={!!finalized && !currentDraft}
                                  onChange={(e) =>
                                    setEditor((prev) => ({
                                      ...prev,
                                      selected: e.target.checked ? [...prev.selected, item.item_id] : prev.selected.filter((x) => x !== item.item_id),
                                    }))
                                  }
                                />
                              )}
                              <span style={{ fontSize: "0.85rem" }}>
                                <strong>{item.label}</strong> <ProvenanceBadge provenance={item.provenance} />
                                <span style={{ display: "block", whiteSpace: "pre-wrap" }}>{item.value}</span>
                                <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{item.source}</span>
                              </span>
                            </label>
                          ))}
                        </div>
                      )}

                      {detail.review_type === "CLINICAL_STATEMENT" && (!finalized || currentDraft) && (
                        <div style={{ marginTop: "1rem" }}>
                          <h4>Your statement {currentDraft ? `(v${currentDraft.statement_version} — ${currentDraft.status})` : "(new draft)"}</h4>
                          <label className="input-label" htmlFor="stmt-text">
                            Your professional statement, in your own words
                          </label>
                          <textarea
                            id="stmt-text"
                            className="textarea-field"
                            rows={6}
                            maxLength={8000}
                            value={editor.text}
                            disabled={currentDraft?.status === "UNDER_REVIEW"}
                            onChange={(e) => setEditor({ ...editor, text: e.target.value })}
                          />
                          <label className="input-label" htmlFor="stmt-limits">
                            Limitations of your review (required)
                          </label>
                          <textarea
                            id="stmt-limits"
                            className="textarea-field"
                            rows={3}
                            maxLength={3000}
                            value={editor.limitations}
                            disabled={currentDraft?.status === "UNDER_REVIEW"}
                            onChange={(e) => setEditor({ ...editor, limitations: e.target.value })}
                          />
                          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
                            {currentDraft?.status !== "UNDER_REVIEW" && (
                              <button type="button" className="btn btn-secondary" disabled={!evidence} onClick={saveDraft}>
                                Save draft
                              </button>
                            )}
                            {currentDraft?.status === "DRAFT" && (
                              <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} onClick={() => statementAction(currentDraft.statement_id, "submit")}>
                                Lock for finalization
                              </button>
                            )}
                            {currentDraft?.status === "UNDER_REVIEW" && (
                              <button type="button" className="btn" style={{ border: "1px solid var(--border-subtle)" }} onClick={() => statementAction(currentDraft.statement_id, "return-to-draft")}>
                                Back to editing
                              </button>
                            )}
                          </div>
                          {currentDraft && (
                            <div style={{ marginTop: "1rem", padding: "0.75rem", border: "1px solid var(--status-warning)", borderRadius: "var(--radius-md)" }}>
                              <label style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
                                <input type="checkbox" checked={confirmTicked} onChange={(e) => setConfirmTicked(e.target.checked)} />
                                <span>{detail.finalization_confirmation_text}</span>
                              </label>
                              <button
                                type="button"
                                className="btn btn-primary"
                                style={{ marginTop: "0.5rem" }}
                                disabled={!confirmTicked}
                                onClick={() => finalizeStatement(currentDraft.statement_id)}
                              >
                                Finalize and sign
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      {detail.review_type === "CLINICAL_STATEMENT" && detail.statements.filter((s) => s.status !== "DRAFT" && s.status !== "UNDER_REVIEW").length > 0 && (
                        <div style={{ marginTop: "1rem" }}>
                          <h4>Your published versions</h4>
                          {detail.statements
                            .filter((s) => s.status !== "DRAFT" && s.status !== "UNDER_REVIEW")
                            .map((s) => (
                              <div key={s.statement_id}>
                                <ClinicalStatementCard statement={s} />
                                {s.status === "FINALIZED" && !currentDraft && (
                                  <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                                    <button type="button" className="btn btn-secondary" onClick={() => statementAction(s.statement_id, "revise")}>
                                      Create new version
                                    </button>
                                    <input
                                      className="input-field"
                                      style={{ maxWidth: 320 }}
                                      placeholder="Reason for withdrawal"
                                      value={withdrawReason}
                                      onChange={(e) => setWithdrawReason(e.target.value)}
                                    />
                                    <button
                                      type="button"
                                      className="btn"
                                      style={{ border: "1px solid var(--status-danger)", color: "var(--status-danger)" }}
                                      disabled={!withdrawReason.trim()}
                                      onClick={() => withdraw(s.statement_id)}
                                    >
                                      Withdraw
                                    </button>
                                  </div>
                                )}
                              </div>
                            ))}
                        </div>
                      )}

                      {detail.review_type === "FACT_CONFIRMATION" && (
                        <div style={{ marginTop: "1rem" }}>
                          <h4>Facts to confirm</h4>
                          {detail.facts.map((f) => (
                            <div key={f.fact_id} style={{ borderTop: "1px solid var(--border-subtle)", padding: "0.75rem 0" }}>
                              <p>{f.fact_question}</p>
                              {f.decision !== "PENDING" ? (
                                <p>
                                  <span className="badge badge-success">{f.decision}</span> {f.reviewer_note}
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
                                    onClick={() => decideFact(f)}
                                  >
                                    Record decision
                                  </button>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  <button type="button" className="btn" style={{ marginTop: "1rem", border: "1px solid var(--border-subtle)" }} onClick={showAudit}>
                    Show audit trail
                  </button>
                  {audit && (
                    <ol className="timeline-list" style={{ fontSize: "0.8rem", marginTop: "0.5rem" }}>
                      {audit.map((e) => (
                        <li key={e.id} className="timeline-item">
                          {e.created_at} — {e.event_type} ({e.actor_type})
                        </li>
                      ))}
                    </ol>
                  )}
                </section>
              )}
            </>
          )}

          {tab === "transcriptions" && (
            <section style={panel}>
              <h3>Transcription tasks</h3>
              <p style={{ fontSize: "0.85rem" }}>
                You are reading as a transcription reviewer. For possible-medication fields you cannot see the software&apos;s guess or
                any other reader&apos;s answer. If you cannot read it with confidence, mark it unreadable.
              </p>
              {tasks.length === 0 && <p>No transcription tasks are assigned to you.</p>}
              {tasks.map((t) => (
                <div key={t.task_id} style={{ borderTop: "1px solid var(--border-subtle)", padding: "0.75rem 0" }}>
                  <p>
                    <strong>{t.field_type.replace("_", " ")}</strong> · <span className="badge badge-warning">{t.risk_level} risk</span>
                  </p>
                  <p>
                    Context: <code>{t.masked_context}</code>
                  </p>
                  {t.ocr_candidate && <p style={{ fontSize: "0.8rem" }}>Software reading: {t.ocr_candidate}</p>}
                  {t.ocr_candidate_hidden && <p style={{ fontSize: "0.8rem" }}>Software reading hidden (blind review).</p>}
                  <p style={{ fontSize: "0.75rem", opacity: 0.8 }}>{t.instructions}</p>
                  {t.your_reading ? (
                    <p>Your reading: {t.your_reading.unreadable ? "unreadable" : t.your_reading.value}</p>
                  ) : t.accepting_readings ? (
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                      <input
                        className="input-field"
                        style={{ maxWidth: 280 }}
                        aria-label="What is written"
                        maxLength={200}
                        disabled={readings[t.task_id]?.unreadable}
                        value={readings[t.task_id]?.value ?? ""}
                        onChange={(e) => setReadings({ ...readings, [t.task_id]: { ...(readings[t.task_id] ?? { unreadable: false, confidence: "HIGH" }), value: e.target.value } })}
                      />
                      <label>
                        <input
                          type="checkbox"
                          checked={readings[t.task_id]?.unreadable ?? false}
                          onChange={(e) => setReadings({ ...readings, [t.task_id]: { ...(readings[t.task_id] ?? { value: "", confidence: "HIGH" }), unreadable: e.target.checked } })}
                        />{" "}
                        Unreadable
                      </label>
                      <select
                        className="select-field"
                        aria-label="Your confidence"
                        value={readings[t.task_id]?.confidence ?? "HIGH"}
                        onChange={(e) => setReadings({ ...readings, [t.task_id]: { ...(readings[t.task_id] ?? { value: "", unreadable: false }), confidence: e.target.value } })}
                      >
                        <option value="HIGH">High confidence</option>
                        <option value="MEDIUM">Medium confidence</option>
                        <option value="LOW">Low confidence</option>
                      </select>
                      <button type="button" className="btn btn-primary" onClick={() => submitReading(t.task_id)}>
                        Submit reading
                      </button>
                    </div>
                  ) : (
                    <p>This task is closed.</p>
                  )}
                </div>
              ))}
            </section>
          )}

          {tab === "safety" && (
            <section style={panel}>
              <h3>Clinical safety governance</h3>
              <p style={{ fontSize: "0.85rem" }}>{SAFETY_FLOOR_DISCLAIMER}</p>
              {rules.length === 0 && <p>No rules to show.</p>}
              {rules.map((rule) => (
                <div key={rule.rule_id} style={{ borderTop: "1px solid var(--border-subtle)", padding: "0.75rem 0" }}>
                  <p>
                    <strong>{rule.title}</strong> · v{rule.version} · <span className="badge badge-info">{rule.status}</span>
                    {rule.is_demo && <span className="badge badge-warning" style={{ marginLeft: "0.4rem" }}>demo fixture</span>}
                    {rule.review_overdue && <span className="badge badge-danger" style={{ marginLeft: "0.4rem" }}>review overdue</span>}
                  </p>
                  <p style={{ fontSize: "0.85rem" }}>{rule.description}</p>
                  <p style={{ fontSize: "0.8rem" }}>
                    Trigger words: {rule.trigger.match_any.join(", ")} · Source: {rule.source.name}
                    {rule.source.version ? ` (${rule.source.version})` : ""} · Limitations: {rule.limitations}
                  </p>
                  <p style={{ fontSize: "0.8rem" }}>
                    Proposed by {rule.proposed_by?.name} ({rule.proposed_by?.verification_label}).{" "}
                    {rule.approvals.map((a) => `${a.decision} by ${a.reviewer.name}${a.applies_to_current_content ? "" : " (earlier content)"}`).join("; ")}
                  </p>
                  {me.is_safety_board_member && (
                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                      <input
                        className="input-field"
                        style={{ maxWidth: 320 }}
                        placeholder="Comment / reason"
                        value={ruleComment[rule.rule_id] ?? ""}
                        onChange={(e) => setRuleComment({ ...ruleComment, [rule.rule_id]: e.target.value })}
                      />
                      {rule.status === "DRAFT" && rule.proposed_by?.reviewer_id === me.id && (
                        <button type="button" className="btn btn-secondary" onClick={() => ruleAction(rule, "submit")}>
                          Submit for review
                        </button>
                      )}
                      {rule.status === "UNDER_REVIEW" && rule.proposed_by?.reviewer_id !== me.id && (
                        <>
                          <button type="button" className="btn btn-primary" onClick={() => ruleAction(rule, "APPROVE")}>
                            Approve
                          </button>
                          <button type="button" className="btn" style={{ border: "1px solid var(--status-danger)" }} onClick={() => ruleAction(rule, "REJECT")}>
                            Reject
                          </button>
                        </>
                      )}
                      {rule.status === "APPROVED" && (
                        <button type="button" className="btn btn-primary" onClick={() => ruleAction(rule, "activate")}>
                          Activate
                        </button>
                      )}
                      {rule.status === "ACTIVE" && (
                        <>
                          <button type="button" className="btn btn-secondary" onClick={() => ruleAction(rule, "new-version")}>
                            New version
                          </button>
                          <button type="button" className="btn" style={{ border: "1px solid var(--status-danger)" }} onClick={() => ruleAction(rule, "retire")}>
                            Retire
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {me.is_safety_board_member && (
                <div style={{ marginTop: "1.25rem" }}>
                  <h4>Propose a rule adapted from a published protocol</h4>
                  <p style={{ fontSize: "0.8rem" }}>
                    Name the source protocol, its version and section. Do not invent protocol content. A different board member
                    must approve before activation.
                  </p>
                  <div className="grid-2">
                    {(
                      [
                        ["rule_key", "Rule key (slug)"],
                        ["title", "Title"],
                        ["terms", "Trigger terms (comma-separated)"],
                        ["message", "Message shown to the user"],
                        ["source_name", "Source protocol name"],
                        ["source_version", "Source version"],
                        ["source_section", "Source section"],
                        ["source_reference", "Source reference"],
                        ["effective_date", "Effective date (YYYY-MM-DD)"],
                        ["review_due_date", "Review due date (YYYY-MM-DD)"],
                      ] as const
                    ).map(([key, label]) => (
                      <div key={key}>
                        <label className="input-label" htmlFor={`rule-${key}`}>
                          {label}
                        </label>
                        <input id={`rule-${key}`} className="input-field" value={ruleForm[key]} onChange={(e) => setRuleForm({ ...ruleForm, [key]: e.target.value })} />
                      </div>
                    ))}
                  </div>
                  <label className="input-label" htmlFor="rule-description">
                    Description
                  </label>
                  <textarea id="rule-description" className="textarea-field" value={ruleForm.description} onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })} />
                  <label className="input-label" htmlFor="rule-limitations">
                    Limitations (required)
                  </label>
                  <textarea id="rule-limitations" className="textarea-field" value={ruleForm.limitations} onChange={(e) => setRuleForm({ ...ruleForm, limitations: e.target.value })} />
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                    <select className="select-field" aria-label="Severity" value={ruleForm.severity} onChange={(e) => setRuleForm({ ...ruleForm, severity: e.target.value })}>
                      <option value="URGENT">Urgent</option>
                      <option value="ADVISORY">Advisory</option>
                    </select>
                    <select className="select-field" aria-label="Action" value={ruleForm.action_type} onChange={(e) => setRuleForm({ ...ruleForm, action_type: e.target.value })}>
                      <option value="SHOW_SAFETY_ESCALATION">Show safety escalation</option>
                      <option value="RECOMMEND_CLINICAL_REVIEW">Recommend clinical review</option>
                    </select>
                    <button type="button" className="btn btn-primary" onClick={proposeRule}>
                      Create draft
                    </button>
                  </div>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </main>
  );
}
