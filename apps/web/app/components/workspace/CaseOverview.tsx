"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { LazyPanel } from "../LazyPanel";
import { EvidenceBadge, StatusBadge } from "../ui/Badges";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { getCaseJson, casePath } from "../../lib/caseApi";
import { WORKSPACE_PATH, moduleHref, type ModuleTab } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { shellCopy } from "../../shell/shellCopy";
import { TransitionLink } from "../../shell/TransitionLink";
import { useCase } from "./CaseProvider";
import { DocumentsKept } from "./DocumentsKept";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { overviewCopy, type OverviewCopy } from "./overviewCopy";
import { fillCopy, formatDateTime, humanizeKey } from "./workspaceFormat";

type WsCopy = CaseCopy & OverviewCopy;

const SafetyEscalationBanner = dynamic(() => import("../clinical/SafetyEscalationBanner").then((m) => m.SafetyEscalationBanner), {
  loading: () => <LazyPanel minHeight="4rem" />,
});
const EntityResolutionReview = dynamic(() => import("../EntityResolutionReview").then((m) => m.EntityResolutionReview), {
  loading: () => <LazyPanel minHeight="4rem" />,
});
const TimelineExplorer = dynamic(() => import("./TimelineExplorer").then((m) => m.TimelineExplorer), {
  loading: () => <LazyPanel minHeight="12rem" />,
});
const EvidenceGraph = dynamic(() => import("./EvidenceGraph").then((m) => m.EvidenceGraph), {
  loading: () => <LazyPanel minHeight="16rem" />,
});

export interface Readiness {
  module_check: string;
  status: "READY" | "NOT_READY" | "BLOCKED_NO_CONSENT";
  auto_run: boolean;
  missing_context: string[];
  description: string;
}

export interface Insight {
  module_check: string;
  status: string;
  trigger: string | null;
  summary: Record<string, unknown> | null;
  missing_context: string[];
  error_id: string | null;
  updated_at: string | null;
}

/** Which workspace page a module check belongs to (from kadi.triggers MODULE_REQUIREMENTS). */
export const CHECK_MODULE: Record<string, ModuleTab> = {
  billnyay_audit: "billnyay",
  billnyay_icd_audit: "billnyay",
  dawacheck_benchmark: "dawacheck",
  schemesetu_eligibility: "schemesetu",
  daavisetu_claim: "daavisetu",
};

/**
 * The open case at a glance (`/app/case`): what to do next (from the API's readiness and the
 * checks it already ran), the documents' extracted details that are kept, the timeline and the
 * evidence graph. Every figure is from a case route; nothing is computed or assumed here.
 */
export function CaseOverview() {
  const [lang] = useLanguage();
  const c = { ...caseCopy[lang], ...overviewCopy[lang] };
  const cs = useCase();

  if (!cs.hydrated || (cs.ref && cs.detailLoading && !cs.detail)) return <LoadingState label={c.common.loading} />;
  if (!cs.ref)
    return (
      <EmptyState
        title={c.module.noCaseTitle}
        action={
          <TransitionLink href={WORKSPACE_PATH} className="btn btn-primary btn-compact">
            {c.module.goToDesk}
          </TransitionLink>
        }
      >
        <p>{c.module.noCaseBody}</p>
      </EmptyState>
    );
  if (cs.problem) return null; // CaseFrame explains it
  if (!cs.ready) return <LoadingState label={c.module.processing} minHeight="10rem" />;

  const ref = cs.ref;
  const token = ref.token ?? undefined;
  const consent = cs.detail?.case.consent_opt_in ?? false;

  return (
    <div className="ws-overview">
      <h1 className="ws-page-title">{c.overview.title}</h1>
      <SafetyEscalationBanner key={`safety-${ref.id}-${cs.version}`} caseId={ref.id} caseToken={token} />
      <InsightsAndActions key={`ins-${ref.id}-${cs.version}`} c={c} lang={lang} consent={consent} />
      <EntityResolutionReview key={`res-${ref.id}-${cs.version}`} caseId={ref.id} caseToken={token} currentLang={lang} />
      {cs.detail && <DocumentsKept c={c} lang={lang} entities={cs.detail.entities} />}
      <TimelineExplorer key={`tl-${ref.id}`} refreshKey={cs.version} />
      <EvidenceGraph key={`graph-${ref.id}-${cs.version}`} />
    </div>
  );
}

