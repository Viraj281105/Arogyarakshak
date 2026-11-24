"use client";

import React from "react";
import { PUBLIC_FOOTER_LINKS } from "../components/public/publicRoutes";
import { NAV_ITEMS } from "./nav";
import { useLanguage } from "./ShellProvider";
import { shellCopy } from "./shellCopy";
import { TransitionLink } from "./TransitionLink";

/**
 * Site footer: what the tool is, where its references come from, the same nav as the header and
 * (Wave 3 M3) the public pages, from the deliberately tiny components/public/publicRoutes.ts.
 */
export function SiteFooter() {
  const [lang] = useLanguage();
  const copy = shellCopy[lang];
  const f = copy.footer;
  return (
    <footer className="site-footer">
      <div className="shell-container site-footer-grid">
        <div className="site-footer-about">
          <p className="site-footer-brand">
            <span>{copy.appName}</span>
            <span className="site-chip">{f.academic}</span>
          </p>
          <p>{f.disclaimer}</p>
          <p className="site-footer-note">{f.statutoryNote}</p>
        </div>

        <nav aria-labelledby="site-footer-explore">
          <h2 id="site-footer-explore" className="site-footer-heading">
            {f.explore}
          </h2>
          <ul className="site-footer-list">
            <li>
              <TransitionLink href="/">{copy.nav.home}</TransitionLink>
            </li>
            {NAV_ITEMS.map((item) => (
              <li key={item.key}>
                <TransitionLink href={item.href}>{copy.nav[item.key]}</TransitionLink>
              </li>
            ))}
            {PUBLIC_FOOTER_LINKS.map(([href, label]) => (
              <li key={href}>
                <TransitionLink href={href}>{label}</TransitionLink>
              </li>
            ))}
          </ul>
        </nav>

        <div>
          <h2 className="site-footer-heading">{f.sources}</h2>
          <ul className="site-footer-list site-footer-refs">
            <li>{f.cghsRef}</li>
            <li>{f.irdaiRef}</li>
            <li>{f.nppaRef}</li>
          </ul>
        </div>
      </div>

      <div className="shell-container site-footer-base">
        <p>{f.copyright}</p>
        <ul className="site-footer-badges">
          <li className="badge badge-demo">{f.notAdvice}</li>
          <li className="badge badge-human-reviewed">{f.zeroRetention}</li>
        </ul>
      </div>
    </footer>
  );
}
