"use client";

import React, { useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { accountPaths, passwordProblem, type DeleteAccountResponse, type SessionResponse } from "../../shared/api-client";
import { PasswordField, postAuth, type Outcome, OutcomeMessage } from "../auth/AuthShared";
import { authCopy } from "../auth/authCopy";
import { ConfirmationDialog } from "../ui/Overlays";
import { PageHeader } from "../ui/PageHeader";
import { StatusBadge } from "../ui/Badges";
import { useAccount } from "../../hooks/useAccount";
import { useActiveCase, useGuestCases } from "../../hooks/useCases";
import { setReadAloudEnabled, setSimpleLanguage, useInstalledVoices, useReadAloudEnabled, useSimpleLanguage, useSpeechSupported } from "../../hooks/useListen";
import { useTheme } from "../../hooks/useTheme";
import { deleteCase } from "../../lib/caseApi";
import { clearActiveCase, readActiveCase, removeGuestCase } from "../../lib/caseStore";
import { markSignedIn, markSignedOut } from "../../lib/session";
import { getListenAvailability } from "../../lib/speech";
import { readReducedMotion, setAppReducedMotion, appReducedMotion, subscribeReducedMotion } from "../../motion/useReducedMotion";
import type { Language } from "../../shared/i18n/types";
import { AUTH_PATHS } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { LANGUAGE_LABELS, shellCopy } from "../../shell/shellCopy";
import { TransitionLink } from "../../shell/TransitionLink";
import { caseCopy, type CaseCopy } from "./caseCopy";
import { settingsCopy, type SettingsCopy } from "./settingsCopy";
import { fillCopy, shortCaseId } from "./workspaceFormat";

type WsCopy = CaseCopy & SettingsCopy;

const LANGS: Language[] = ["en", "hi", "mr"];

function useAppReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReducedMotion, appReducedMotion, () => false);
}
function useAnyReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReducedMotion, () => readReducedMotion(), () => false);
}

/**
 * Settings (`/app/settings`): display preferences (kept in this browser only, never sent), the
 * account (change password, delete the account) and deleting the open case.
 */
