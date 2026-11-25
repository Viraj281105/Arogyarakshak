"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { accountPaths } from "../shared/api-client";
import type { Language } from "../shared/i18n/types";
import { DemoAccountNote } from "../components/auth/DemoAccountNote";
import { apiFetch } from "../lib/apiFetch";
import { clearActiveCase, readActiveCase } from "../lib/caseStore";
import { markSignedOut } from "../lib/session";
import { SETTINGS_PATH, WORKSPACE_PATH } from "./nav";
import { shellCopy } from "./shellCopy";
import { TransitionLink } from "./TransitionLink";

/**
 * The signed-in account panel (loaded on first open). A disclosure, not an ARIA menu: plain links
 * and a button in tab order. Escape or a click outside closes it; Escape returns focus to the
 * account button.
 */
export function AccountMenu({
  id,
  email,
  lang,
  onClose,
  anchor,
}: {
  id: string;
  email: string;
  lang: Language;
  onClose: (returnFocus: boolean) => void;
  anchor: React.RefObject<HTMLButtonElement | null>;
}) {
  const c = shellCopy[lang].account;
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose(true);
    };
    const onPointer = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!ref.current?.contains(t) && !anchor.current?.contains(t)) onClose(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [onClose, anchor]);

  const signOut = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch(accountPaths.logout, { method: "POST" });
      // 401: the session had already ended; either way this browser is signed out now.
      if (!res.ok && res.status !== 401) throw new Error(String(res.status));
      markSignedOut();
      // An owned case cannot be opened without the session; guest cases in this tab are kept.
      if (readActiveCase()?.owned) clearActiveCase();
      onClose(false);
      router.push("/");
    } catch {
      setError(c.signOutFailed);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div ref={ref} id={id} className="site-account-menu">
      <p className="site-account-who">
        <span>{c.signedInAs}</span> <strong>{email}</strong>
      </p>
      <DemoAccountNote className="site-account-who" />
      <ul>
        <li>
          <TransitionLink href={WORKSPACE_PATH} onClick={() => onClose(false)}>
            {c.myCases}
          </TransitionLink>
        </li>
        <li>
          <TransitionLink href={SETTINGS_PATH} onClick={() => onClose(false)}>
            {c.settings}
          </TransitionLink>
        </li>
        <li>
          <button type="button" onClick={signOut} disabled={busy}>
            {busy ? c.signingOut : c.signOut}
          </button>
        </li>
      </ul>
      {error && (
        <p className="site-account-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
