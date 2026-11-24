"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import type { OwnedCaseSummary } from "../../shared/api-client";
import { DocumentUploader } from "../DocumentUploader";
import { DemoBanner, DemoPill, useDemoStatus } from "../demo/DemoBanner";
import { LazyPanel } from "../LazyPanel";
import { StatePanel } from "../clinical/StatePanel";
import { PageHeader } from "../ui/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { StatusBadge } from "../ui/Badges";
import { useAccount } from "../../hooks/useAccount";
import { useGuestCases } from "../../hooks/useCases";
import { CaseApiError, claimCase, createCase, fetchCaseDetail, listOwnedCases, uploadDocument, type CaseSummary } from "../../lib/caseApi";
import { addGuestCase, removeGuestCase, setActiveCase, type GuestCase } from "../../lib/caseStore";
import type { DemoScenarioResult } from "../../lib/demo";
import { AUTH_PATHS, CASE_PATH, MODULE_ORDER, moduleFromHash, moduleHref } from "../../shell/nav";
import { useHeaderSlot, useLanguage } from "../../shell/ShellProvider";
import { shellCopy } from "../../shell/shellCopy";
import { TransitionLink } from "../../shell/TransitionLink";
import { uploadCopy } from "../../lib/uploadCopy";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { deskCopy, type DeskCopy } from "./deskCopy";
import { fillCopy, formatDate, formatRupees, shortCaseId } from "./workspaceFormat";

type WsCopy = CaseCopy & DeskCopy;

const DemoControls = dynamic(() => import("../demo/DemoControls").then((m) => m.DemoControls), {
  loading: () => <LazyPanel minHeight="10rem" />,
});

/**
 * The case desk (`/app`). Signed in: the account's cases from the server (GET /kadi/cases). Guest:
 * the cases this browser tab holds (sessionStorage, decision D2), with a prompt to sign in and,
 * once signed in, a "keep in my account" claim for each. Starting a case creates it (owned when
 * signed in) and opens it in the workspace; the case never goes into the URL.
 */
// Shortcut blurbs (transformation M8). English only for now: hi/mr need native-speaker copy, so the
// elements carry lang="en" in the other languages rather than an unreviewed translation.
const SHORTCUT_BLURB: Record<(typeof MODULE_ORDER)[number], string> = {
  billnyay: "CGHS line-by-line bill check, ICD-10 consistency hint and appeal draft",
  daavisetu: "Pre-authorisation readiness and Annexure-B package",
  bimanyay: "IRDAI denial clause check, three-tier appeal drafts and deadlines",
  schemesetu: "Provisional PM-JAY and MJPJAY eligibility with citations",
  dawacheck: "Per-unit NPPA ceiling check and prescription shorthand",
};

export function CaseDesk({ intakeBg, intakeArt }: { intakeBg?: React.ReactNode; intakeArt?: React.ReactNode } = {}) {
  const [lang] = useLanguage();
  const c = { ...caseCopy[lang], ...deskCopy[lang] };
  const upload = uploadCopy[lang];
  const router = useRouter();
  const account = useAccount();
  const guests = useGuestCases();
  const demoStatus = useDemoStatus();
  useHeaderSlot(useMemo(() => <DemoPill status={demoStatus} />, [demoStatus]));
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const signedIn = account.status === "signed-in";

  // Old links (`/app#module-<id>`) open that check on its own page now.
  useEffect(() => {
    const m = moduleFromHash(window.location.hash);
    if (m) router.replace(moduleHref(m));
  }, [router]);

  const open = useCallback(
    (id: string, owned: boolean) => {
      setActiveCase({ id, owned });
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
      if (!ref.owned && ref.token) addGuestCase({ id: ref.id, token: ref.token });
      setActiveCase({ id: ref.id, owned: ref.owned });
      await uploadDocument(ref, file);
      router.push(CASE_PATH);
    } catch (err) {
      setStartError(fillCopy(c.desk.startFailed, { reason: err instanceof Error ? err.message : "" }));
    } finally {
      setStarting(false);
    }
  };

  // Demo kit: a scenario arrives as an already-processed guest case.
  const onScenarioLoaded = (result: DemoScenarioResult) => {
    addGuestCase({ id: result.case_id, token: result.access_token });
    open(result.case_id, false);
  };

  return (
    <>
      <div className="lp-backdrop" aria-hidden="true" />
      <div className="container ws-desk">
        <DemoBanner status={demoStatus} />
        <PageHeader kicker={c.desk.kicker} title={c.desk.title} lede={c.desk.lede} />

        {demoStatus?.demo_mode && <DemoControls status={demoStatus} onScenarioLoaded={onScenarioLoaded} onReset={() => undefined} />}

        <section id="intake-dropzone" className="ws-section lp-intake ws-kadi-hero" aria-labelledby="ws-start-title">
          {intakeBg}
          <div className="ws-kadi-hero-copy">
            <h2 id="ws-start-title" className="ws-section-title">
              {c.desk.startTitle}
            </h2>
            <p className="ws-section-lede">{signedIn ? c.desk.startOwned : c.desk.startGuest}</p>
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
          <h2 id="ws-shortcuts-title" className="ws-section-title" lang={lang === "en" ? undefined : "en"}>
            Standalone &amp; case tools
          </h2>
          <p className="ws-section-lede" lang={lang === "en" ? undefined : "en"}>
            Open any module directly. BillNyay and DaaviSetu work on an uploaded case; BimaNyay, DawaCheck, and SchemeSetu also work without uploading a document.
          </p>
          <ul className="ws-shortcuts">
            {MODULE_ORDER.map((id) => (
              <li key={id}>
                <TransitionLink href={moduleHref(id)} className={`ws-shortcut-card ws-mod-${id}`}>
                  <strong>{shellCopy[lang].tabs[id]}</strong>
                  <span lang={lang === "en" ? undefined : "en"}>{SHORTCUT_BLURB[id]}</span>
                </TransitionLink>
              </li>
            ))}
          </ul>
        </section>

        <section className="ws-section" aria-labelledby="ws-cases-title">
          <h2 id="ws-cases-title" className="ws-section-title">
            {c.desk.casesTitle}
          </h2>
          {signedIn ? <OwnedCases c={c} lang={lang} onOpen={(id) => open(id, true)} /> : <SignInPrompt c={c} lang={lang} expired={account.status === "expired"} />}
          {(guests.length > 0 || !signedIn) && (
            <GuestCases c={c} lang={lang} guests={guests} signedIn={signedIn} onOpen={(id) => open(id, false)} />
          )}
        </section>
      </div>
    </>
  );
}

