"use client";

import React, { useCallback, useEffect, useId, useState } from "react";
import { LOCALE } from "../../i18n/format";
import { useT } from "../../i18n/useT";
import { ACTIONS_CHANGED, createAction, deleteAction, listActions, recordActionEvent } from "../../lib/actionsApi";
import type { ActionModule, ActionStatus, CaseAction, ContactMethod } from "../../shared/api-client/accounts";
import { useLanguage } from "../../shell/ShellProvider";
import { StatusBadge } from "../ui/Badges";
import { ConfirmationDialog } from "../ui/Overlays";
import { ErrorState, LoadingState } from "../ui/States";
import { ASKS_AMOUNT_CORRECTED, CONTACT_LABEL, EVENT_LABEL, NEEDS_DATE, NEXT_HINT, STATUS_LABEL, STATUS_TONE } from "./actionLabels";
import "./actions.css";

/**
 * What the person chose to do and what they say happened since. `module` narrows the list to one
 * check; without it the whole case is shown. Everything here is labelled as the user's record.
 */
export function ActionTracker({ caseId, module }: { caseId: string; module?: ActionModule }) {
  const tr = useT();
  const [actions, setActions] = useState<CaseAction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((n) => n + 1), []);

  useEffect(() => {
    window.addEventListener(ACTIONS_CHANGED, reload);
    return () => window.removeEventListener(ACTIONS_CHANGED, reload);
  }, [reload]);

  useEffect(() => {
    let cancelled = false;
    listActions(caseId)
      .then((list) => {
        if (cancelled) return;
        setActions(list);
        setError(null);
      })
      .catch((err: unknown) => !cancelled && setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [caseId, tick]);

  const shown = actions?.filter((a) => !module || a.module === module) ?? null;
  const headingId = `progress-${module ?? "case"}`;

  return (
    <section className="case-panel act-tracker" aria-labelledby={headingId}>
      <h3 id={headingId}>{tr("Your progress")}</h3>
      <p className="act-evidence">
        {tr("These are your own notes of what you did and what you heard back. ArogyaRakshak sends nothing and does not verify them.")}
      </p>
      {error && (
        <ErrorState
          title={tr("Your progress could not be loaded")}
          action={
            <button type="button" className="btn btn-secondary btn-compact" onClick={reload}>
              {tr("Try again")}
            </button>
          }
        >
          <p>{error}</p>
        </ErrorState>
      )}
      {!error && shown === null && <LoadingState label={tr("Loading your progress…")} minHeight="4rem" />}
      {shown?.length === 0 && <p>{tr("Nothing tracked yet. Choose a next step above, or add your own below.")}</p>}
      {shown && shown.length > 0 && (
        <ul className="act-list">
          {shown.map((action) => (
            <ActionCard key={action.id} caseId={caseId} action={action} />
          ))}
        </ul>
      )}
      {shown && <AddOwnStep caseId={caseId} module={module ?? "kadi"} />}
    </section>
  );
}

function AddOwnStep({ caseId, module }: { caseId: string; module: ActionModule }) {
  const tr = useT();
  const id = useId();
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createAction(caseId, { module, kind: "other", title: title.trim() });
      setTitle("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="act-add" onSubmit={add}>
      <label className="input-label" htmlFor={id}>
        {tr("Add your own step")}
      </label>
      <div className="act-row">
        <input id={id} className="input-field" maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
        <button type="submit" className="btn btn-secondary btn-compact" disabled={busy || !title.trim()}>
          {busy ? tr("Adding…") : tr("Add")}
        </button>
      </div>
      {error && (
        <p className="ws-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

function ActionCard({ caseId, action }: { caseId: string; action: CaseAction }) {
  const tr = useT();
  const [lang] = useLanguage();
  const id = useId();
  const [next, setNext] = useState<ActionStatus | "">("");
  const [day, setDay] = useState("");
  const [note, setNote] = useState("");
  const [institution, setInstitution] = useState("");
  const [method, setMethod] = useState<ContactMethod | "">("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);

  const date = (value: string) => new Date(value).toLocaleDateString(LOCALE[lang], { day: "numeric", month: "short", year: "numeric" });
  const needsDay = next !== "" && NEEDS_DATE.has(next);
  const asksContact = next === "sent";
  const asksAmount = next !== "" && ASKS_AMOUNT_CORRECTED.has(next);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!next) return;
    if (needsDay && !day) {
      setError(tr("Say which day this happened."));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await recordActionEvent(caseId, action.id, {
        status: next,
        occurred_on: day || null,
        note: note.trim() || null,
        institution: asksContact && institution.trim() ? institution.trim() : null,
        contact_method: asksContact && method ? method : null,
        amount_corrected: asksAmount && amount !== "" ? Number(amount) : null,
      });
      setNext("");
      setDay("");
      setNote("");
      setAmount("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setConfirm(false);
    try {
      await deleteAction(caseId, action.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <li className="act-card">
      <div className="act-card-head">
        <h4>{action.title}</h4>
        <StatusBadge tone={STATUS_TONE[action.status]}>{tr(STATUS_LABEL[action.status])}</StatusBadge>
      </div>
      {action.institution && (
        <p className="act-evidence">
          {action.contact_method
            ? tr("Contacted: {institution} ({method})", { institution: action.institution, method: tr(CONTACT_LABEL[action.contact_method]) })
            : tr("Contact: {institution}", { institution: action.institution })}
        </p>
      )}
      {action.amount_corrected !== null && action.amount_corrected !== undefined && (
        <p className="act-evidence">{tr("Amount you recorded as corrected or refunded: ₹{amount}", { amount: action.amount_corrected.toLocaleString("en-IN") })}</p>
      )}
      <p>
        <strong>{tr("Next:")}</strong> {tr(NEXT_HINT[action.status])}
      </p>

      <details>
        <summary>{tr("Timeline ({count} entries)", { count: action.events.length })}</summary>
        <ol className="act-timeline">
          {action.events.map((event, index) => (
            <li key={`${event.recorded_at}-${index}`}>
              <strong>{tr(STATUS_LABEL[event.status])}</strong>
              <span>
                {event.occurred_on
                  ? tr("Happened on {date}, as you recorded it", { date: date(event.occurred_on) })
                  : tr("Recorded by you on {date}", { date: date(event.recorded_at) })}
              </span>
              {event.note && <span>{event.note}</span>}
            </li>
          ))}
        </ol>
      </details>

      {action.allowed_next.length > 0 && (
        <form className="act-form" onSubmit={save} aria-label={tr("Record what happened for: {title}", { title: action.title })}>
          <label className="input-label" htmlFor={`${id}-next`}>
            {tr("What happened?")}
          </label>
          <select id={`${id}-next`} className="select-field" value={next} onChange={(e) => setNext(e.target.value as ActionStatus | "")}>
            <option value="">{tr("Choose one…")}</option>
            {action.allowed_next.map((s) => (
              <option key={s} value={s}>
                {tr(EVENT_LABEL[s])}
              </option>
            ))}
          </select>
          {next && (
            <>
              <label className="input-label" htmlFor={`${id}-day`}>
                {needsDay ? tr("Day it happened (required)") : tr("Day it happened (optional)")}
              </label>
              <input id={`${id}-day`} type="date" className="input-field" required={needsDay} value={day} onChange={(e) => setDay(e.target.value)} />
              {asksContact && (
                <>
                  <label className="input-label" htmlFor={`${id}-inst`}>
                    {tr("Who you contacted (optional)")}
                  </label>
                  <input id={`${id}-inst`} className="input-field" maxLength={200} value={institution} onChange={(e) => setInstitution(e.target.value)} />
                  <label className="input-label" htmlFor={`${id}-how`}>
                    {tr("How (optional)")}
                  </label>
                  <select id={`${id}-how`} className="select-field" value={method} onChange={(e) => setMethod(e.target.value as ContactMethod | "")}>
                    <option value="">{tr("Choose one…")}</option>
                    {(Object.keys(CONTACT_LABEL) as ContactMethod[]).map((m) => (
                      <option key={m} value={m}>
                        {tr(CONTACT_LABEL[m])}
                      </option>
                    ))}
                  </select>
                </>
              )}
              {asksAmount && (
                <>
                  <label className="input-label" htmlFor={`${id}-amount`}>
                    {tr("Amount corrected or refunded in rupees (only if it happened)")}
                  </label>
                  <input id={`${id}-amount`} type="number" min="0" step="0.01" inputMode="decimal" className="input-field" value={amount} onChange={(e) => setAmount(e.target.value)} />
                </>
              )}
              <label className="input-label" htmlFor={`${id}-note`}>
                {tr("Notes (optional). Leave out names, phone and ID numbers.")}
              </label>
              <textarea id={`${id}-note`} className="textarea-field" rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
              <button type="submit" className="btn btn-primary btn-compact" disabled={busy}>
                {busy ? tr("Saving…") : tr("Save to your timeline")}
              </button>
            </>
          )}
        </form>
      )}
      {error && (
        <p className="ws-error" role="alert">
          {error}
        </p>
      )}
      <button type="button" className="btn btn-ghost btn-compact" onClick={() => setConfirm(true)}>
        {tr("Remove this step")}
      </button>
      <ConfirmationDialog
        open={confirm}
        onCancel={() => setConfirm(false)}
        onConfirm={remove}
        title={tr("Remove this step?")}
        consequence={tr("The step and its timeline are erased. Your documents and results stay.")}
        confirmLabel={tr("Remove this step")}
        cancelLabel={tr("Cancel")}
        destructive
      />
    </li>
  );
}
