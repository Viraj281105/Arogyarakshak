"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAccount } from "../../hooks/useAccount";
import { useT } from "../../i18n/useT";
import { refreshAccount } from "../../lib/session";
import { AUTH_PATHS } from "../../shell/nav";
import { TransitionLink } from "../../shell/TransitionLink";
import { ErrorState, LoadingState } from "../ui/States";

/**
 * Shows the workspace only to a signed-in account (ADR-029). This is a convenience, not the
 * boundary: the API refuses every signed-out request, so nothing about a case can be fetched
 * even if this component were skipped. Signed out, it sends the visitor to sign in and back.
 */
export function RequireAccount({ children }: { children: React.ReactNode }) {
  const account = useAccount();
  const router = useRouter();
  const pathname = usePathname();
  const tr = useT();
  const signedOut = account.status === "signed-out" || account.status === "expired";
  const signInHref = `${AUTH_PATHS.login}?next=${encodeURIComponent(pathname)}`;

  useEffect(() => {
    if (signedOut) router.replace(signInHref);
  }, [signedOut, signInHref, router]);

  if (account.status === "signed-in") return <>{children}</>;

  return (
    <div className="container ws-gate">
      {account.status === "unreachable" ? (
        <ErrorState
          title={tr("The server cannot be reached")}
          action={
            <button type="button" className="btn btn-secondary btn-compact" onClick={() => void refreshAccount()}>
              {tr("Try again")}
            </button>
          }
        >
          <p>{tr("You can open your cases once the server answers and you are signed in.")}</p>
        </ErrorState>
      ) : signedOut ? (
        <>
          <h1 className="ws-page-title">{tr("Sign in to continue")}</h1>
          <p>{tr("Your cases and every check need an account, so that only you can open them.")}</p>
          <p>
            <TransitionLink href={signInHref} className="btn btn-primary">
              {tr("Sign in")}
            </TransitionLink>
          </p>
        </>
      ) : (
        <LoadingState label={tr("Checking your sign-in…")} minHeight="12rem" />
      )}
    </div>
  );
}
