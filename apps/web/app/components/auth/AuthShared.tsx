"use client";

import React, { useId, useState, useSyncExternalStore } from "react";
import Eye from "lucide-react/icons/eye";
import EyeOff from "lucide-react/icons/eye-off";
import { apiErrorMessage, apiFetch, retryAfterSeconds } from "../../lib/apiFetch";
import { authCopy, fillCopy, type AuthCopy } from "./authCopy";
import type { Language } from "../../shared/i18n/types";
/**
 * The form card shared by the account pages: one <h1>, a lede and the form. The Deep Forest brand
 * panel beside it is AuthSplit (a Server Component the pages wrap around the form), so this client
 * module, which Settings also imports, carries no brand or background code.
 */
export function AuthCard({ title, lede, children, footer }: { title: string; lede?: React.ReactNode; children: React.ReactNode; footer?: React.ReactNode }) {
  return (
    <section className="auth-card" aria-labelledby="auth-title">
      <h1 id="auth-title" className="auth-title">
        {title}
      </h1>
      {lede && <p className="auth-lede">{lede}</p>}
      {children}
      {footer && <div className="auth-footer">{footer}</div>}
    </section>
  );
}

export function TextField({
  label,
  hint,
  error,
  ...input
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string | null }) {
  const id = useId();
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-err` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <input id={id} className="auth-input" aria-describedby={describedBy} aria-invalid={error ? true : undefined} {...input} />
      {hint && (
        <p id={`${id}-hint`} className="auth-hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className="auth-field-error">
          {error}
        </p>
      )}
    </div>
  );
}

/** Password input with a show/hide toggle (the toggle never submits and keeps its own label). */
export function PasswordField({
  label,
  hint,
  error,
  lang,
  ...input
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string | null; lang: Language }) {
  const id = useId();
  const [shown, setShown] = useState(false);
  const c = authCopy[lang];
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-err` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <div className="auth-password">
        <input
          id={id}
          className="auth-input"
          type={shown ? "text" : "password"}
          aria-describedby={describedBy}
          aria-invalid={error ? true : undefined}
          {...input}
        />
        <button
          type="button"
          className="auth-reveal"
          aria-pressed={shown}
          aria-label={shown ? c.hidePassword : c.showPassword}
          onClick={() => setShown((s) => !s)}
        >
          {shown ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </div>
      {hint && (
        <p id={`${id}-hint`} className="auth-hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className="auth-field-error">
          {error}
        </p>
      )}
    </div>
  );
}

export type Outcome = { kind: "error" | "success" | "info"; title?: string; text: string } | null;

/** The result of a submit, announced to screen readers (alert for errors, status otherwise). */
export function OutcomeMessage({ outcome }: { outcome: Outcome }) {
  if (!outcome) return null;
  return (
    <div className={`auth-outcome auth-outcome-${outcome.kind}`} role={outcome.kind === "error" ? "alert" : "status"}>
      {outcome.title && <p className="auth-outcome-title">{outcome.title}</p>}
      <p>{outcome.text}</p>
    </div>
  );
}

/** Says, before any form, that the server cannot send email yet (no fake "check your inbox"). */
export function EmailUnavailableNotice({ c }: { c: AuthCopy }) {
  return (
    <div className="auth-outcome auth-outcome-info" role="note">
      <p className="auth-outcome-title">{c.emailUnavailableTitle}</p>
      <p>{c.emailUnavailable}</p>
    </div>
  );
}

export interface AuthResult<T> {
  ok: boolean;
  status: number;
  body: T | null;
  /** Readable error for a failed request (API text, throttle with Retry-After, or network). */
  error: string | null;
}

/**
 * POSTs JSON to an account route. Always sends credentials ("include") so a login can set the
 * session cookie and a signed-in change can carry it. Errors are the API's own enumeration-
 * resistant text; only network failure, an untrusted Origin and the throttle get local wording.
 */
export async function postAuth<T>(path: string, body: unknown, c: AuthCopy, method: "POST" | "DELETE" = "POST"): Promise<AuthResult<T>> {
  let res: Response;
  try {
    res = await apiFetch(path, {
      method,
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 0, body: null, error: c.unreachable };
  }
  if (res.ok) {
    let parsed: T | null = null;
    try {
      parsed = res.status === 204 ? null : ((await res.json()) as T);
    } catch {
      parsed = null;
    }
    return { ok: true, status: res.status, body: parsed, error: null };
  }
  if (res.status === 429) {
    const s = retryAfterSeconds(res);
    const detail = await apiErrorMessage(res);
    return { ok: false, status: 429, body: null, error: s ? `${detail} ${fillCopy(c.retryIn, { seconds: s })}` : detail || c.throttled };
  }
  const detail = await apiErrorMessage(res);
  if (res.status === 403 && /origin/i.test(detail)) return { ok: false, status: 403, body: null, error: c.untrustedOrigin };
  return { ok: false, status: res.status, body: null, error: detail };
}

// The fragment token is read once per page load and cached, so every render agrees.
let fragmentToken: string | null | undefined;
const noSubscribe = () => () => {};

/** The one-time token from `#token=...` (null on the server and when there is none). */
export function useFragmentToken(): string | null {
  return useSyncExternalStore(
    noSubscribe,
    () => {
      if (fragmentToken === undefined) fragmentToken = takeFragmentToken();
      return fragmentToken;
    },
    () => null,
  );
}

/**
 * Reads a one-time token from the URL fragment (`#token=...`, the form ADR-026 requires of a
 * future mail transport: fragments are never sent to a server or in a Referer) and removes it from
 * the address bar and history entry at once.
 */
export function takeFragmentToken(): string | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const token = params.get("token");
  if (!token) return null;
  try {
    window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
  } catch {
    // ignore: the token is still only in the fragment
  }
  return token.trim().slice(0, 512) || null;
}
