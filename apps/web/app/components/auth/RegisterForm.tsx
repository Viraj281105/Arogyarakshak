"use client";

import React, { useState } from "react";
import { accountPaths, passwordProblem, type AcceptedResponse } from "../../shared/api-client";
import { AUTH_PATHS } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { TransitionLink } from "../../shell/TransitionLink";
import { AuthCard, OutcomeMessage, PasswordField, TextField, postAuth, type Outcome } from "./AuthShared";
import { authCopy } from "./authCopy";

export function RegisterForm() {
  const [lang] = useLanguage();
  const c = authCopy[lang];
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [done, setDone] = useState<string | null>(null);

  const problem = password ? passwordProblem(password, email) : "too_short";
  const policyError = touched && password ? (problem ? c.policy[problem] : null) : null;
  const mismatch = touched && confirm && confirm !== password ? c.mismatch : null;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (busy || problem || confirm !== password) {
      setOutcome({ kind: "error", text: problem ? c.policy[problem] : c.mismatch });
      return;
    }
    setBusy(true);
    setOutcome(null);
    const r = await postAuth<AcceptedResponse>(accountPaths.register, { email: email.trim(), password }, c);
    setBusy(false);
    if (r.ok) {
      setPassword("");
      setConfirm("");
      // The API answers the same for a new and an existing address (enumeration resistance).
      setDone(r.body?.message ?? "");
      return;
    }
    setOutcome({ kind: "error", text: r.error ?? c.unreachable });
  };

  if (done !== null) {
    return (
      <AuthCard title={c.register.doneTitle}>
        <OutcomeMessage outcome={{ kind: "success", text: done }} />
        <p className="auth-note">{c.register.verifyNote}</p>
        <p>
          <TransitionLink href={AUTH_PATHS.login} className="btn btn-primary">
            {c.register.signIn}
          </TransitionLink>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title={c.register.title}
      lede={c.register.lede}
      footer={
        <p>
          {c.register.haveAccount} <TransitionLink href={AUTH_PATHS.login}>{c.register.signIn}</TransitionLink>
        </p>
      }
    >
      <form className="auth-form" onSubmit={onSubmit}>
        <TextField label={c.email} type="email" name="email" autoComplete="email" required maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} />
        <PasswordField
          lang={lang}
          label={c.password}
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
        <p className="auth-note">{c.register.whatIsKept}</p>
        <OutcomeMessage outcome={outcome} />
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy} aria-busy={busy}>
          {busy ? c.working : c.register.submit}
        </button>
      </form>
    </AuthCard>
  );
}
