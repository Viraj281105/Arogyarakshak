"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { DemoAccountNote } from "../auth/DemoAccountNote";
import type { OwnedCaseSummary } from "../../shared/api-client";
import { DocumentUploader } from "../DocumentUploader";
import { DemoBanner, DemoPill, useDemoStatus } from "../demo/DemoBanner";
import { LazyPanel } from "../LazyPanel";
import { StatePanel } from "../clinical/StatePanel";
import { PageHeader } from "../ui/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { StatusBadge } from "../ui/Badges";
import { useGuestCases } from "../../hooks/useCases";
import { CaseApiError, claimCase, createCase, listOwnedCases, uploadDocument, type CaseSummary } from "../../lib/caseApi";
import { removeGuestCase, setActiveCase, type GuestCase } from "../../lib/caseStore";
import type { DemoScenarioResult } from "../../lib/demo";
import { CASE_PATH, MODULE_ORDER, moduleFromHash, moduleHref } from "../../shell/nav";
import { useHeaderSlot, useLanguage } from "../../shell/ShellProvider";
import { shellCopy } from "../../shell/shellCopy";
import { TransitionLink } from "../../shell/TransitionLink";
import { uploadCopy } from "../../lib/uploadCopy";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { deskCopy, type DeskCopy } from "./deskCopy";
import { fillCopy, formatDate, formatRupees, shortCaseId } from "./workspaceFormat";
import { useT } from "../../i18n/useT";
import { msg } from "../../i18n/format";

type WsCopy = CaseCopy & DeskCopy;

const DemoControls = dynamic(() => import("../demo/DemoControls").then((m) => m.DemoControls), {
  loading: () => <LazyPanel minHeight="10rem" />,
});

/**
 * The case desk (`/app`, signed-in accounts only): the account's cases from the server
 * (GET /kadi/cases). A tab that still holds the key of a case started before sign-in was
 * required can move it into the account. Starting a case creates it and opens it in the
 * workspace; the case never goes into the URL.
 */
// Shortcut blurbs (transformation M8).
const SHORTCUT_BLURB: Record<(typeof MODULE_ORDER)[number], string> = {
  billnyay: msg("CGHS line-by-line bill check, ICD-10 consistency hint and appeal draft"),
  daavisetu: msg("Pre-authorisation readiness and Annexure-B package"),
  bimanyay: msg("IRDAI denial clause check, three-tier appeal drafts and deadlines"),
  schemesetu: msg("Provisional PM-JAY and MJPJAY eligibility with citations"),
  dawacheck: msg("Per-unit NPPA ceiling check and prescription shorthand"),
};

