"use client";

import React, { useEffect, useRef } from "react";
import type { Language } from "../shared/i18n/types";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { MODULE_ICONS } from "./icons/moduleIcons";
import { MODULE_META, MODULE_ORDER, NAV_ITEMS, isActiveHref, moduleHash, type ModuleTab } from "./nav";

function ModuleIcon({ id }: { id: ModuleTab }) {
  const Icon = MODULE_ICONS[id];
  return <Icon size={20} aria-hidden="true" className="site-icon" />;
}
import { shellCopy } from "./shellCopy";
import { TransitionLink } from "./TransitionLink";

/**
 * The drawer used below the desktop breakpoint. A native modal <dialog>: the browser traps
 * focus, closes it on Escape, makes the page behind it inert and returns focus to the menu
 * button. Links close it synchronously, before the browser follows them.
 */
export function MobileNav({
  open,
  onClosed,
  lang,
  pathname,
}: {
  open: boolean;
  onClosed: () => void;
  lang: Language;
  pathname: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const copy = shellCopy[lang];

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    else if (!open && d.open) d.close();
  }, [open]);

  const close = () => ref.current?.close();

  return (
    <dialog
      ref={ref}
      id="site-drawer"
      className="site-drawer"
      aria-labelledby="site-drawer-title"
      onClose={onClosed}
      onClick={(e) => {
        // The panel fills the dialog box, so a click on the dialog itself is on the backdrop.
        if (e.target === ref.current) close();
      }}
    >
      <div className="site-drawer-panel">
        <div className="site-drawer-head">
          <p id="site-drawer-title" className="site-drawer-title">
            {copy.menu.title}
          </p>
          <button type="button" className="site-icon-btn" onClick={close} aria-label={copy.menu.close}>
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" className="site-icon">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <nav aria-label={copy.nav.primary}>
          <ul className="site-drawer-nav">
            <li>
              <TransitionLink href="/" onClick={close} aria-current={isActiveHref("/", pathname) ? "page" : undefined}>
                {copy.nav.home}
              </TransitionLink>
            </li>
            {NAV_ITEMS.map((item) => (
              <li key={item.key}>
                <TransitionLink
                  href={item.href}
                  onClick={close}
                  aria-current={isActiveHref(item.href, pathname) ? "page" : undefined}
                >
                  {copy.nav[item.key]}
                </TransitionLink>
              </li>
            ))}
          </ul>
        </nav>

        <section className="site-drawer-section" aria-labelledby="site-drawer-checks">
          <h2 id="site-drawer-checks" className="site-drawer-heading">
            {copy.menu.checks}
          </h2>
          <ul className="site-drawer-modules">
            {MODULE_ORDER.map((id) => (
              <li key={id}>
                <TransitionLink href={`/${moduleHash(id)}`} onClick={close}>
                  <ModuleIcon id={id} />
                  <span>{copy.tabs[id]}</span>
                  <span className="site-chip">{MODULE_META[id].badge}</span>
                </TransitionLink>
              </li>
            ))}
          </ul>
        </section>

        <div className="site-drawer-section site-drawer-lang">
          <p className="site-drawer-heading">{copy.language.label}</p>
          <LanguageSwitcher />
        </div>

        <p className="site-drawer-privacy">
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="site-icon">
            <rect width="18" height="11" x="3" y="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>
            <strong>{copy.byodBadge}</strong>
            {copy.byodDescription}
          </span>
        </p>
      </div>
    </dialog>
  );
}
