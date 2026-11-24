"use client";

import React, { useState } from "react";
import { accountPaths, type AcceptedResponse } from "../../shared/api-client";
import { useAccount } from "../../hooks/useAccount";
import { refreshAccount } from "../../lib/session";
import { useLanguage } from "../../shell/ShellProvider";
import { AuthCard, EmailUnavailableNotice, OutcomeMessage, TextField, postAuth, useFragmentToken, type Outcome } from "./AuthShared";
import { authCopy, fillCopy } from "./authCopy";

/**
 * Email verification with the one-time code from a link (`/verify#token=...`). Confirming is an
 * explicit button press, never automatic on page load. Asking for a new link is possible, but the
 * page says first that this server cannot send email.
 */
export function VerifyEmailForm() {
  const [lang] = useLanguage();
  const c = authCopy[lang];
  const account = useAccount();
  const linkToken = useFragmentToken();
  const [typed, setToken] = useState("");
  const [used, setUsed] = useState(false);
  const fromLink = !!linkToken && !used;
  const token = fromLink ? linkToken : typed;
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [email, setEmail] = useState("");
  const [requestBusy, setRequestBusy] = useState(false);
  const [requestOutcome, setRequestOutcome] = useState<Outcome>(null);


  const confirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy || !token.trim()) return;
    setBusy(true);
    setOutcome(null);
    const r = await postAuth(accountPaths.verificationConfirm, { token: token.trim() }, c);
    setBusy(false);
    if (r.ok) {
      setToken("");
      setUsed(true);
      setOutcome({ kind: "success", text: c.verify.done });
      void refreshAccount();
    } else {
      setOutcome({ kind: "error", text: r.error ?? c.unreachable });
    }
  };

  const request = async (e: React.FormEvent) => {
    e.preventDefault();
    if (requestBusy) return;
    setRequestBusy(true);
    setRequestOutcome(null);
    const r = await postAuth<AcceptedResponse>(accountPaths.verificationRequest, { email: email.trim() }, c);
    setRequestBusy(false);
    setRequestOutcome(r.ok ? { kind: "info", text: r.body?.message ?? "" } : { kind: "error", text: r.error ?? c.unreachable });
  };

  const verifiedEmail = account.status === "signed-in" && account.user?.email_verified ? account.user.email : null;

  return (
    <AuthCard title={c.verify.title} lede={c.verify.lede}>
      {verifiedEmail && <OutcomeMessage outcome={{ kind: "success", text: fillCopy(c.verify.alreadyVerified, { email: verifiedEmail }) }} />}
      <form className="auth-form" onSubmit={confirm}>
        {fromLink ? (
          <p className="auth-note" role="status">
            {c.verify.tokenFromLink}
          </p>
        ) : (
          <TextField
            label={c.verify.token}
            name="one-time-code"
            autoComplete="one-time-code"
            required
            maxLength={512}
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        )}
        <OutcomeMessage outcome={outcome} />
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy || !token.trim()} aria-busy={busy}>
          {busy ? c.working : c.verify.submit}
        </button>
      </form>

      <section className="auth-subsection" aria-labelledby="verify-request-title">
        <h2 id="verify-request-title" className="auth-subtitle">
          {c.verify.requestTitle}
        </h2>
        <EmailUnavailableNotice c={c} />
        <form className="auth-form" onSubmit={request}>
          <TextField label={c.email} type="email" name="email" autoComplete="email" required maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} />
          <OutcomeMessage outcome={requestOutcome} />
          <button type="submit" className="btn btn-secondary auth-submit" disabled={requestBusy} aria-busy={requestBusy}>
            {requestBusy ? c.working : c.verify.requestSubmit}
          </button>
        </form>
      </section>
    </AuthCard>
  );
}
