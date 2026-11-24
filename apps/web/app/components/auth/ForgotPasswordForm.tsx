"use client";

import React, { useState } from "react";
import { accountPaths, type AcceptedResponse } from "../../shared/api-client";
import { AUTH_PATHS } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { TransitionLink } from "../../shell/TransitionLink";
import { AuthCard, EmailUnavailableNotice, OutcomeMessage, TextField, postAuth, type Outcome } from "./AuthShared";
import { authCopy } from "./authCopy";

/**
 * Password-reset request. The API accepts it (202, the same answer whether or not an account
 * exists) but cannot deliver email (MAIL_TRANSPORT=disabled, ADR-026), so the page says so before
 * the form and shows the API's own answer, which also says no message will arrive.
 */
export function ForgotPasswordForm() {
  const [lang] = useLanguage();
  const c = authCopy[lang];
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setOutcome(null);
    const r = await postAuth<AcceptedResponse>(accountPaths.resetRequest, { email: email.trim() }, c);
    setBusy(false);
    setOutcome(r.ok ? { kind: "info", title: c.forgot.doneTitle, text: r.body?.message ?? "" } : { kind: "error", text: r.error ?? c.unreachable });
  };

  return (
    <AuthCard
      title={c.forgot.title}
      lede={c.forgot.lede}
      footer={
        <p>
          <TransitionLink href={AUTH_PATHS.login}>{c.forgot.backToSignIn}</TransitionLink>
        </p>
      }
    >
      <EmailUnavailableNotice c={c} />
      <form className="auth-form" onSubmit={onSubmit}>
        <TextField label={c.email} type="email" name="email" autoComplete="email" required maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} />
        <OutcomeMessage outcome={outcome} />
        <button type="submit" className="btn btn-secondary auth-submit" disabled={busy} aria-busy={busy}>
          {busy ? c.working : c.forgot.submit}
        </button>
      </form>
    </AuthCard>
  );
}