export function CaseDesk({ intakeBg, intakeArt }: { intakeBg?: React.ReactNode; intakeArt?: React.ReactNode } = {}) {
  const tr = useT();
  const [lang] = useLanguage();
  const c = { ...caseCopy[lang], ...deskCopy[lang] };
  const upload = uploadCopy[lang];
  const router = useRouter();
  const guests = useGuestCases();
  const demoStatus = useDemoStatus();
  useHeaderSlot(useMemo(() => <DemoPill status={demoStatus} />, [demoStatus]));
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // Old links (`/app#module-<id>`) open that check on its own page now.
  useEffect(() => {
    const m = moduleFromHash(window.location.hash);
    if (m) router.replace(moduleHref(m));
  }, [router]);

  const open = useCallback(
    (id: string) => {
      setActiveCase({ id, owned: true });
      router.push(CASE_PATH);
    },
    [router],
  );

  const onStart = async (file: File | null, ...[, consent]: [string, boolean]) => {
    if (!file) return setStartError(upload.consentRequired);
    if (!consent) return setStartError(upload.consentRequired);
    setStarting(true);
    setStartError(null);
    try {
      const ref = await createCase(consent);
      setActiveCase({ id: ref.id, owned: ref.owned });
      await uploadDocument(ref, file);
      router.push(CASE_PATH);
    } catch (err) {
      setStartError(fillCopy(c.desk.startFailed, { reason: err instanceof Error ? err.message : "" }));
    } finally {
      setStarting(false);
    }
  };

  // Demo kit: a scenario arrives as an already-processed case in the signed-in account.
  const onScenarioLoaded = (result: DemoScenarioResult) => open(result.case_id);

  return (
    <>
      <div className="lp-backdrop" aria-hidden="true" />
      <div className="container ws-desk">
        <DemoBanner status={demoStatus} />
        <PageHeader kicker={c.desk.kicker} title={c.desk.title} lede={c.desk.lede} />
        <DemoAccountNote className="ws-warning" />

        {demoStatus?.demo_mode && <DemoControls status={demoStatus} onScenarioLoaded={onScenarioLoaded} onReset={() => undefined} />}

        <section id="intake-dropzone" className="ws-section lp-intake ws-kadi-hero" aria-labelledby="ws-start-title">
          {intakeBg}
          <div className="ws-kadi-hero-copy">
            <h2 id="ws-start-title" className="ws-section-title">
              {c.desk.startTitle}
            </h2>
            <p className="ws-section-lede">{c.desk.startOwned}</p>
            <DocumentUploader currentLang={lang} onStartAudit={onStart} isProcessing={starting} />
            {startError && <StatePanel kind="error">{startError}</StatePanel>}
          </div>
          {intakeArt && (
            <div className="ws-kadi-hero-art" aria-hidden="true">
              {intakeArt}
            </div>
          )}
        </section>

        <section className="ws-section" aria-labelledby="ws-shortcuts-title">
          <h2 id="ws-shortcuts-title" className="ws-section-title">{tr("Standalone & case tools")}</h2>
          <p className="ws-section-lede">{tr("Open any module directly. BillNyay and DaaviSetu work on an uploaded case; BimaNyay, DawaCheck, and SchemeSetu also work without uploading a document.")}</p>
          <ul className="ws-shortcuts">
            {MODULE_ORDER.map((id) => (
              <li key={id}>
                <TransitionLink href={moduleHref(id)} className={`ws-shortcut-card ws-mod-${id}`}>
                  <strong>{shellCopy[lang].tabs[id]}</strong>
                  <span>{tr(SHORTCUT_BLURB[id])}</span>
                </TransitionLink>
              </li>
            ))}
          </ul>
        </section>

        <section className="ws-section" aria-labelledby="ws-cases-title">
          <h2 id="ws-cases-title" className="ws-section-title">
            {c.desk.casesTitle}
          </h2>
          <OwnedCases c={c} lang={lang} onOpen={open} />
          {guests.length > 0 && <OlderCases c={c} guests={guests} />}
        </section>
      </div>
    </>
  );
}

