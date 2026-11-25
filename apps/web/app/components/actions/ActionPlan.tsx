"use client";

import React, { useState } from "react";
import { useT } from "../../i18n/useT";
import { FINDING_GROUPS, type ActionPlanData, type PlanStep } from "../../lib/actionPlan";
import { createAction } from "../../lib/actionsApi";
import "./actions.css";

/**
 * Situation, findings, uncertainty and next steps for one module's result. With an open case a
 * step can be tracked (it starts as "chosen, not done yet"); without one the plan still reads.
 */
export function ActionPlan({ plan, caseId }: { plan: ActionPlanData; caseId?: string }) {
  const tr = useT();
  const headingId = `plan-${plan.module}`;
  return (
    <section className="case-panel act-plan" aria-labelledby={headingId}>
      <h3 id={headingId}>{tr("Your situation and next steps")}</h3>
      <p className="act-situation">{plan.situation}</p>

      {plan.amounts && (
        <dl className="act-amounts">
          {plan.amounts.map((a) => (
            <div key={a.label}>
              <dt>{a.label}</dt>
              <dd className="code-tabular">{a.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {plan.findings.length > 0 && (
        <>
          <h4>{tr("What was found")}</h4>
          {FINDING_GROUPS.map((group) => {
            const findings = plan.findings.filter((f) => f.group === group.id);
            if (findings.length === 0) return null;
            return (
              <details key={group.id} className="act-group" open={group.id !== "confirmed" && group.id !== "unable_to_assess"}>
                <summary>
                  {tr(group.label)} <span className="act-count">({findings.length})</span>
                </summary>
                <ul>
                  {findings.map((f) => (
                    <li key={f.id}>
                      <strong>{f.title}</strong>
                      <span>{f.observed}</span>
                      {f.evidence && <span className="act-evidence">{tr("Based on: {evidence}", { evidence: f.evidence })}</span>}
                      {f.why && <span>{tr("Why look into it: {why}", { why: f.why })}</span>}
                    </li>
                  ))}
                </ul>
              </details>
            );
          })}
        </>
      )}

      <h4>{tr("What remains uncertain")}</h4>
      <ul className="act-plain">
        {plan.uncertainties.map((u) => (
          <li key={u}>{u}</li>
        ))}
      </ul>

      {plan.steps.length > 0 && (
        <>
          <h4>{tr("Your next steps, in order")}</h4>
          <ol className="act-steps">
            {plan.steps.map((step) => (
              <Step key={step.id} step={step} module={plan.module} caseId={caseId} />
            ))}
          </ol>
        </>
      )}

      <h4>{tr("What happens next")}</h4>
      <p>{plan.whatNext}</p>
    </section>
  );
}

function Step({ step, module, caseId }: { step: PlanStep; module: ActionPlanData["module"]; caseId?: string }) {
  const tr = useT();
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [draft, setDraft] = useState<string | null>(null);
  const text = draft ?? step.draft ?? "";

  const track = async () => {
    if (!caseId) return;
    setState("saving");
    setError(null);
    try {
      await createAction(caseId, { module, kind: step.kind, title: step.title.slice(0, 200), finding_ref: step.id });
      setState("saved");
    } catch (err) {
      setState("idle");
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setError(tr("Copying is not available here. Select the text and copy it."));
    }
  };

  return (
    <li className="act-step">
      <p className="act-step-title">{step.title}</p>
      <p>{step.why}</p>
      {step.contact && <p className="act-evidence">{tr("Who to contact: {contact}", { contact: step.contact })}</p>}
      {step.prepare.length > 0 && (
        <>
          <p className="act-label">{tr("What to have ready")}</p>
          <ul className="act-plain">
            {step.prepare.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </>
      )}
      {step.draft && (
        <details className="act-draft">
          <summary>{tr("Help me prepare: a draft to check and send yourself")}</summary>
          <label className="sr-only" htmlFor={`draft-${module}-${step.id}`}>
            {tr("Draft for: {title}", { title: step.title })}
          </label>
          <textarea
            id={`draft-${module}-${step.id}`}
            className="textarea-field"
            rows={Math.min(16, text.split("\n").length + 2)}
            value={text}
            onChange={(e) => {
              setDraft(e.target.value);
              setCopied(false);
            }}
          />
          <button type="button" className="btn btn-secondary btn-compact" onClick={copy}>
            {copied ? tr("Copied") : tr("Copy the draft")}
          </button>
          <p className="act-evidence">{tr("This is a draft. Nothing has been sent.")}</p>
        </details>
      )}
      {caseId ? (
        <button type="button" className="btn btn-primary btn-compact" onClick={track} disabled={state !== "idle"}>
          {state === "saved" ? tr("Added to your progress") : state === "saving" ? tr("Adding…") : tr("Track this step")}
        </button>
      ) : (
        <p className="act-evidence">{tr("Open or start a case to track this step.")}</p>
      )}
      <span role="status" className="sr-only">
        {state === "saved" ? tr("Added to your progress") : copied ? tr("Copied") : ""}
      </span>
      {error && (
        <p className="ws-error" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}
