"use client";

import React, { useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { accountPaths, type SessionResponse } from "../../shared/api-client";
import { useAccount } from "../../hooks/useAccount";
import { markSignedIn } from "../../lib/session";
import { AUTH_PATHS, WORKSPACE_PATH } from "../../shell/nav";
import { useLanguage } from "../../shell/ShellProvider";
import { TransitionLink } from "../../shell/TransitionLink";
import { AuthCard, OutcomeMessage, PasswordField, TextField, postAuth, type Outcome } from "./AuthShared";
import { authCopy, fillCopy } from "./authCopy";

// Where a successful sign-in may continue to: the workspace pages and the reviewer desk.
// Anything else (an external URL, a protocol-relative "//host", a query or fragment) is ignored,
// so the page cannot be used as an open redirect.
const NEXT_ALLOWED = [
  "/app",
  "/app/case",
  "/app/case/billnyay",
  "/app/case/daavisetu",
  "/app/case/bimanyay",
  "/app/case/schemesetu",
  "/app/case/dawacheck",
  "/app/case/reports",
  "/app/settings",
  "/review",
];

const noSubscribe = () => () => {};

export function safeNext(raw: string | null): string {
  return raw && NEXT_ALLOWED.includes(raw) ? raw : WORKSPACE_PATH;
}

export function LoginForm() {
  const [lang] = useLanguage();
  const c = authCopy[lang];
  const account = useAccount();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  // Read on the client only (no useSearchParams, so the page stays static).
  const next = useSyncExternalStore(
    noSubscribe,
    () => safeNext(new URLSearchParams(window.location.search).get("next")),
    () => WORKSPACE_PATH,
  );

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setOutcome(null);
    const r = await postAuth<SessionResponse>(accountPaths.login, { email: email.trim(), password, session_transport: "cookie" }, c);
    setBusy(false);
    if (r.ok && r.body) {
      setPassword("");
      markSignedIn(r.body.user);
      router.push(next);
      return;
    }
    setOutcome({ kind: "error", text: r.error ?? c.unreachable });
  };

  if (account.status === "signed-in" && account.user) {
    return (
      <AuthCard title={c.login.title}>
        <p className="auth-lede">{fillCopy(c.login.alreadyIn, { email: account.user.email })}</p>
        <p>
          <TransitionLink href={next} className="btn btn-primary">
            {c.login.goToCases}
          </TransitionLink>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title={c.login.title}
      lede={c.login.lede}
      footer={
        <>
          <p>
            <TransitionLink href={AUTH_PATHS.forgotPassword}>{c.login.forgot}</TransitionLink>
          </p>
          <p>
            {c.login.noAccount} <TransitionLink href={AUTH_PATHS.register}>{c.login.register}</TransitionLink>
          </p>
        </>
      }
    >
      {account.status === "expired" && <OutcomeMessage outcome={{ kind: "info", text: c.login.sessionEnded }} />}
      <form className="auth-form" onSubmit={onSubmit} noValidate={false}>
        <TextField label={c.email} type="email" name="email" autoComplete="email" required maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} />
        <PasswordField
          lang={lang}
          label={c.password}
          name="password"
          autoComplete="current-password"
          required
          maxLength={1024}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <OutcomeMessage outcome={outcome} />
        <button type="submit" className="btn btn-primary auth-submit" disabled={busy} aria-busy={busy}>
          {busy ? c.working : c.login.submit}
        </button>
      </form>
    </AuthCard>
  );
}