function OwnedCases({ c, lang, onOpen }: { c: WsCopy; lang: keyof typeof shellCopy; onOpen: (id: string) => void }) {
  const [state, setState] = useState<{ loading: boolean; cases: OwnedCaseSummary[] | null; error: string | null }>({ loading: true, cases: null, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listOwnedCases()
      .then((cases) => !cancelled && setState({ loading: false, cases, error: null }))
      .catch((err: unknown) => !cancelled && setState({ loading: false, cases: null, error: err instanceof Error ? err.message : String(err) }));
    return () => {
      cancelled = true;
    };
  }, [tick]);

  // A claim elsewhere on this page adds a case to the account.
  useEffect(() => {
    const onClaimed = () => setTick((n) => n + 1);
    window.addEventListener("arogya:case-claimed", onClaimed);
    return () => window.removeEventListener("arogya:case-claimed", onClaimed);
  }, []);

  if (state.loading && !state.cases) return <LoadingState label={c.desk.loadingCases} minHeight="6rem" />;
  if (state.error)
    return (
      <ErrorState
        title={c.desk.casesError}
        action={
          <button type="button" className="btn btn-secondary btn-compact" onClick={() => setTick((n) => n + 1)}>
            {c.common.retry}
          </button>
        }
      >
        <p>{state.error}</p>
      </ErrorState>
    );
  if (!state.cases || state.cases.length === 0)
    return (
      <EmptyState title={c.desk.noOwnedCases}>
        <p>{c.desk.noOwnedCasesBody}</p>
      </EmptyState>
    );

  return (
    <ul className="ws-case-list" aria-label={c.desk.ownedListLabel}>
      {state.cases.map((k) => (
        <li key={k.id} className="ws-case-row">
          <div className="ws-case-row-main">
            <p className="ws-case-row-title">
              {fillCopy(c.frame.caseTitle, { id: shortCaseId(k.id) })} <StatusBadge tone="success">{c.common.owned}</StatusBadge>
            </p>
            <CaseFacts c={c} lang={lang} summary={{ ...k, created_at: k.created_at ?? null }} expiresAt={k.expires_at ?? null} />
          </div>
          <button type="button" className="btn btn-primary btn-compact" onClick={() => onOpen(k.id)} aria-label={fillCopy(c.desk.openAria, { id: shortCaseId(k.id) })}>
            {c.desk.open}
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Figures for one case, each straight from the API; the billed total is labelled as read from documents. */
function CaseFacts({ c, lang, summary, expiresAt }: { c: WsCopy; lang: keyof typeof shellCopy; summary: Pick<CaseSummary, "created_at" | "total_charged" | "consent_opt_in" | "status">; expiresAt?: string | null }) {
  return (
    <dl className="ws-facts">
      {summary.created_at && (
        <div>
          <dt>{c.desk.started}</dt>
          <dd>{formatDate(summary.created_at, lang)}</dd>
        </div>
      )}
      <div>
        <dt>{c.desk.billedTotal}</dt>
        <dd className="code-tabular">{summary.total_charged > 0 ? formatRupees(summary.total_charged, lang) : c.desk.noBillLines}</dd>
      </div>
      <div>
        <dt>{c.desk.consent}</dt>
        <dd>{summary.consent_opt_in ? c.desk.consentYes : c.desk.consentNo}</dd>
      </div>
      {expiresAt && (
        <div>
          <dt>{c.desk.expires}</dt>
          <dd>{formatDate(expiresAt, lang)}</dd>
        </div>
      )}
    </dl>
  );
}

/** Cases created before mandatory sign-in: their key in this tab can only claim them. */
function OlderCases({ c, guests }: { c: WsCopy; guests: GuestCase[] }) {
  return (
    <div className="ws-guest">
      <h3 className="ws-subtitle">{c.desk.guestTitle}</h3>
      <p className="ws-section-lede">{c.desk.guestNote}</p>
      <ul className="ws-case-list" aria-label={c.desk.guestListLabel}>
        {guests.map((g) => (
          <OlderCaseRow key={g.id} c={c} guest={g} />
        ))}
      </ul>
    </div>
  );
}

function OlderCaseRow({ c, guest }: { c: WsCopy; guest: GuestCase }) {
  const [claiming, setClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const claim = async () => {
    setClaiming(true);
    setError(null);
    try {
      await claimCase(guest.id, guest.token);
      // The case key stops working now; the account's session opens the case from here on.
      removeGuestCase(guest.id);
      window.dispatchEvent(new Event("arogya:case-claimed"));
    } catch (err) {
      const status = err instanceof CaseApiError ? err.status : 0;
      // 404: deleted or expired. 403: the key no longer opens it.
      setError(status === 404 ? c.desk.guestGone : status === 403 ? c.desk.guestRefused : err instanceof Error ? err.message : c.desk.guestError);
    } finally {
      setClaiming(false);
    }
  };

  const id = shortCaseId(guest.id);
  return (
    <li className="ws-case-row">
      <div className="ws-case-row-main">
        <p className="ws-case-row-title">
          {fillCopy(c.frame.caseTitle, { id })} <StatusBadge tone="info">{c.common.guest}</StatusBadge>
        </p>
        {error && (
          <p className="ws-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <div className="ws-case-row-actions">
        <button type="button" className="btn btn-primary btn-compact" onClick={claim} disabled={claiming} aria-label={fillCopy(c.desk.claimAria, { id })}>
          {claiming ? c.desk.claiming : c.desk.claim}
        </button>
        <button type="button" className="btn btn-secondary btn-compact" onClick={() => removeGuestCase(guest.id)}>
          {c.desk.forget}
        </button>
      </div>
    </li>
  );
}
