"use client";

import React from "react";
import Link from "next/link";
import { Language, translations } from "../translations";

interface HeaderProps {
  currentLang: Language;
  onLanguageChange: (lang: Language) => void;
  currentTheme?: "dark" | "light";
  onThemeToggle?: () => void;
  /** Shown only when the server reports demo mode. */
  demoBadge?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({
  currentLang,
  onLanguageChange,
  currentTheme = "dark",
  onThemeToggle,
  demoBadge,
}) => {
  const t = translations[currentLang];

  return (
    <header className="header-bar">
      <div className="container header-inner">
        <Link href="/" className="brand-logo" aria-label="ArogyaRakshak Home">
          <div className="brand-emblem-wrap">
            <div className="brand-emblem-inner">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: "currentColor" }}
                aria-hidden="true"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M12 8v8" />
                <path d="M8 12h8" />
              </svg>
            </div>
          </div>
          <div className="brand-text">
            <div className="brand-name">
              <span>{t.appName}</span>
              <span className="brand-devanagari" lang="hi">आरोग्यरक्षक</span>
            </div>
            <div className="brand-tagline">{t.tagline}</div>
          </div>
          <span className="brand-badge" title="Release candidate of an academic project — not a production medical or legal service">
            PROTOTYPE
          </span>
        </Link>

        <div className="nav-actions">
          {demoBadge}
          <Link href="/clinical-review" className="reviewer-link-chip" title="Open Clinician & Reviewer Workspace">
            <span className="reviewer-status-dot" aria-hidden="true" />
            <span>Reviewer workspace</span>
          </Link>

          <div className="privacy-pill" title={t.byodDescription}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>{t.byodBadge}</span>
          </div>

          <div className="lang-btn-group" role="group" aria-label="Language Selector">
            <button
              type="button"
              className={`lang-btn ${currentLang === "en" ? "active" : ""}`}
              onClick={() => onLanguageChange("en")}
              aria-pressed={currentLang === "en"}
            >
              EN
            </button>
            <button
              type="button"
              className={`lang-btn ${currentLang === "hi" ? "active" : ""}`}
              onClick={() => onLanguageChange("hi")}
              aria-pressed={currentLang === "hi"}
            >
              हिंदी
            </button>
            <button
              type="button"
              className={`lang-btn ${currentLang === "mr" ? "active" : ""}`}
              onClick={() => onLanguageChange("mr")}
              aria-pressed={currentLang === "mr"}
            >
              मराठी
            </button>
          </div>

          {onThemeToggle && (
            <button
              type="button"
              className="theme-toggle-btn"
              onClick={onThemeToggle}
              aria-label={currentTheme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={currentTheme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                {currentTheme === "dark" ? (
                  <>
                    <circle cx="12" cy="12" r="4" />
                    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                  </>
                ) : (
                  <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
                )}
              </svg>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
