"use client";

import React, { useCallback, useState } from "react";
import Link from "next/link";
import { ReviewerProfile, clinicalPaths, clinicalRequest } from "../lib/clinical";
import { ReviewerAttribution } from "../components/clinical/Attribution";
import { StatePanel } from "../components/clinical/StatePanel";
import { DemoBanner, DemoPill, useDemoStatus } from "../components/demo/DemoBanner";
import { TONE_CLASS } from "../lib/labels";
import { ReviewsTab } from "./components/ReviewsTab";
import { SafetyTab } from "./components/SafetyTab";
import { SignInPanel } from "./components/SignInPanel";
import { TranscriptionTab } from "./components/TranscriptionTab";
import { AssignedReview, ReviewerCall, Tab } from "./types";
import { useTheme } from "../hooks/useTheme";

/** Reviewer workspace: credential + profile, then three tabs (assigned reviews,
 *  transcriptions, safety governance). Each tab owns its own state. */
export default function ClinicalReviewWorkspace() {
  // Held in memory only: the credential is a bearer secret and is never written to
  // localStorage. Reloading the page means pasting it again.
  const { theme, toggleTheme } = useTheme();
  const demoStatus = useDemoStatus();
  const [token, setToken] = useState("");
  const [me, setMe] = useState<ReviewerProfile | null>(null);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("reviews");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [queue, setQueue] = useState<AssignedReview[]>([]);

  const call = useCallback(
    async <T,>(path: string, method: "GET" | "POST" | "PUT" = "GET", body?: unknown): Promise<T> =>
      clinicalRequest<T>(path, { method, body, reviewerToken: token }),
    [token]
  ) as ReviewerCall;

  const guard = async (fn: () => Promise<void>, ok?: string) => {
    setError(null);
    setNotice(null);
    try {
      await fn();
      if (ok) setNotice(ok);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const openWithCredential = (value: string) =>
    guard(async () => {
      const profile = await clinicalRequest<ReviewerProfile>(clinicalPaths.reviewerMe(), { reviewerToken: value });
      setToken(value);
      setMe(profile);
      const q = await clinicalRequest<AssignedReview[]>(clinicalPaths.assigned(), { reviewerToken: value });
      setQueue(q);
    });

  const refreshQueue = () => guard(async () => setQueue(await call<AssignedReview[]>(clinicalPaths.assigned())));

  const [copied, setCopied] = useState(false);
  const copyIssued = async () => {
    if (!issuedToken) return;
    try {
      await navigator.clipboard.writeText(issuedToken);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const TABS: { id: Tab; label: string; hint: string }[] = [
    { id: "reviews", label: "Assigned reviews", hint: "Statements and fact confirmations patients asked you for" },
    { id: "transcriptions", label: "Transcriptions", hint: "Unclear prescription readings" },
    { id: "safety", label: "Safety governance", hint: "Red-flag rules and their approval" },
  ];

  return (
    <div className="rv-page">
      <div className="lp-backdrop" aria-hidden="true" />

      <header className="header-bar">
        <div className="container header-inner">
          <Link href="/" className="rv-back">
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
              <path d="M19 12H5M11 6l-6 6 6 6" />
            </svg>
            ArogyaRakshak
          </Link>
          <div className="nav-actions">
            <DemoPill status={demoStatus} />
            {me && (
              <span className="rv-signed-chip" title={`Signed in as ${me.name}`}>
                <span className="reviewer-status-dot" aria-hidden="true" />
                {me.name}
              </span>
            )}
            <button
              type="button"
              className="theme-toggle-btn"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                {theme === "dark" ? (
                  <>
                    <circle cx="12" cy="12" r="4" />
                    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                  </>
                ) : (
                  <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="container rv-main">
        <DemoBanner status={demoStatus} />

        <section className="rv-hero" aria-labelledby="rv-title">
          <p className="lp-kicker">Reviewer workspace</p>
          <h1 id="rv-title" className="lp-heading">
            Clinical Reviewer Workspace
          </h1>
          <p className="lp-section-lede">
            For doctors, pharmacists, medical transcriptionists and trained annotators. You see only the evidence a patient chose
            to share with you, and everything you write is attributed to you with your declared conflict of interest. Your
            registration is shown to patients exactly as verified — self-declared details are labelled as such.
          </p>
        </section>

        {error && <StatePanel kind="error">{error}</StatePanel>}
        {notice && <StatePanel kind="success">{notice}</StatePanel>}

        {!me && <SignInPanel guard={guard} openWithCredential={openWithCredential} onIssued={setIssuedToken} />}

        {issuedToken && (
          <section role="status" className="case-panel bn-card rv-issued" aria-labelledby="rv-issued-title">
            <h3 id="rv-issued-title">Your reviewer credential — shown once, store it now</h3>
            <p className="bn-fine">
              ArogyaRakshak does not keep a copy you can retrieve. Without it you cannot open this workspace again.
            </p>
            <code className="rv-token">{issuedToken}</code>
            <div className="bn-actions-row">
              <button type="button" className="btn btn-secondary btn-compact" onClick={() => void copyIssued()}>
                {copied ? "Copied" : "Copy credential"}
              </button>
              <button type="button" className="btn btn-ghost btn-compact" onClick={() => setIssuedToken(null)}>
                I have stored it
              </button>
            </div>
          </section>
        )}

        {me && (
          <>
            <section className="case-panel bn-card rv-profile" aria-label="Signed-in reviewer">
              <div className="rv-profile-main">
                <div className="stat-label">Signed in as</div>
                <ReviewerAttribution reviewer={me} />
                {me.is_safety_board_member && <span className={TONE_CLASS.neutral}>Clinical safety board member</span>}
              </div>
              <div className="rv-profile-side">
                <p className="rv-id">
                  Your reviewer ID: <code>{me.id}</code> — give it to your patient so they can assign you. Only independently
                  verified reviewers appear in the public list.
                </p>
                <p className="bn-fine">
                  Verification limits: ArogyaRakshak is not connected to any medical or pharmacy council registry. Patients see
                  your registration exactly as labelled here —{" "}
                  {me.verification_status === "DEMO_VERIFIED" ? "a demo fixture, not a real check" : "self-declared, not verified"}.
                </p>
              </div>
            </section>

            <nav className="rv-tabs" role="tablist" aria-label="Workspace sections">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  className={`rv-tab ${tab === t.id ? "is-active" : ""}`}
                  onClick={() => {
                    setTab(t.id);
                    // Transcriptions and safety load when their tab mounts.
                    if (t.id === "reviews") void refreshQueue();
                  }}
                >
                  <strong>{t.label}</strong>
                  <span>
                    {t.id === "reviews" && queue.length > 0 ? `${queue.length} assigned · ` : ""}
                    {t.hint}
                  </span>
                </button>
              ))}
            </nav>

            <div role="tabpanel" className="rv-tabpanel">
              {tab === "reviews" && <ReviewsTab guard={guard} call={call} queue={queue} setQueue={setQueue} refreshQueue={refreshQueue} />}
              {tab === "transcriptions" && <TranscriptionTab guard={guard} call={call} />}
              {tab === "safety" && <SafetyTab guard={guard} call={call} me={me} />}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
