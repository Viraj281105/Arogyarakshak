"use client";

import React, { useCallback, useState } from "react";
import Link from "next/link";
import { ReviewerProfile, clinicalPaths, clinicalRequest } from "../lib/clinical";
import { ReviewerAttribution } from "../components/clinical/Attribution";
import { StatePanel } from "../components/clinical/StatePanel";
import { DemoBanner, useDemoStatus } from "../components/demo/DemoBanner";
import { TONE_CLASS } from "../lib/labels";
import { ReviewsTab } from "./components/ReviewsTab";
import { SafetyTab } from "./components/SafetyTab";
import { SignInPanel } from "./components/SignInPanel";
import { TranscriptionTab } from "./components/TranscriptionTab";
import { AssignedReview, ReviewerCall, Tab, panel } from "./types";

/** Reviewer workspace: credential + profile, then three tabs (assigned reviews,
 *  transcriptions, safety governance). Each tab owns its own state. */
export default function ClinicalReviewWorkspace() {
  // Held in memory only: the credential is a bearer secret and is never written to
  // localStorage. Reloading the page means pasting it again.
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

  return (
    <main className="container" style={{ paddingTop: "1.5rem", paddingBottom: "3rem" }}>
      <DemoBanner status={demoStatus} />
      <p>
        <Link href="/">← Back to ArogyaRakshak</Link>
      </p>
      <h1 style={{ marginBottom: "0.25rem" }}>Clinical Reviewer Workspace</h1>
      <p style={{ fontSize: "0.9rem", maxWidth: 760 }}>
        For doctors, pharmacists, medical transcriptionists and trained annotators. You see only the evidence a patient chose
        to share with you, and everything you write is attributed to you with your declared conflict of interest. Your
        registration is shown to patients exactly as verified — self-declared details are labelled as such.
      </p>

      {error && <StatePanel kind="error">{error}</StatePanel>}
      {notice && <StatePanel kind="success">{notice}</StatePanel>}

      {!me && <SignInPanel guard={guard} openWithCredential={openWithCredential} onIssued={setIssuedToken} />}

      {issuedToken && (
        <div role="status" style={{ ...panel, borderColor: "var(--status-warning)" }}>
          <strong>Your reviewer credential (shown once — store it now):</strong>
          <code style={{ display: "block", wordBreak: "break-all", marginTop: "0.5rem" }}>{issuedToken}</code>
          <button type="button" className="btn" style={{ marginTop: "0.5rem", border: "1px solid var(--border-subtle)" }} onClick={() => setIssuedToken(null)}>
            I have stored it
          </button>
        </div>
      )}

      {me && (
        <>
          <section style={panel}>
            <div className="stat-label">Signed in as</div>
            <ReviewerAttribution reviewer={me} />
            {me.is_safety_board_member && <span className={TONE_CLASS.neutral}>Clinical safety board member</span>}
            <p style={{ fontSize: "0.8rem", marginTop: "0.5rem", opacity: 0.9 }}>
              Verification limits: ArogyaRakshak is not connected to any medical or pharmacy council registry. Patients see your
              registration exactly as labelled above — {me.verification_status === "DEMO_VERIFIED" ? "a demo fixture, not a real check" : "self-declared, not verified"}.
            </p>
            <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
              Your reviewer ID: <code>{me.id}</code> — give it to your patient so they can assign you. Only independently
              verified reviewers appear in the public list.
            </p>
          </section>

          <nav className="module-tabs" role="tablist" aria-label="Workspace sections">
            {(["reviews", "transcriptions", "safety"] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => {
                  setTab(t);
                  // Transcriptions and safety load when their tab mounts.
                  if (t === "reviews") void refreshQueue();
                }}
              >
                {t === "reviews" ? "Assigned reviews" : t === "transcriptions" ? "Transcriptions" : "Safety governance"}
              </button>
            ))}
          </nav>

          {tab === "reviews" && <ReviewsTab guard={guard} call={call} queue={queue} setQueue={setQueue} refreshQueue={refreshQueue} />}
          {tab === "transcriptions" && <TranscriptionTab guard={guard} call={call} />}
          {tab === "safety" && <SafetyTab guard={guard} call={call} me={me} />}
        </>
      )}
    </main>
  );
}
