"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { DOCUMENT_ACCEPT, DocumentUploader } from "./components/DocumentUploader";
import { DemoBanner, useDemoStatus } from "./components/demo/DemoBanner";
import { DemoControls } from "./components/demo/DemoControls";
import { CaseTimeline } from "./components/CaseTimeline";
import type { DemoScenario, DemoScenarioResult } from "./lib/demo";
import { AgentStreamVisualizer, PipelineStep } from "./components/AgentStreamVisualizer";
import { EntityResolutionReview } from "./components/EntityResolutionReview";
import { SafetyEscalationBanner } from "./components/clinical/SafetyEscalationBanner";
import { StatePanel } from "./components/clinical/StatePanel";
import { BillNyayView } from "./components/modules/BillNyayView";
import { BimaNyayView } from "./components/modules/BimaNyayView";
import { DaaviSetuView } from "./components/modules/DaaviSetuView";
import { SchemeSetuView } from "./components/modules/SchemeSetuView";
import { DawaCheckView } from "./components/modules/DawaCheckView";
import { Language, translations } from "./translations";

type ModuleTab = "billnyay" | "bimanyay" | "daavisetu" | "schemesetu" | "dawacheck";

// The module each demo scenario starts in.
const SCENARIO_TAB: Record<DemoScenario["id"], ModuleTab> = { A: "billnyay", B: "daavisetu", C: "dawacheck", D: "bimanyay", E: "daavisetu" };

// A processing stream silent for this long is reported as "taking longer than expected".
const PROCESSING_SILENCE_MS = 90_000;

