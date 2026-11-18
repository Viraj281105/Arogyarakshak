"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { DOCUMENT_ACCEPT, DocumentUploader } from "./components/DocumentUploader";
import { DemoBanner, DemoPill, useDemoStatus } from "./components/demo/DemoBanner";
import { SimpleLanguageToggle } from "./components/SimpleLanguageToggle";
import type { DemoScenario, DemoScenarioResult } from "./lib/demo";
import { ModuleTab, ModuleTabs } from "./components/ModuleTabs";
import { StatePanel } from "./components/clinical/StatePanel";
import { BillNyayView } from "./components/modules/BillNyayView";
import { useCaseSession } from "./hooks/useCaseSession";

// Code-split (WS4): none of these is on screen at first paint. Inactive module tabs load when
// opened; the case desk loads once a case exists; demo controls load only in demo mode.
// BillNyayView stays static because it is the default tab and renders immediately.
const BimaNyayView = dynamic(() => import("./components/modules/BimaNyayView").then((m) => m.BimaNyayView));
const DaaviSetuView = dynamic(() => import("./components/modules/DaaviSetuView").then((m) => m.DaaviSetuView));
const SchemeSetuView = dynamic(() => import("./components/modules/SchemeSetuView").then((m) => m.SchemeSetuView));
const DawaCheckView = dynamic(() => import("./components/modules/DawaCheckView").then((m) => m.DawaCheckView));
const AgentStreamVisualizer = dynamic(() =>
  import("./components/AgentStreamVisualizer").then((m) => m.AgentStreamVisualizer)
);
const SafetyEscalationBanner = dynamic(() =>
  import("./components/clinical/SafetyEscalationBanner").then((m) => m.SafetyEscalationBanner)
);
const EntityResolutionReview = dynamic(() =>
  import("./components/EntityResolutionReview").then((m) => m.EntityResolutionReview)
);
const ClaimPackPanel = dynamic(() => import("./components/ClaimPackPanel").then((m) => m.ClaimPackPanel));
const CaseTimeline = dynamic(() => import("./components/CaseTimeline").then((m) => m.CaseTimeline));
const DemoControls = dynamic(() => import("./components/demo/DemoControls").then((m) => m.DemoControls));
import { translations } from "./translations";
import { useHeaderSlot, useLanguage } from "./shell/ShellProvider";
import { moduleFromHash } from "./shell/nav";
import { Landing } from "./components/landing/Landing";

// The module each demo scenario starts in.
const SCENARIO_TAB: Record<DemoScenario["id"], ModuleTab> = { A: "billnyay", B: "daavisetu", C: "dawacheck", D: "bimanyay", E: "daavisetu" };

