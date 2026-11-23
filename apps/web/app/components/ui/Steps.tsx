import React from "react";
import Check from "lucide-react/icons/check";
import Circle from "lucide-react/icons/circle";
import CircleAlert from "lucide-react/icons/circle-alert";
import CircleDashed from "lucide-react/icons/circle-dashed";

/**
 * Step indicator for multi-step flows (e.g. DaaviSetu readiness -> template -> package). Each
 * step's state is stated in words for screen readers; aria-current marks the current step. The
 * caller owns navigation (buttons in `children`), so this stays a Server-safe component.
 */
export function StepWizard({
  steps,
  current,
  label = "Progress",
  children,
}: {
  steps: readonly { id: string; label: string }[];
  /** Index of the current step. */
  current: number;
  label?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="ui-wizard">
      <ol className="ui-steps" aria-label={label}>
        {steps.map((s, i) => {
          const state = i < current ? "done" : i === current ? "current" : "upcoming";
          return (
            <li key={s.id} className={`ui-step ui-step-${state}`} aria-current={state === "current" ? "step" : undefined}>
              <span className="ui-step-marker" aria-hidden="true">
                {state === "done" ? <Check size={14} /> : i + 1}
              </span>
              <span className="ui-step-label">{s.label}</span>
              <span className="sr-only">{state === "done" ? " (completed)" : state === "current" ? " (current step)" : " (not started)"}</span>
            </li>
          );
        })}
      </ol>
      <p className="ui-wizard-count">
        Step {Math.min(current + 1, steps.length)} of {steps.length}
      </p>
      {children && <div className="ui-wizard-body">{children}</div>}
    </div>
  );
}

export type ChecklistStatus = "done" | "todo" | "blocked" | "unknown";

const STATUS_WORD: Record<ChecklistStatus, string> = {
  done: "Done",
  todo: "To do",
  blocked: "Blocked",
  unknown: "Not checked",
};

const STATUS_ICON = { done: Check, todo: Circle, blocked: CircleAlert, unknown: CircleDashed } as const;

/** Read-only checklist (e.g. pre-authorisation readiness). Every item states its status in words. */
export function Checklist({
  title,
  items,
}: {
  title: string;
  items: readonly { id: string; label: string; status: ChecklistStatus; note?: string }[];
}) {
  const done = items.filter((i) => i.status === "done").length;
  return (
    <section className="ui-checklist" aria-label={title}>
      <header className="ui-checklist-head">
        <h3>{title}</h3>
        <span className="code-tabular">
          {done} of {items.length} done
        </span>
      </header>
      <ul>
        {items.map((it) => {
          const Icon = STATUS_ICON[it.status];
          return (
            <li key={it.id} className={`ui-check ui-check-${it.status}`}>
              <Icon size={16} aria-hidden="true" />
              <span className="ui-check-label">{it.label}</span>
              <span className="ui-check-status">{STATUS_WORD[it.status]}</span>
              {it.note && <span className="ui-check-note">{it.note}</span>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