export function SettingsPage() {
  const [lang, setLang] = useLanguage();
  const c = { ...caseCopy[lang], ...settingsCopy[lang] };
  const { theme, setTheme } = useTheme();
  const simple = useSimpleLanguage();
  const readAloud = useReadAloudEnabled();
  const appMotion = useAppReducedMotion();
  const anyMotion = useAnyReducedMotion();
  const supported = useSpeechSupported();
  const voices = useInstalledVoices();
  const voice = getListenAvailability(supported, voices, lang);

  return (
    <div className="container ws-settings">
      <PageHeader kicker={c.settings.kicker} title={c.settings.title} lede={c.settings.lede} />

      <section className="ws-section" aria-labelledby="ws-prefs-title">
        <h2 id="ws-prefs-title" className="ws-section-title">
          {c.settings.prefsTitle}
        </h2>
        <p className="ws-section-lede">{c.settings.prefsLede}</p>

        <fieldset className="ws-fieldset">
          <legend>{c.settings.language}</legend>
          <div className="ws-radio-row">
            {LANGS.map((l) => (
              <label key={l} className="ws-radio">
                <input type="radio" name="ws-lang" checked={lang === l} onChange={() => setLang(l)} />
                <span lang={l}>{LANGUAGE_LABELS[l]}</span>
              </label>
            ))}
          </div>
          <p className="ws-muted">{c.settings.languageNote}</p>
        </fieldset>

        <fieldset className="ws-fieldset">
          <legend>{c.settings.theme}</legend>
          <div className="ws-radio-row">
            {(["light", "dark"] as const).map((t) => (
              <label key={t} className="ws-radio">
                <input type="radio" name="ws-theme" checked={theme === t} onChange={() => setTheme(t)} />
                <span>{t === "light" ? c.settings.light : c.settings.dark}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="ws-fieldset">
          <legend>{c.settings.reading}</legend>
          <label className="ws-check">
            <input type="checkbox" checked={simple} onChange={(e) => setSimpleLanguage(e.target.checked)} />
            <span>
              <strong>{c.settings.simple}</strong>
              <span className="ws-muted">{c.settings.simpleNote}</span>
            </span>
          </label>
          <label className="ws-check">
            <input type="checkbox" checked={readAloud} onChange={(e) => setReadAloudEnabled(e.target.checked)} />
            <span>
              <strong>{c.settings.readAloud}</strong>
              <span className="ws-muted">
                {voice.status === "ready" ? c.settings.voiceReady : voice.status === "no-local-voice" ? c.settings.voiceMissing : c.settings.voiceUnsupported}
              </span>
            </span>
          </label>
          <label className="ws-check">
            <input type="checkbox" checked={appMotion} onChange={(e) => setAppReducedMotion(e.target.checked)} />
            <span>
              <strong>{c.settings.motion}</strong>
              <span className="ws-muted">{anyMotion && !appMotion ? c.settings.motionSystem : c.settings.motionNote}</span>
            </span>
          </label>
        </fieldset>
      </section>

      <AccountSection c={c} lang={lang} />
      <CaseSection c={c} />
    </div>
  );
}

function AccountSection({ c, lang }: { c: WsCopy; lang: Language }) {
  const account = useAccount();
  const a = authCopy[lang];
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [delPassword, setDelPassword] = useState("");
  const [askDelete, setAskDelete] = useState(false);
  const [delBusy, setDelBusy] = useState(false);
  const [delOutcome, setDelOutcome] = useState<Outcome>(null);
  const [deleted, setDeleted] = useState<number | null>(null);

  if (deleted !== null) {
    return (
      <section className="ws-section" aria-labelledby="ws-account-title">
        <h2 id="ws-account-title" className="ws-section-title">
          {c.settings.accountTitle}
        </h2>
        <OutcomeMessage outcome={{ kind: "success", text: fillCopy(c.settings.deleted, { count: deleted }) }} />
        <p>
          <TransitionLink href="/">{c.settings.home}</TransitionLink>
        </p>
      </section>
    );
  }

  if (account.status !== "signed-in" || !account.user) {
    return (
      <section className="ws-section" aria-labelledby="ws-account-title">
        <h2 id="ws-account-title" className="ws-section-title">
          {c.settings.accountTitle}
        </h2>
        <p className="ws-prompt">
          {account.status === "expired" ? shellCopy[lang].account.sessionEnded : c.settings.signedOut}{" "}
          <TransitionLink href={`${AUTH_PATHS.login}?next=${encodeURIComponent("/app/settings")}`}>{shellCopy[lang].account.signIn}</TransitionLink>
        </p>
      </section>
    );
  }

  const problem = next ? passwordProblem(next, account.user.email) : null;

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (!next || problem || next !== confirm) {
      setOutcome({ kind: "error", text: problem ? a.policy[problem] : !next ? a.policy.too_short : a.mismatch });
      return;
    }
    setBusy(true);
    setOutcome(null);
    const r = await postAuth<SessionResponse>(accountPaths.password, { current_password: current, new_password: next }, a);
    setBusy(false);
    if (r.ok && r.body) {
      // The API revoked every session and issued this browser a fresh cookie.
      markSignedIn(r.body.user);
      setCurrent("");
      setNext("");
      setConfirm("");
      setOutcome({ kind: "success", text: c.settings.passwordChanged });
    } else {
      setOutcome({ kind: "error", text: r.error ?? a.unreachable });
    }
  };

  const deleteAccount = async () => {
    setAskDelete(false);
    setDelBusy(true);
    setDelOutcome(null);
    const r = await postAuth<DeleteAccountResponse>(accountPaths.me, { password: delPassword }, a, "DELETE");
    setDelBusy(false);
    if (r.ok && r.body) {
      setDelPassword("");
      if (readActiveCase()?.owned) clearActiveCase();
      markSignedOut();
      setDeleted(r.body.cases_erased);
      router.refresh();
    } else {
      setDelOutcome({ kind: "error", text: r.error ?? a.unreachable });
    }
  };

  return (
    <section className="ws-section" aria-labelledby="ws-account-title">
      <h2 id="ws-account-title" className="ws-section-title">
        {c.settings.accountTitle}
      </h2>
      <dl className="ws-facts">
        <div>
          <dt>{a.email}</dt>
          <dd>{account.user.email}</dd>
        </div>
        <div>
          <dt>{c.settings.emailStatus}</dt>
          <dd>
            <StatusBadge tone={account.user.email_verified ? "success" : "neutral"}>{account.user.email_verified ? c.settings.verified : c.settings.notVerified}</StatusBadge>{" "}
            {!account.user.email_verified && <TransitionLink href={AUTH_PATHS.verify}>{c.settings.verifyLink}</TransitionLink>}
          </dd>
        </div>
      </dl>

      <form className="auth-form ws-subform" onSubmit={changePassword} aria-labelledby="ws-password-title">
        <h3 id="ws-password-title" className="ws-subtitle">
          {c.settings.passwordTitle}
        </h3>
        <p className="ws-muted">{c.settings.passwordNote}</p>
        <PasswordField lang={lang} label={c.settings.currentPassword} autoComplete="current-password" required maxLength={1024} value={current} onChange={(e) => setCurrent(e.target.value)} />
        <PasswordField
          lang={lang}
          label={a.newPassword}
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={1024}
          hint={a.passwordHint}
          error={next && problem ? a.policy[problem] : null}
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
        <PasswordField
          lang={lang}
          label={a.confirmPassword}
          autoComplete="new-password"
          required
          maxLength={1024}
          error={confirm && confirm !== next ? a.mismatch : null}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
        <OutcomeMessage outcome={outcome} />
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy} aria-busy={busy}>
          {busy ? a.working : c.settings.changePassword}
        </button>
      </form>

      <form
        className="auth-form ws-subform ws-danger-zone"
        aria-labelledby="ws-delete-title"
        onSubmit={(e) => {
          e.preventDefault();
          if (delPassword) setAskDelete(true);
        }}
      >
        <h3 id="ws-delete-title" className="ws-subtitle">
          {c.settings.deleteTitle}
        </h3>
        <p>{c.settings.deleteErases}</p>
        <p className="ws-muted">{c.settings.deleteKeeps}</p>
        <PasswordField lang={lang} label={c.settings.deletePassword} autoComplete="current-password" required maxLength={1024} value={delPassword} onChange={(e) => setDelPassword(e.target.value)} />
        <OutcomeMessage outcome={delOutcome} />
        <button type="submit" className="btn btn-danger-outline auth-submit" disabled={delBusy || !delPassword} aria-busy={delBusy}>
          {delBusy ? a.working : c.settings.deleteAccount}
        </button>
      </form>
      <ConfirmationDialog
        open={askDelete}
        onCancel={() => setAskDelete(false)}
        onConfirm={deleteAccount}
        title={c.settings.deleteConfirmTitle}
        consequence={c.settings.deleteErases}
        confirmLabel={c.settings.deleteAccount}
        cancelLabel={c.common.cancel}
        destructive
      />
    </section>
  );
}

function CaseSection({ c }: { c: WsCopy }) {
  const active = useActiveCase();
  const guests = useGuestCases();
  const [ask, setAsk] = useState(false);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);

  const remove = async () => {
    setAsk(false);
    if (!active) return;
    setBusy(true);
    setOutcome(null);
    try {
      await deleteCase(active);
      if (!active.owned) removeGuestCase(active.id);
      clearActiveCase();
      setOutcome({ kind: "success", text: c.settings.caseDeleted });
    } catch (err) {
      setOutcome({ kind: "error", text: fillCopy(c.frame.deleteFailed, { reason: err instanceof Error ? err.message : "" }) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="ws-section" aria-labelledby="ws-case-settings-title">
      <h2 id="ws-case-settings-title" className="ws-section-title">
        {c.settings.caseTitle}
      </h2>
      <p className="ws-section-lede">{fillCopy(c.settings.guestCount, { count: guests.length })}</p>
      <OutcomeMessage outcome={outcome} />
      {active ? (
        <>
          <p>{fillCopy(c.settings.openCase, { id: shortCaseId(active.id), kind: active.owned ? c.common.owned : c.common.guest })}</p>
          <button type="button" className="btn btn-danger-outline btn-compact" disabled={busy} onClick={() => setAsk(true)}>
            {busy ? c.frame.deleting : c.frame.deleteCase}
          </button>
        </>
      ) : (
        <p className="ws-muted">{c.settings.noOpenCase}</p>
      )}
      <ConfirmationDialog
        open={ask}
        onCancel={() => setAsk(false)}
        onConfirm={remove}
        title={c.frame.deleteTitle}
        consequence={c.frame.deleteConsequence}
        confirmLabel={c.frame.deleteConfirm}
        cancelLabel={c.common.cancel}
        destructive
      />
    </section>
  );
}
