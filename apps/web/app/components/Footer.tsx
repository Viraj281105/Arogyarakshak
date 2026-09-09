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
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "2rem", marginBottom: "1.5rem" }}>
          <div style={{ maxWidth: "480px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{t.appName}</span>
              <span style={{ fontSize: "0.8rem", color: "var(--brand-teal)" }}>• v1.0 Production</span>
            </div>
            <p style={{ fontSize: "0.85rem", lineHeight: 1.6 }}>{t.footer.disclaimer}</p>
            <p style={{ fontSize: "0.8rem", marginTop: "0.5rem", color: "var(--brand-emerald)" }}>{t.footer.statutoryNote}</p>
          </div>

          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
              Statutory Benchmark Citations
            </div>
            <ul style={{ listStyle: "none", fontSize: "0.825rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <li>
                <span style={{ color: "var(--brand-cyan)" }}>✓</span> {t.footer.cghsRef}
              </li>
              <li>
                <span style={{ color: "var(--brand-cyan)" }}>✓</span> {t.footer.irdaiRef}
              </li>
              <li>
                <span style={{ color: "var(--brand-cyan)" }}>✓</span> {t.footer.nppaRef}
              </li>
            </ul>
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.25rem", display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "1rem", fontSize: "0.8rem" }}>
          <div>
            © 2026 ArogyaRakshak (आरोग्यरक्षक) — Open Source MIT License
          </div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <span>DPDP Act 2023 Compliant</span>
            <span>•</span>
            <span>Zero Document Retention (BYOD)</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