export default function Home() {
  const [currentLang] = useLanguage();
  const [activeTab, setActiveTab] = useState<ModuleTab>("billnyay");
  const demoStatus = useDemoStatus();
  useHeaderSlot(useMemo(() => <DemoPill status={demoStatus} />, [demoStatus]));
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

  // A landing-page module card opens that tab and brings the workspace into view. No explicit
  // `behavior`: the CSS scroll-behavior decides, which is instant under reduced motion.
  const openModule = (tab: ModuleTab) => {
    setActiveTab(tab);
    document.getElementById("module-workspace")?.scrollIntoView({ block: "start" });
  };

  // Shell deep links (#module-<id>, from the header drawer or another page) open that check.
  useEffect(() => {
    const apply = () => {
      const tab = moduleFromHash(window.location.hash);
      if (!tab) return;
      setActiveTab(tab);
      document.getElementById("module-workspace")?.scrollIntoView({ block: "start" });
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, []);

  // When a document starts processing, bring the case workspace into view.
  const processingStarted = pipelineStep === 1 && isProcessing;
  React.useEffect(() => {
    if (processingStarted) document.getElementById("case-desk")?.scrollIntoView({ block: "start" });
  }, [processingStarted]);

  const onAddDocument = async (file: File | undefined) => {
    try {
      await handleAddDocument(file);
    } finally {
      if (addDocInput.current) addDocInput.current.value = "";
    }
  };

  return (
    <>
      <div className="lp-backdrop" aria-hidden="true" />

      <div className="container">
        <DemoBanner status={demoStatus} />

        <Landing t={t} onOpenModule={openModule} />

        {demoStatus?.demo_mode && <DemoControls status={demoStatus} onScenarioLoaded={onScenarioLoaded} onReset={resetCaseView} />}

        {/* BYOD Document Intake Dropzone */}
        <div id="intake-dropzone" className="lp-intake">
          <DocumentUploader
            currentLang={currentLang}
            onStartAudit={handleStartAudit}
            isProcessing={isProcessing}
          />
        </div>

        {/* Error Alert Display */}
        {errorMessage && (
          <div style={{ marginBottom: "1.5rem" }}>
            <StatePanel kind="error">{errorMessage}</StatePanel>
          </div>
        )}

        {/* The patient's case: progress, safety, questions, history and the claim pack */}
        {(caseId || pipelineStep > 0) && (
          <section id="case-desk" className="case-desk" aria-labelledby="case-desk-title">
            <header className="case-desk-head">
              <div className="case-desk-title">
                <p className="lp-kicker">Your case</p>
                <h2 id="case-desk-title">
                  {caseReady ? "Your document has been read" : isProcessing ? "Reading your document…" : "Processing stopped"}
                </h2>
                {activeFileName && (
                  <p className="case-file">
                    <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                      <path d="M6 3h8l4 4v14H6zM14 3v4h4" />
                    </svg>
                    <span>{activeFileName}</span>
                  </p>
                )}
              </div>

              {/* SEC-03: explicit patient-initiated case deletion */}
              {caseId && (
                <div className="case-actions">
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
                    <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                    Add another document
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger-outline btn-compact"
                    onClick={handleDeleteCase}
                    disabled={isDeletingCase}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                      <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" />
                    </svg>
                    {isDeletingCase ? "Deleting…" : "Delete this case & all data"}
                  </button>
                </div>
              )}
            </header>

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

            <div className="case-desk-grid">
              <div className="case-desk-main">
                {/* Processing progress, from the server's status stream only */}
                {pipelineStep > 0 && (
                  <AgentStreamVisualizer
                    currentLang={currentLang}
                    currentStep={pipelineStep}
                    activeFileName={activeFileName}
                    caseId={caseId}
                    liveLog={liveLog}
                  />
                )}

                {/* ADR-011: red-flag escalations from active, board-approved safety rules */}
                {pipelineStep === 4 && !isProcessing && caseId && (
                  <SafetyEscalationBanner key={`safety-${caseId}`} caseId={caseId} caseToken={caseToken} />
                )}

                {/* Entity-resolution questions Kadi could not decide on its own (#31) */}
                {pipelineStep === 4 && !isProcessing && caseId && (
                  <EntityResolutionReview key={caseId} caseId={caseId} caseToken={caseToken} currentLang={currentLang} />
                )}

                {/* ADR-015: one downloadable pack for the person helping with the paperwork */}
                {pipelineStep === 4 && !isProcessing && caseId && (
                  <ClaimPackPanel key={`pack-${caseId}`} caseId={caseId} caseToken={caseToken} />
                )}
              </div>

              {/* What has actually happened to this case, from persisted records only */}
              {caseId && (
                <div className="case-desk-side">
                  <CaseTimeline caseId={caseId} caseToken={caseToken} refreshKey={caseVersion} processing={isProcessing} failure={errorMessage} />
                </div>
              )}
            </div>

            {caseReady && (
              <a href="#module-workspace" className="case-next">
                Next: open a check on this case
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" className="lp-icon">
                  <path d="M12 5v14M5 12l7 7 7-7" />
                </svg>
              </a>
            )}
          </section>
        )}

        <div id="module-workspace" className="module-workspace-head">
          <SimpleLanguageToggle lang={currentLang} />
          <ModuleTabs active={activeTab} onSelect={setActiveTab} t={t} />
        </div>

        {/* Active Module Panel */}
        <div role="tabpanel" id={`panel-${activeTab}`} aria-labelledby={`tab-${activeTab}`} tabIndex={0}>
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
      </div>
    </>
  );
}
