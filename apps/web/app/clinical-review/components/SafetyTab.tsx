"use client";

import React, { useEffect, useState } from "react";
import { ReviewerProfile, SAFETY_FLOOR_DISCLAIMER, clinicalPaths } from "../../lib/clinical";
import { StatePanel } from "../../components/clinical/StatePanel";
import { TONE_CLASS, humanizeEnum } from "../../lib/labels";
import { Guard, ReviewerCall, RuleView } from "../types";

const EMPTY_RULE_FORM = {
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
};

type RuleAction = "submit" | "activate" | "new-version" | "retire" | "APPROVE" | "REJECT";

/** Safety-rule governance: everyone sees the public rules; board members see the
 *  workspace, approve/reject, activate, re-version, retire (four-eyes) and propose. */
export function SafetyTab({ guard, call, me }: { guard: Guard; call: ReviewerCall; me: ReviewerProfile }) {
  const [rules, setRules] = useState<RuleView[]>([]);
  const [ruleForm, setRuleForm] = useState(EMPTY_RULE_FORM);
  const [ruleComment, setRuleComment] = useState<Record<string, string>>({});

  const loadRules = () =>
    guard(async () => {
      const path = me.is_safety_board_member ? clinicalPaths.safetyWorkspace() : clinicalPaths.safetyRules();
      setRules((await call<{ rules: RuleView[] }>(path)).rules);
    });

  useEffect(() => {
    void loadRules();
    // Load once per opening of the tab, as the tab button did before.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const ruleAction = (rule: RuleView, action: RuleAction) =>
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

  return (
    <section className="case-panel bn-card">
      <h3>Clinical safety governance</h3>
      <p style={{ fontSize: "0.85rem" }}>{SAFETY_FLOOR_DISCLAIMER}</p>
      {rules.length === 0 && <StatePanel kind="empty">No rules to show.</StatePanel>}
      {rules.map((rule) => (
        <div key={rule.rule_id} style={{ borderTop: "1px solid var(--border-subtle)", padding: "0.75rem 0" }}>
          <p>
            <strong>{rule.title}</strong> · version {rule.version} · <span className={TONE_CLASS.neutral}>{humanizeEnum(rule.status)}</span>
            {rule.is_demo && <span className={TONE_CLASS.demo} style={{ marginLeft: "0.4rem" }}>Demo fixture</span>}
            {rule.retirement_requested_by && (
              <span className={TONE_CLASS.warning} style={{ marginLeft: "0.4rem" }}>Retirement requested — awaiting a second board member</span>
            )}
            {rule.review_overdue && <span className="badge badge-danger" style={{ marginLeft: "0.4rem" }}>review overdue</span>}
          </p>
          <p style={{ fontSize: "0.85rem" }}>{rule.description}</p>
          <p style={{ fontSize: "0.8rem" }}>
            Trigger words: {rule.trigger.match_any.join(", ")} · Source: {rule.source.name}
            {rule.source.version ? ` (${rule.source.version})` : ""} · Limitations: {rule.limitations}
          </p>
          <p style={{ fontSize: "0.8rem" }}>
            Proposed by {rule.proposed_by?.name} ({rule.proposed_by?.verification_label}).{" "}
            {rule.approvals
              .map((a) => `${a.decision === "APPROVE" ? "Approved" : "Rejected"} by ${a.reviewer.name}${a.applies_to_current_content ? "" : " (earlier submission)"}`)
              .join("; ")}
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
                  <button
                    type="button"
                    className="btn"
                    style={{ border: "1px solid var(--status-danger)" }}
                    disabled={rule.retirement_requested_by === me.id}
                    title="Retirement needs two board members: one requests, a different one confirms."
                    onClick={() => ruleAction(rule, "retire")}
                  >
                    {rule.retirement_requested_by
                      ? rule.retirement_requested_by === me.id
                        ? "Retirement requested by you"
                        : "Confirm retirement"
                      : "Request retirement"}
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
  );
}
