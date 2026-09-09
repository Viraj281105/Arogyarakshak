"use client";

import React from "react";
import Link from "next/link";
import { Language, translations } from "../translations";

interface HeaderProps {
  currentLang: Language;
  onLanguageChange: (lang: Language) => void;
  currentTheme?: "dark" | "light";
  onThemeToggle?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentLang,
  onLanguageChange,
  currentTheme = "dark",
  onThemeToggle,
}) => {
  const t = translations[currentLang];

  return (
    <header className="header-bar">
      <div className="container header-inner">
        <Link href="/" className="brand-logo" aria-label="ArogyaRakshak Home">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: "var(--brand-cyan)" }}
            aria-hidden="true"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="M12 8v8" />
            <path d="M8 12h8" />
          </svg>
          <span>{t.appName}</span>
          <span className="brand-badge">PROD</span>
        </Link>

        <div className="nav-actions">
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
              {currentTheme === "dark" ? "☀️" : "🌙"}
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