function InsightsAndActions({ c, lang, consent }: { c: WsCopy; lang: "en" | "hi" | "mr"; consent: boolean }) {
  const cs = useCase();
  const tabs = shellCopy[lang].tabs;
  const [data, setData] = useState<{ readiness: Readiness[]; insights: Insight[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const ref = cs.ref;

  useEffect(() => {
    if (!ref || !consent) return;
    let cancelled = false;
    getCaseJson<{ readiness: Readiness[]; insights: Insight[] }>(ref, `${casePath(ref.id)}/insights`)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((err: unknown) => !cancelled && setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [ref, consent, tick]);

  return (
    <section className="ws-section" aria-labelledby="ws-actions-title">
      <h2 id="ws-actions-title" className="ws-section-title">
        {c.overview.actionsTitle}
      </h2>
      {!consent ? (
        <div className="ws-prompt" role="note">
          <p className="ws-prompt-title">{c.overview.noConsentTitle}</p>
          <p>{c.overview.noConsentBody}</p>
        </div>
      ) : error ? (
        <ErrorState
          title={c.overview.insightsError}
          action={
            <button type="button" className="btn btn-secondary btn-compact" onClick={() => setTick((n) => n + 1)}>
              {c.common.retry}
            </button>
          }
        >
          <p>{error}</p>
        </ErrorState>
      ) : !data ? (
        <LoadingState label={c.common.loading} minHeight="6rem" />
      ) : (
        <>
          <ul className="ws-actions">
            {data.readiness.map((r) => {
              const mod = CHECK_MODULE[r.module_check];
              const ran = data.insights.find((i) => i.module_check === r.module_check);
              const label = c.checks[r.module_check as keyof WsCopy["checks"]] ?? humanizeKey(r.module_check);
              return (
                <li key={r.module_check} className="ws-action">
                  <div className="ws-action-main">
                    <p className="ws-action-title">{label}</p>
                    <p className="ws-muted">
                      {r.status === "READY"
                        ? ran?.status === "COMPLETED"
                          ? c.overview.ranAutomatically
                          : c.overview.readyToRun
                        : r.status === "BLOCKED_NO_CONSENT"
                          ? c.overview.blockedNoConsent
                          : fillCopy(c.overview.missing, { items: r.missing_context.map(humanizeKey).join(", ") })}
                    </p>
                  </div>
                  <StatusBadge tone={r.status === "READY" ? "success" : r.status === "BLOCKED_NO_CONSENT" ? "danger" : "warning"}>
                    {r.status === "READY" ? c.overview.statusReady : r.status === "BLOCKED_NO_CONSENT" ? c.overview.statusBlocked : c.overview.statusNotReady}
                  </StatusBadge>
                  {mod && (
                    <TransitionLink href={moduleHref(mod)} className="btn btn-secondary btn-compact">
                      {fillCopy(c.overview.openCheck, { check: tabs[mod] })}
                    </TransitionLink>
                  )}
                </li>
              );
            })}
          </ul>

          <h3 className="ws-subtitle">{c.overview.insightsTitle}</h3>
          {data.insights.length === 0 ? (
            <EmptyState title={c.overview.noInsights}>
              <p>{c.overview.noInsightsBody}</p>
            </EmptyState>
          ) : (
            <ul className="ws-insights">
              {data.insights.map((i) => (
                <li key={i.module_check} className="ws-insight">
                  <div className="ws-insight-head">
                    <p className="ws-action-title">{c.checks[i.module_check as keyof WsCopy["checks"]] ?? humanizeKey(i.module_check)}</p>
                    {i.status === "COMPLETED" ? <EvidenceBadge state="rule-engine" size="sm" /> : <StatusBadge tone="warning">{c.overview.couldNotRun}</StatusBadge>}
                  </div>
                  {i.updated_at && <p className="ws-muted">{fillCopy(c.overview.updated, { when: formatDateTime(i.updated_at, lang) })}</p>}
                  <InsightSummary c={c} summary={i.summary} />
                  {i.missing_context.length > 0 && <p className="ws-muted">{fillCopy(c.overview.missing, { items: i.missing_context.map(humanizeKey).join(", ") })}</p>}
                  {i.error_id && <p className="ws-muted">{fillCopy(c.overview.errorRef, { id: i.error_id })}</p>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

/** The plain values of an automatic check's stored summary, exactly as the API stored them. */
function InsightSummary({ c, summary }: { c: WsCopy; summary: Record<string, unknown> | null }) {
  const rows = Object.entries(summary ?? {}).filter(([, v]) => typeof v === "number" || typeof v === "string" || typeof v === "boolean");
  if (rows.length === 0) return null;
  return (
    <>
    <p className="ws-muted">{c.overview.summaryNote}</p>
    <dl className="ws-facts ws-facts-compact" aria-label={c.overview.summaryLabel}>
      {rows.slice(0, 8).map(([k, v]) => (
        <div key={k}>
          <dt>{humanizeKey(k)}</dt>
          <dd className="code-tabular">{typeof v === "boolean" ? (v ? c.common.yes : c.common.no) : String(v)}</dd>
        </div>
      ))}
    </dl>
    </>
  );
}