export default function Home() {
  const [currentLang, setCurrentLang] = useState<Language>("en");
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("arogyarakshak_theme") as "dark" | "light" | null;
        if (saved) return saved;
        if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
          return "light";
        }
      } catch {
        // Fallback
      }
    }
    return "dark";
  });

  const [activeTab, setActiveTab] = useState<ModuleTab>("billnyay");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>(0);
  const [activeFileName, setActiveFileName] = useState<string>("");
  const [caseId, setCaseId] = useState<string>("");
  // ADR-009: the case's one-time access token, captured from the case-creation
  // response and held only in memory for this tab's session. Required on every
  // subsequent case-scoped request — a case id alone is no longer sufficient.
  const [caseToken, setCaseToken] = useState<string>("");
  const [liveLog, setLiveLog] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Processing stream health: a dropped or silent stream is shown as such, with a way to
  // refresh — never as completion.
  const [streamIssue, setStreamIssue] = useState<"lost" | "timeout" | null>(null);
  const streamRef = useRef<EventSource | null>(null);
  const silenceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const demoStatus = useDemoStatus();
  // Bumped whenever the case changes server-side (a document added, a scenario loaded), so
  // the timeline re-reads it.
  const [caseVersion, setCaseVersion] = useState(0);
  const addDocInput = useRef<HTMLInputElement | null>(null);

  const clearSilenceTimer = () => {
    if (silenceTimer.current) clearTimeout(silenceTimer.current);
    silenceTimer.current = null;
  };

  const connectStream = useCallback((id: string, token: string) => {
    streamRef.current?.close();
    setStreamIssue(null);
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // The browser's native EventSource cannot set custom headers, so the token travels via
    // query string here only (ADR-009) — every other request uses the X-Case-Access-Token header.
    const es = new EventSource(`${API_BASE}/api/v1/kadi/cases/${id}/stream?access_token=${encodeURIComponent(token)}`);
    streamRef.current = es;
    let settled = false;
    const armSilenceTimer = () => {
      clearSilenceTimer();
      silenceTimer.current = setTimeout(() => {
        if (!settled) setStreamIssue("timeout");
      }, PROCESSING_SILENCE_MS);
    };
    armSilenceTimer();

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        armSilenceTimer();
        setStreamIssue(null);
        if (payload.log) {
          setLiveLog(payload.log);
        }
        if (payload.status === "upload_received" || payload.status === "ocr_start") {
          setPipelineStep(1);
        } else if (payload.status === "extraction_start") {
          setPipelineStep(2);
        } else if (payload.status === "database_write" || payload.status === "entity_resolution" || payload.status === "transcription_flags" || payload.status === "module_checks") {
          setPipelineStep(3);
        } else if (payload.status === "completed" || payload.status === "idle") {
          settled = true;
          clearSilenceTimer();
          setPipelineStep(4);
          setIsProcessing(false);
          setCaseVersion((v) => v + 1);
          // The backend log says when a document was a duplicate or which module checks ran.
          setLiveLog(payload.log || "Document processed successfully. Entities extracted.");
          es.close();
        } else if (payload.status === "timeout") {
          settled = true;
          clearSilenceTimer();
          setStreamIssue("timeout");
          es.close();
        } else if (payload.status === "failed") {
          settled = true;
          clearSilenceTimer();
          setErrorMessage(payload.log || "Document processing failed");
          setIsProcessing(false);
          es.close();
        }
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    };

    es.onerror = () => {
      es.close();
      if (!settled) {
        clearSilenceTimer();
        setStreamIssue("lost");
      }
    };
  }, []);

  useEffect(
    () => () => {
      streamRef.current?.close();
      clearSilenceTimer();
    },
    []
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const handleThemeToggle = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    try {
      localStorage.setItem("arogyarakshak_theme", nextTheme);
    } catch {
      // Ignore
    }
  };

  const t = translations[currentLang];
  const caseReady = !!caseId && pipelineStep === 4 && !isProcessing;
  const readyCaseId = caseReady ? caseId : "";

  // SEC-03: the server also purges a case automatically once its retention deadline
  // passes (app/case_retention.py — does not depend on the patient coming back), but
  // this lets them ask for the same real erasure DELETE /cases/{id} already performs
  // (P1-10) right now, from the UI, instead of only via a direct API call.
  const [isDeletingCase, setIsDeletingCase] = useState<boolean>(false);

  const handleDeleteCase = async () => {
    if (!caseId || !caseToken) return;
    const confirmed = window.confirm(
      "Delete this case permanently? This removes everything derived from it — extracted entities, audits, and any generated documents. This cannot be undone."
    );
    if (!confirmed) return;

    setIsDeletingCase(true);
    setErrorMessage(null);
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const res = await fetch(`${API_BASE}/api/v1/kadi/cases/${caseId}`, {
        method: "DELETE",
        headers: { "X-Case-Access-Token": caseToken },
      });
      if (!res.ok && res.status !== 204) {
        throw new Error(`Delete failed: HTTP ${res.status}`);
      }
      streamRef.current?.close();
      clearSilenceTimer();
      setStreamIssue(null);
      setIsProcessing(false);
      setCaseId("");
      setCaseToken("");
      setPipelineStep(0);
      setActiveFileName("");
      setLiveLog("");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to delete this case.");
    } finally {
      setIsDeletingCase(false);
    }
  };

  const handleStartAudit = async (
    file: File | null,
    fileName: string,
    consentGiven: boolean
  ) => {
    if (!file) {
      setErrorMessage("Please select or drop a valid document file before starting the audit.");
      return;
    }

    if (!consentGiven) {
      setErrorMessage(t.upload.consentRequired);
      return;
    }

    setActiveFileName(fileName || file.name);
    setIsProcessing(true);
    setPipelineStep(1);
    setErrorMessage(null);
    setLiveLog("Initializing case session with Kadi layer...");

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      // 1. Create patient case session in Kadi
      const caseRes = await fetch(`${API_BASE}/api/v1/kadi/cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent_opt_in: consentGiven }),
      });

      if (!caseRes.ok) {
        throw new Error(`API /kadi/cases returned HTTP ${caseRes.status}`);
      }

      const caseData = await caseRes.json();
      const newCaseId: string = caseData.id;
      const newCaseToken: string = caseData.access_token;
      setCaseId(newCaseId);
      setCaseToken(newCaseToken);
      setLiveLog("Case created. Uploading document for transient OCR...");

      // 2. Upload document to /kadi/cases/{case_id}/upload
      const formData = new FormData();
      formData.append("file", file);

      const uploadRes = await fetch(`${API_BASE}/api/v1/kadi/cases/${newCaseId}/upload`, {
        method: "POST",
        headers: { "X-Case-Access-Token": newCaseToken },
        body: formData,
      });

      if (!uploadRes.ok) {
        throw new Error(`API /upload returned HTTP ${uploadRes.status}`);
      }

      // 3. Connect real-time Server-Sent Events (SSE) stream.
      setLiveLog("Document received. Listening to live multi-agent SSE status stream...");
      connectStream(newCaseId, newCaseToken);
    } catch (err) {
      // Previously fell back to a fake "simulated audit" here — animating the pipeline
      // to a green "completed" state and telling the user their document was processed
      // when nothing had actually happened. That is exactly the kind of fabricated
      // successful result the rest of this project explicitly refuses to produce
      // elsewhere (see AuditResponse's not_benchmarked state, the 422s in DaaviSetu/
      // BillNyay, etc.) — an upload failure must be reported honestly, not disguised.
      console.error("Document upload/processing failed:", err);
      setPipelineStep(0);
      setIsProcessing(false);
      setErrorMessage(
        err instanceof Error
          ? `Could not process your document: ${err.message}`
          : "Could not process your document. Please check your connection and try again."
      );
      setLiveLog("");
    }
  };

  const resetCaseView = () => {
    streamRef.current?.close();
    clearSilenceTimer();
    setStreamIssue(null);
    setIsProcessing(false);
    setCaseId("");
    setCaseToken("");
    setPipelineStep(0);
    setActiveFileName("");
    setLiveLog("");
  };

  // Demo kit: a scenario arrives as an already-processed case; its processing log is
  // replayed from the server's status stream, and the scenario's module opens.
  const handleScenarioLoaded = (result: DemoScenarioResult, scenario: DemoScenario) => {
    resetCaseView();
    setErrorMessage(null);
    setCaseId(result.case_id);
    setCaseToken(result.access_token);
    setActiveFileName(result.documents.join(" + "));
    setIsProcessing(true);
    setPipelineStep(1);
    setLiveLog(`Demo Scenario ${scenario.id} loaded — reading its processing log…`);
    setActiveTab(SCENARIO_TAB[scenario.id]);
    setCaseVersion((v) => v + 1);
    connectStream(result.case_id, result.access_token);
  };

  // A case can hold several documents (e.g. a bill and its discharge summary); both feed
  // the same entities, plausibility check and evidence packet.
  const handleAddDocument = async (file: File | undefined) => {
    if (!file || !caseId || !caseToken || isProcessing) return;
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    setErrorMessage(null);
    setActiveFileName(file.name);
    setIsProcessing(true);
    setPipelineStep(1);
    setLiveLog("Adding a document to this case...");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/api/v1/kadi/cases/${caseId}/upload`, {
        method: "POST",
        headers: { "X-Case-Access-Token": caseToken },
        body: formData,
      });
      if (!res.ok) throw new Error(`API /upload returned HTTP ${res.status}`);
      connectStream(caseId, caseToken);
    } catch (err) {
      setIsProcessing(false);
      setPipelineStep(4);
      setErrorMessage(err instanceof Error ? `Could not add the document: ${err.message}` : "Could not add the document.");
    } finally {
      if (addDocInput.current) addDocInput.current.value = "";
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header
        currentLang={currentLang}
        onLanguageChange={setCurrentLang}
        currentTheme={theme}
        onThemeToggle={handleThemeToggle}
      />

      <main className="container" style={{ flex: 1 }}>
        <DemoBanner status={demoStatus} />
        {/* Hero Section */}
        <section className="hero-section">
          <h1>
            <span className="hero-gradient-text">{t.appName}</span>
          </h1>
          <p style={{ marginTop: "0.5rem", maxWidth: "680px", marginLeft: "auto", marginRight: "auto" }}>
            {t.tagline}
          </p>
          <p style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
            Clinician, pharmacist or transcription reviewer? <Link href="/clinical-review">Open the reviewer workspace →</Link>
          </p>
        </section>

        <DemoControls status={demoStatus} onScenarioLoaded={handleScenarioLoaded} onReset={resetCaseView} />

        {/* BYOD Document Intake Dropzone */}
        <DocumentUploader
          currentLang={currentLang}
          onStartAudit={handleStartAudit}
          isProcessing={isProcessing}
        />

        {/* Error Alert Display */}
        {errorMessage && (
          <div
            style={{
              padding: "1rem",
              marginBottom: "1.5rem",
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid var(--status-danger)",
              borderRadius: "var(--radius-md)",
              color: "#fca5a5",
              fontSize: "0.9rem",
            }}
          >
            ⚠️ {errorMessage}
          </div>
        )}

        {streamIssue && caseId && (
          <StatePanel
            kind="warning"
            onRetry={() => connectStream(caseId, caseToken)}
            retryLabel="Refresh status"
          >
            {streamIssue === "timeout"
              ? "Processing is taking longer than expected. Your document may still be being read — nothing has been checked yet."
              : "Lost contact with the processing status stream. Your document may still be processing."}
          </StatePanel>
        )}

        {/* Live SSE Multi-Agent Stream Visualizer */}
        {pipelineStep > 0 && (
          <AgentStreamVisualizer
            currentLang={currentLang}
            currentStep={pipelineStep}
            activeFileName={activeFileName}
            caseId={caseId}
            liveLog={liveLog}
          />
        )}

        {/* What has actually happened to this case, from persisted records only */}
        {caseId && (
          <CaseTimeline caseId={caseId} caseToken={caseToken} refreshKey={caseVersion} processing={isProcessing} failure={errorMessage} />
        )}

        {/* ADR-011: red-flag escalations from active, board-approved safety rules */}
        {pipelineStep === 4 && !isProcessing && caseId && (
          <SafetyEscalationBanner key={`safety-${caseId}`} caseId={caseId} caseToken={caseToken} />
        )}

        {/* Entity-resolution questions Kadi could not decide on its own (#31) */}
        {pipelineStep === 4 && !isProcessing && caseId && (
          <EntityResolutionReview key={caseId} caseId={caseId} caseToken={caseToken} currentLang={currentLang} />
        )}

        {/* SEC-03: explicit patient-initiated case deletion */}
        {caseId && (
          <div style={{ display: "flex", justifyContent: "flex-end", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
            <input
              ref={addDocInput}
              type="file"
              accept={DOCUMENT_ACCEPT}
              style={{ display: "none" }}
              aria-label="Add another document to this case"
              onChange={(e) => handleAddDocument(e.target.files?.[0])}
            />
            <button
              type="button"
              className="btn btn-secondary btn-compact"
              disabled={!caseReady}
              title={caseReady ? undefined : "Available once the current document has finished processing"}
              onClick={() => addDocInput.current?.click()}
            >
              ➕ Add another document to this case
            </button>
            <button
              type="button"
              onClick={handleDeleteCase}
              disabled={isDeletingCase}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--status-danger)",
                background: "transparent",
                color: "var(--status-danger)",
                fontSize: "0.85rem",
                cursor: isDeletingCase ? "not-allowed" : "pointer",
                opacity: isDeletingCase ? 0.6 : 1,
              }}
            >
              {isDeletingCase ? "Deleting…" : "🗑 Delete this case & all data"}
            </button>
          </div>
        )}


        {/* Module Tab Navigation (Mobile Touch-Friendly Scroll) */}
        <nav className="module-tabs" role="tablist" aria-label="Feature Modules">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "billnyay"}
            className={`tab-btn ${activeTab === "billnyay" ? "active" : ""}`}
            onClick={() => setActiveTab("billnyay")}
          >
            📊 {t.tabs.billnyay}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "bimanyay"}
            className={`tab-btn ${activeTab === "bimanyay" ? "active" : ""}`}
            onClick={() => setActiveTab("bimanyay")}
          >
            🛡️ {t.tabs.bimanyay}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "daavisetu"}
            className={`tab-btn ${activeTab === "daavisetu" ? "active" : ""}`}
            onClick={() => setActiveTab("daavisetu")}
          >
            📋 {t.tabs.daavisetu}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "schemesetu"}
            className={`tab-btn ${activeTab === "schemesetu" ? "active" : ""}`}
            onClick={() => setActiveTab("schemesetu")}
          >
            🏛️ {t.tabs.schemesetu}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "dawacheck"}
            className={`tab-btn ${activeTab === "dawacheck" ? "active" : ""}`}
            onClick={() => setActiveTab("dawacheck")}
          >
            💊 {t.tabs.dawacheck}
          </button>
        </nav>

        {/* Active Module Panel */}
        <div role="tabpanel" id={`panel-${activeTab}`}>
          {/* Module views receive the case only once extraction has finished, so nothing is
              computed (or shown as "empty") from a half-built case. */}
          {caseId && !caseReady && (
            <StatePanel kind="loading">
              Your document is still being processed. Case results appear here as soon as extraction finishes.
            </StatePanel>
          )}
          {activeTab === "billnyay" && <BillNyayView currentLang={currentLang} caseId={readyCaseId} caseToken={caseToken} />}
          {activeTab === "bimanyay" && <BimaNyayView currentLang={currentLang} caseId={readyCaseId} caseToken={caseToken} />}
          {activeTab === "daavisetu" && <DaaviSetuView currentLang={currentLang} caseId={readyCaseId} caseToken={caseToken} />}
          {activeTab === "schemesetu" && <SchemeSetuView currentLang={currentLang} caseId={readyCaseId} caseToken={caseToken} />}
          {activeTab === "dawacheck" && <DawaCheckView currentLang={currentLang} caseId={readyCaseId} caseToken={caseToken} />}
        </div>
      </main>

      <Footer currentLang={currentLang} />
    </div>
  );
}
