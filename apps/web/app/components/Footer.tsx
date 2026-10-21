"use client";

import React from "react";
import { Language, translations } from "../translations";

interface FooterProps {
  currentLang: Language;
}

export const Footer: React.FC<FooterProps> = ({ currentLang }) => {
  const t = translations[currentLang];

  return (
    <footer className="footer-bar">
      <div className="container">
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "2rem", marginBottom: "2rem" }}>
          <div style={{ maxWidth: "520px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.75rem" }}>
              <span style={{ fontWeight: 800, fontSize: "1.1rem", color: "var(--text-primary)", fontFamily: "var(--font-headline)" }}>{t.appName}</span>
              <span className="brand-badge" style={{ fontSize: "0.65rem" }}>Academic Prototype</span>
            </div>
            <p style={{ fontSize: "0.85rem", lineHeight: 1.65, color: "var(--text-secondary)" }}>{t.footer.disclaimer}</p>
            <p style={{ fontSize: "0.8rem", marginTop: "0.65rem", color: "var(--brand-emerald)", fontWeight: 500 }}>{t.footer.statutoryNote}</p>
          </div>

          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", fontFamily: "var(--font-headline)" }}>
              Reference sources
            </div>
            <ul style={{ listStyle: "none", fontSize: "0.825rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <li style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="footer-ref-dot" aria-hidden="true" />
                <span style={{ color: "var(--text-secondary)" }}>{t.footer.cghsRef}</span>
              </li>
              <li style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="footer-ref-dot" aria-hidden="true" />
                <span style={{ color: "var(--text-secondary)" }}>{t.footer.irdaiRef}</span>
              </li>
              <li style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="footer-ref-dot" aria-hidden="true" />
                <span style={{ color: "var(--text-secondary)" }}>{t.footer.nppaRef}</span>
              </li>
            </ul>
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.5rem", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "1rem", fontSize: "0.8rem" }}>
          <div style={{ color: "var(--text-muted)" }}>
            © 2026 ArogyaRakshak (आरोग्यरक्षक) — Open Source MIT License
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <span className="badge badge-demo" style={{ fontSize: "0.7rem" }}>
              Not legal or medical advice
            </span>
            <span style={{ color: "var(--border-subtle)" }}>•</span>
            <span className="badge badge-human-reviewed" style={{ fontSize: "0.7rem" }}>
              Zero Document Retention (BYOD)
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
