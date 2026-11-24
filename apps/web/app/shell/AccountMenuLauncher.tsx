"use client";

import React, { useCallback, useRef, useState } from "react";
import CircleUser from "lucide-react/icons/circle-user";
import { useAccount } from "../hooks/useAccount";
import { AUTH_PATHS } from "./nav";
import { useLanguage } from "./ShellProvider";
import { shellCopy } from "./shellCopy";
import { TransitionLink } from "./TransitionLink";

type MenuComponent = typeof import("./AccountMenu").AccountMenu;

/**
 * The header's account control (ADR-026). Signed out: a "Sign in" link. Signed in: a button that
 * opens the account menu, which is fetched with a plain import() on first use so every route only
 * carries this launcher. While the first GET /auth/me is in flight a same-sized placeholder keeps
 * the header from shifting.
 */
export function AccountMenuLauncher() {
  const { status, user } = useAccount();
  const [lang] = useLanguage();
  const c = shellCopy[lang].account;
  const [open, setOpen] = useState(false);
  const [Menu, setMenu] = useState<MenuComponent | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const close = useCallback((returnFocus: boolean) => {
    setOpen(false);
    if (returnFocus) buttonRef.current?.focus();
  }, []);

  if (status === "unknown" || status === "checking") {
    return <span className="site-account-placeholder" aria-hidden="true" />;
  }

  if (status !== "signed-in" || !user) {
    return (
      <TransitionLink href={AUTH_PATHS.login} className="site-account-link" aria-label={c.signIn}>
        <CircleUser size={18} aria-hidden="true" className="site-icon" />
        <span className="site-account-text">{c.signIn}</span>
      </TransitionLink>
    );
  }

  const toggle = () => {
    if (open) return close(false);
    setOpen(true);
    if (!Menu) {
      import("./AccountMenu")
        .then((m) => setMenu(() => m.AccountMenu))
        .catch(() => setOpen(false));
    }
  };

  return (
    <div className="site-account">
      <button
        ref={buttonRef}
        type="button"
        className="site-account-btn"
        aria-expanded={open}
        aria-controls="site-account-menu"
        aria-label={`${c.menuLabel}: ${user.email}`}
        onClick={toggle}
      >
        <CircleUser size={18} aria-hidden="true" className="site-icon" />
        <span className="site-account-text site-account-email">{user.email}</span>
      </button>
      {open && Menu && <Menu id="site-account-menu" email={user.email} lang={lang} onClose={close} anchor={buttonRef} />}
    </div>
  );
}
