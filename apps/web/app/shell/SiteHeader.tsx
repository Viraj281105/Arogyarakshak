"use client";

import React, { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { readReducedMotion } from "../motion/useReducedMotion";
import { drawerShouldClose, nextHeaderState, type HeaderState } from "./headerScroll";
import { AccountMenuLauncher } from "./AccountMenuLauncher";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { MobileNav } from "./MobileNav";
import { NAV_ITEMS, isActiveHref } from "./nav";
import { useHeaderSlotContent, useLanguage } from "./ShellProvider";
import { shellCopy } from "./shellCopy";
import { ThemeToggle } from "./ThemeToggle";
import { TransitionLink } from "./TransitionLink";

// Must match the desktop breakpoint in shell.css (inline nav, no menu button).
const COMPACT_QUERY = "(max-width: 1279.98px)";

/**
 * The sticky site header. Scroll-aware without changing its height (so it cannot cause layout
 * shift): `data-elevated` raises its surface once the page scrolls; below the desktop
 * breakpoint `data-hidden` slides it away while scrolling down and back on any scroll up
 * (see nextHeaderState). Attributes are written directly, so scrolling never re-renders React.
 */
export function SiteHeader() {
  const [lang] = useLanguage();
  const copy = shellCopy[lang];
  const pathname = usePathname() ?? "/";
  const slot = useHeaderSlotContent();
  const [menuOpen, setMenuOpen] = useState(false);
  const headerRef = useRef<HTMLElement>(null);
  const menuOpenRef = useRef(false);

  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const compact = window.matchMedia?.(COMPACT_QUERY);
    let state: HeaderState = { elevated: false, hidden: false };
    let lastY = window.scrollY;
    let frame = 0;
    const update = () => {
      frame = 0;
      const y = window.scrollY;
      const pinned = menuOpenRef.current || el.contains(document.activeElement);
      const next = nextHeaderState(state, {
        y,
        lastY,
        compact: compact?.matches ?? false,
        reducedMotion: readReducedMotion(),
        pinned,
      });
      lastY = y;
      if (next.elevated !== state.elevated) el.toggleAttribute("data-elevated", next.elevated);
      if (next.hidden !== state.hidden) el.toggleAttribute("data-hidden", next.hidden);
      state = next;
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    // The drawer only exists below the desktop breakpoint; close it if the viewport grows past it.
    const onBreakpoint = () => {
      if (drawerShouldClose({ open: menuOpenRef.current, compact: compact?.matches ?? false })) {
        el.querySelector<HTMLDialogElement>("dialog.site-drawer")?.close();
      }
      schedule();
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    el.addEventListener("focusin", schedule);
    compact?.addEventListener?.("change", onBreakpoint);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      el.removeEventListener("focusin", schedule);
      compact?.removeEventListener?.("change", onBreakpoint);
    };
  }, []);

  // The scroll handler reads the drawer state through a ref; opening the drawer also brings a
  // hidden header back.
  useEffect(() => {
    menuOpenRef.current = menuOpen;
    if (menuOpen) headerRef.current?.removeAttribute("data-hidden");
  }, [menuOpen]);

  return (
    <header ref={headerRef} className="site-header">
      <div className="shell-container site-header-inner">
        <TransitionLink href="/" className="site-brand">
          {/* Static files from scripts/brand-assets.ts: no JS in this client header, and a dark-theme variant. */}
          {/* eslint-disable-next-line @next/next/no-img-element -- tiny static SVG; next/image adds JS for no gain */}
          <img src="/brand/ar-emblem-compact.svg" width={36} height={36} alt="" className="site-emblem ar-only-light" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/ar-emblem-compact-dark.svg" width={36} height={36} alt="" className="site-emblem ar-only-dark" />
          <span className="site-brand-text">
            <span className="site-brand-name">
              <span>{copy.appName}</span>
              {/* In Hindi and Marathi the name itself is already Devanagari. */}
              {lang === "en" && (
                <span className="site-brand-deva" lang="hi">
                  आरोग्यरक्षक
                </span>
              )}
            </span>
            <span className="site-brand-tagline">{copy.tagline}</span>
          </span>
          <span className="site-chip site-badge" title={copy.prototypeTitle}>
            {copy.prototype}
          </span>
        </TransitionLink>

        <nav className="site-nav" aria-label={copy.nav.primary}>
          <ul>
            {NAV_ITEMS.map((item) => (
              <li key={item.key}>
                <TransitionLink
                  href={item.href}
                  className="site-nav-link"
                  aria-current={isActiveHref(item.href, pathname) ? "page" : undefined}
                >
                  {copy.nav[item.key]}
                </TransitionLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="site-actions">
          {/* Page chips (demo pill, signed-in reviewer). Actions are right-anchored, so filling
              this never moves the language, theme or menu buttons. */}
          <div className="site-slot">{slot}</div>
          <LanguageSwitcher className="site-lang-inline" />
          <AccountMenuLauncher />
          <ThemeToggle />
          <button
            type="button"
            className="site-icon-btn site-menu-btn"
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            aria-controls="site-drawer"
            aria-label={copy.menu.open}
            onClick={() => setMenuOpen(true)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="site-icon">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
        </div>
      </div>
      <MobileNav open={menuOpen} onClosed={() => setMenuOpen(false)} lang={lang} pathname={pathname} />
    </header>
  );
}