function SignInPrompt({ c, lang, expired }: { c: WsCopy; lang: keyof typeof shellCopy; expired: boolean }) {
  const a = shellCopy[lang].account;
  return (
    <div className="ws-prompt" role="note">
      <p className="ws-prompt-title">{expired ? a.sessionEnded : c.desk.keepTitle}</p>
      <p>{c.desk.keepBody}</p>
      <p className="ws-prompt-actions">
        <TransitionLink href={AUTH_PATHS.login} className="btn btn-primary btn-compact">
          {a.signIn}
        </TransitionLink>
        <TransitionLink href={AUTH_PATHS.register} className="btn btn-secondary btn-compact">
          {a.register}
        </TransitionLink>
      </p>
    </div>
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

function GuestCases({ c, lang, guests, signedIn, onOpen }: { c: WsCopy; lang: keyof typeof shellCopy; guests: GuestCase[]; signedIn: boolean; onOpen: (id: string) => void }) {
  return (
    <div className="ws-guest">
      <h3 className="ws-subtitle">{c.desk.guestTitle}</h3>
      <p className="ws-section-lede">{c.desk.guestNote}</p>
      {guests.length === 0 ? (
        <EmptyState title={c.desk.noGuestCases}>
          <p>{c.desk.noGuestCasesBody}</p>
        </EmptyState>
      ) : (
        <ul className="ws-case-list" aria-label={c.desk.guestListLabel}>
          {guests.map((g) => (
            <GuestCaseRow key={g.id} c={c} lang={lang} guest={g} signedIn={signedIn} onOpen={onOpen} />
          ))}
        </ul>
      )}
    </div>
  );
}

function GuestCaseRow({ c, lang, guest, signedIn, onOpen }: { c: WsCopy; lang: keyof typeof shellCopy; guest: GuestCase; signedIn: boolean; onOpen: (id: string) => void }) {
  const [summary, setSummary] = useState<CaseSummary | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "gone" | "claimed-elsewhere" | "error">("loading");
  const [claiming, setClaiming] = useState(false);
  const [claimError, setClaimError] = useState<string | null>(null);
  const ref = useMemo(() => ({ id: guest.id, token: guest.token, owned: false }), [guest.id, guest.token]);

  useEffect(() => {
    let cancelled = false;
    fetchCaseDetail(ref)
      .then((d) => {
        if (cancelled) return;
        setSummary(d.case);
        setStatus("ok");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const s = err instanceof CaseApiError ? err.status : 0;
        // 404: deleted or expired. 403: the token no longer opens it (it was moved into an account).
        setStatus(s === 404 ? "gone" : s === 403 ? "claimed-elsewhere" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [ref]);

  const claim = async () => {
    setClaiming(true);
    setClaimError(null);
    try {
      await claimCase(guest.id, guest.token);
      // The case token stops working now; the account's session opens the case from here on.
      removeGuestCase(guest.id);
      window.dispatchEvent(new Event("arogya:case-claimed"));
    } catch (err) {
      setClaimError(err instanceof Error ? err.message : String(err));
    } finally {
      setClaiming(false);
    }
  };

  const title = fillCopy(c.frame.caseTitle, { id: shortCaseId(guest.id) });
  return (
    <li className="ws-case-row">
      <div className="ws-case-row-main">
        <p className="ws-case-row-title">
          {title} <StatusBadge tone="info">{c.common.guest}</StatusBadge>
        </p>
        {status === "loading" && <p className="ws-muted">{c.common.loading}</p>}
        {status === "ok" && summary && <CaseFacts c={c} lang={lang} summary={summary} />}
        {status === "gone" && <p className="ws-muted">{c.desk.guestGone}</p>}
        {status === "claimed-elsewhere" && <p className="ws-muted">{c.desk.guestRefused}</p>}
        {status === "error" && <p className="ws-muted">{c.desk.guestError}</p>}
        {claimError && (
          <p className="ws-error" role="alert">
            {claimError}
          </p>
        )}
      </div>
      <div className="ws-case-row-actions">
        {status === "ok" && (
          <button type="button" className="btn btn-primary btn-compact" onClick={() => onOpen(guest.id)} aria-label={fillCopy(c.desk.openAria, { id: shortCaseId(guest.id) })}>
            {c.desk.open}
          </button>
        )}
        {status === "ok" && signedIn && (
          <button type="button" className="btn btn-secondary btn-compact" onClick={claim} disabled={claiming} aria-label={fillCopy(c.desk.claimAria, { id: shortCaseId(guest.id) })}>
            {claiming ? c.desk.claiming : c.desk.claim}
          </button>
        )}
        {(status === "gone" || status === "claimed-elsewhere" || status === "error") && (
          <button type="button" className="btn btn-secondary btn-compact" onClick={() => removeGuestCase(guest.id)}>
            {c.desk.forget}
          </button>
        )}
      </div>
    </li>
  );
}
