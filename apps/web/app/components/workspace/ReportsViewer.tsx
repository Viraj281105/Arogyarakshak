"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Download from "lucide-react/icons/download";
import { LazyPanel } from "../LazyPanel";
import { EvidenceBadge } from "../ui/Badges";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { CaseApiError, casePath, downloadCaseFile, getCaseJson } from "../../lib/caseApi";
import type { CaseRef } from "../../lib/caseStore";
import { WORKSPACE_PATH, moduleHref } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { TransitionLink } from "../../shell/TransitionLink";
import { useCase } from "./CaseProvider";
import type { TimelineResponse } from "./TimelineExplorer";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { reportsCopy, type ReportsCopy } from "./reportsCopy";
import { fillCopy } from "./workspaceFormat";
import { useT } from "../../i18n/useT";

type WsCopy = CaseCopy & ReportsCopy;

const ClaimPackPanel = dynamic(() => import("../ClaimPackPanel").then((m) => m.ClaimPackPanel), {
  loading: () => <LazyPanel minHeight="10rem" />,
});

interface AppealVerify {
  sha256_hash: string;
  hash_matches_stored_bytes: boolean;
  signature_valid: boolean;
  note: string;
}

type Availability<T = undefined> = { state: "loading" } | { state: "available"; data?: T } | { state: "absent" } | { state: "no-consent" } | { state: "error"; message: string };

/**
 * Report viewer (`/app/case/reports`): the files that exist for THIS case, each fetched as bytes
 * with the case token header or the session cookie (never a credential in a link). Availability
 * comes from the API: the appeal from GET .../appeal/verify (409 = not drafted), the pre-auth
 * form from the case timeline's "claim" step (the claim row exists), the Claim Pack whenever the
 * case consented to cross-module use.
 */
export function ReportsViewer({ heroArt }: { heroArt?: React.ReactNode } = {}) {
  const [lang] = useLanguage();
  const c = { ...caseCopy[lang], ...reportsCopy[lang] };
  const cs = useCase();

  if (!cs.hydrated || (cs.ref && !cs.detail && !cs.problem)) return <LoadingState label={c.common.loading} />;
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
        <p>{c.reports.noCase}</p>
      </EmptyState>
    );
  if (cs.problem) return null;
  if (!cs.ready) return <LoadingState label={c.module.processing} />;
  return <Reports key={`${cs.ref.id}-${cs.version}`} c={c} caseRef={cs.ref} consent={cs.detail?.case.consent_opt_in ?? false} heroArt={heroArt} />;
}

function Reports({ c, caseRef, consent, heroArt }: { c: WsCopy; caseRef: CaseRef; consent: boolean; heroArt?: React.ReactNode }) {
  const tr = useT();
  const [appealState, setAppeal] = useState<Availability<AppealVerify>>({ state: "loading" });
  const [claimState, setClaim] = useState<Availability>({ state: "loading" });
  // Without cross-module consent the API refuses these routes (403), so they are not asked.
  const appeal: Availability<AppealVerify> = consent ? appealState : { state: "no-consent" };
  const claim: Availability = consent ? claimState : { state: "no-consent" };

  useEffect(() => {
    if (!consent) return;
    let cancelled = false;
    getCaseJson<AppealVerify>(caseRef, `/api/v1/billnyay/cases/${encodeURIComponent(caseRef.id)}/appeal/verify`)
      .then((d) => !cancelled && setAppeal({ state: "available", data: d }))
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof CaseApiError && err.status === 409) setAppeal({ state: "absent" });
        else setAppeal({ state: "error", message: err instanceof Error ? err.message : String(err) });
      });
    getCaseJson<TimelineResponse>(caseRef, `${casePath(caseRef.id)}/timeline`)
      .then((t) => !cancelled && setClaim(t.events.some((e) => e.kind === "claim") ? { state: "available" } : { state: "absent" }))
      .catch((err: unknown) => !cancelled && setClaim({ state: "error", message: err instanceof Error ? err.message : String(err) }));
    return () => {
      cancelled = true;
    };
  }, [caseRef, consent]);

  const id = encodeURIComponent(caseRef.id);
  return (
    <div className="ws-reports">
      <header className="ws-mod-hero ws-mod-kadi">
        <div className="ws-mod-hero-copy">
          <p className="ui-kicker">{tr("Case reports & packages")}</p>
          <h1 className="ws-page-title">{c.reports.title}</h1>
          <p className="ws-section-lede">{c.reports.lede}</p>
        </div>
        {heroArt && (
          <div className="ws-mod-hero-art" aria-hidden="true">
            {heroArt}
          </div>
        )}
      </header>

      <ReportCard
        c={c}
        title={c.reports.appealTitle}
        description={c.reports.appealBody}
        availability={appeal}
        absentText={c.reports.appealAbsent}
        absentLink={{ href: moduleHref("billnyay"), label: c.reports.openBillNyay }}
        downloads={[{ label: c.reports.downloadPdf, path: `/api/v1/billnyay/cases/${id}/appeal/pdf`, filename: `appeal_${caseRef.id}.pdf` }]}
        caseRef={caseRef}
      >
        {appeal.state === "available" && appeal.data && <AppealVerification c={c} v={appeal.data} />}
      </ReportCard>

      <ReportCard
        c={c}
        title={c.reports.claimTitle}
        description={c.reports.claimBody}
        availability={claim}
        absentText={c.reports.claimAbsent}
        absentLink={{ href: moduleHref("daavisetu"), label: c.reports.openDaaviSetu }}
        downloads={[
          { label: c.reports.downloadPdf, path: `/api/v1/daavisetu/cases/${id}/claim/pdf`, filename: `preauth_${caseRef.id}.pdf` },
          { label: c.reports.downloadPackage, path: `/api/v1/daavisetu/cases/${id}/claim/package`, filename: `claim_package_${caseRef.id}.zip` },
        ]}
        caseRef={caseRef}
      />

      <section className="ws-section" aria-labelledby="ws-pack-title">
        <h2 id="ws-pack-title" className="ws-section-title">
          {c.reports.packTitle}
        </h2>
        <p className="ws-section-lede">{c.reports.packBody}</p>
        {consent ? <ClaimPackPanel caseId={caseRef.id} caseToken={caseRef.token ?? undefined} /> : <p className="ws-prompt">{c.reports.noConsent}</p>}
      </section>
    </div>
  );
}

