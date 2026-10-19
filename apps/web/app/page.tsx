"use client";

import React, { useRef, useState } from "react";
import Link from "next/link";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { DOCUMENT_ACCEPT, DocumentUploader } from "./components/DocumentUploader";
import { DemoBanner, useDemoStatus } from "./components/demo/DemoBanner";
import { DemoControls } from "./components/demo/DemoControls";
import { CaseTimeline } from "./components/CaseTimeline";
import { SimpleLanguageToggle } from "./components/SimpleLanguageToggle";
import { ClaimPackPanel } from "./components/ClaimPackPanel";
import type { DemoScenario, DemoScenarioResult } from "./lib/demo";
import { AgentStreamVisualizer } from "./components/AgentStreamVisualizer";
import { EntityResolutionReview } from "./components/EntityResolutionReview";
import { ModuleTab, ModuleTabs } from "./components/ModuleTabs";
import { SafetyEscalationBanner } from "./components/clinical/SafetyEscalationBanner";
import { StatePanel } from "./components/clinical/StatePanel";
import { BillNyayView } from "./components/modules/BillNyayView";
import { BimaNyayView } from "./components/modules/BimaNyayView";
import { DaaviSetuView } from "./components/modules/DaaviSetuView";
import { SchemeSetuView } from "./components/modules/SchemeSetuView";
import { DawaCheckView } from "./components/modules/DawaCheckView";
import { useCaseSession } from "./hooks/useCaseSession";
import { useTheme } from "./hooks/useTheme";
import { Language, translations } from "./translations";

// The module each demo scenario starts in.
const SCENARIO_TAB: Record<DemoScenario["id"], ModuleTab> = { A: "billnyay", B: "daavisetu", C: "dawacheck", D: "bimanyay", E: "daavisetu" };

export default function Home() {
  const [currentLang, setCurrentLang] = useState<Language>("en");
  const { theme, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<ModuleTab>("billnyay");
  const demoStatus = useDemoStatus();
  const addDocInput = useRef<HTMLInputElement | null>(null);

  const t = translations[currentLang];
  const {
    caseId,
    caseToken,
    caseReady,
    caseVersion,
    isProcessing,
    isDeletingCase,
    pipelineStep,
    activeFileName,
    liveLog,
    errorMessage,
    streamIssue,
    connectStream,
    handleStartAudit,
    handleDeleteCase,
    handleAddDocument,
    handleScenarioLoaded,
    resetCaseView,
  } = useCaseSession({ consentRequiredMessage: t.upload.consentRequired });
  const readyCaseId = caseReady ? caseId : "";

  const onScenarioLoaded = (result: DemoScenarioResult, scenario: DemoScenario) => {
    handleScenarioLoaded(result, scenario);
    setActiveTab(SCENARIO_TAB[scenario.id]);
  };

  const onAddDocument = async (file: File | undefined) => {
    try {
      await handleAddDocument(file);
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
        onThemeToggle={toggleTheme}
      />

      <main className="container" style={{ flex: 1 }}>
        <DemoBanner status={demoStatus} />
        <SimpleLanguageToggle lang={currentLang} />
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

        <DemoControls status={demoStatus} onScenarioLoaded={onScenarioLoaded} onReset={resetCaseView} />

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

        {/* ADR-015: one downloadable pack for the person helping with the paperwork */}
        {pipelineStep === 4 && !isProcessing && caseId && (<ClaimPackPanel key={`pack-${caseId}`} caseId={caseId} caseToken={caseToken} />)}

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
              onChange={(e) => onAddDocument(e.target.files?.[0])}
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

        <ModuleTabs active={activeTab} onSelect={setActiveTab} t={t} />

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
