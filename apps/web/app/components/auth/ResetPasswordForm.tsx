"use client";

import React, { useState } from "react";
import { accountPaths, passwordProblem } from "../../shared/api-client";
import { markSignedOut } from "../../lib/session";
import { AUTH_PATHS } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { TransitionLink } from "../../shell/TransitionLink";
import { AuthCard, OutcomeMessage, PasswordField, TextField, postAuth, useFragmentToken, type Outcome } from "./AuthShared";
import { authCopy } from "./authCopy";

/** Sets a new password with the one-time code from a reset link (`/reset-password#token=...`). */
export function ResetPasswordForm() {
  const [lang] = useLanguage();
  const c = authCopy[lang];
  const linkToken = useFragmentToken();
  const [typed, setToken] = useState("");
  const [used, setUsed] = useState(false);
  const fromLink = !!linkToken && !used;
  const token = fromLink ? linkToken : typed;
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [done, setDone] = useState(false);


  const problem = passwordProblem(password);
  const policyError = touched && password && problem ? c.policy[problem] : null;
  const mismatch = touched && confirm && confirm !== password ? c.mismatch : null;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (busy) return;
    if (problem || confirm !== password) {
      setOutcome({ kind: "error", text: problem ? c.policy[problem] : c.mismatch });
      return;
    }
    setBusy(true);
    setOutcome(null);
    const r = await postAuth(accountPaths.resetConfirm, { token: token.trim(), new_password: password }, c);
    setBusy(false);
    if (r.ok) {
      setPassword("");
      setConfirm("");
      setToken("");
      setUsed(true);
      // Every session of the account was revoked, possibly this browser's too.
      markSignedOut();
      setDone(true);
      return;
    }
    setOutcome({ kind: "error", text: r.error ?? c.unreachable });
  };

  if (done) {
    return (
      <AuthCard title={c.reset.doneTitle}>
        <OutcomeMessage outcome={{ kind: "success", text: c.reset.done }} />
        <p>
          <TransitionLink href={AUTH_PATHS.login} className="btn btn-primary">
            {c.reset.signIn}
          </TransitionLink>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={c.reset.title} lede={c.reset.lede}>
      <form className="auth-form" onSubmit={onSubmit}>
        {fromLink ? (
          <p className="auth-note" role="status">
            {c.reset.tokenFromLink}
          </p>
        ) : (
          <TextField
            label={c.reset.token}
            hint={c.reset.tokenHint}
            name="one-time-code"
            autoComplete="one-time-code"
            required
            maxLength={512}
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        )}
        <PasswordField
          lang={lang}
          label={c.newPassword}
          name="new-password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={1024}
          hint={c.passwordHint}
          error={policyError}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onBlur={() => setTouched(true)}
        />
        <PasswordField
          lang={lang}
          label={c.confirmPassword}
          name="confirm-password"
          autoComplete="new-password"
          required
          maxLength={1024}
          error={mismatch}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
        <OutcomeMessage outcome={outcome} />
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy || !token.trim()} aria-busy={busy}>
          {busy ? c.working : c.reset.submit}
        </button>
      </form>
    </AuthCard>
  );
}