function ReportCard({
  c,
  title,
  description,
  availability,
  absentText,
  absentLink,
  downloads,
  caseRef,
  children,
}: {
  c: WsCopy;
  title: string;
  description: string;
  availability: Availability<unknown>;
  absentText: string;
  absentLink: { href: string; label: string };
  downloads: { label: string; path: string; filename: string }[];
  caseRef: CaseRef;
  children?: React.ReactNode;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const download = async (d: { path: string; filename: string }) => {
    setBusy(d.path);
    setError(null);
    try {
      await downloadCaseFile(caseRef, d.path, d.filename);
    } catch (err) {
      setError(fillCopy(c.reports.downloadFailed, { reason: err instanceof Error ? err.message : "" }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="ws-section ws-report" aria-label={title}>
      <h2 className="ws-section-title">{title}</h2>
      <p className="ws-section-lede">{description}</p>
      {availability.state === "loading" && <LoadingState label={c.common.loading} minHeight="4rem" />}
      {availability.state === "no-consent" && <p className="ws-prompt">{c.reports.noConsent}</p>}
      {availability.state === "absent" && (
        <div className="ws-prompt">
          <p>{absentText}</p>
          <p>
            <TransitionLink href={absentLink.href}>{absentLink.label}</TransitionLink>
          </p>
        </div>
      )}
      {availability.state === "error" && (
        <ErrorState title={c.reports.checkFailed}>
          <p>{availability.message}</p>
        </ErrorState>
      )}
      {availability.state === "available" && (
        <>
          <div className="ws-report-actions">
            {downloads.map((d) => (
              <button key={d.path} type="button" className="btn btn-primary btn-compact" onClick={() => download(d)} disabled={busy !== null}>
                <Download size={16} aria-hidden="true" />
                {busy === d.path ? c.reports.downloading : d.label}
              </button>
            ))}
          </div>
          {children}
        </>
      )}
      {error && (
        <p className="ws-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function AppealVerification({ c, v }: { c: WsCopy; v: AppealVerify }) {
  const tr = useT();
  const intact = v.hash_matches_stored_bytes && v.signature_valid;
  return (
    <div className="ws-verify">
      <p className="ws-action-title">
        {c.reports.verifyTitle} <EvidenceBadge state={intact ? "verified" : "insufficient-evidence"} size="sm" />
      </p>
      <dl className="ws-facts ws-facts-compact">
        <div>
          <dt>{c.reports.hashMatches}</dt>
          <dd>{v.hash_matches_stored_bytes ? c.common.yes : c.common.no}</dd>
        </div>
        <div>
          <dt>{c.reports.signatureValid}</dt>
          <dd>{v.signature_valid ? c.common.yes : c.common.no}</dd>
        </div>
        <div className="ws-facts-wide">
          <dt>{tr("SHA-256")}</dt>
          <dd className="ws-hash">{v.sha256_hash}</dd>
        </div>
      </dl>
      <p className="ws-muted" lang="en">
        {v.note}
      </p>
    </div>
  );
}
