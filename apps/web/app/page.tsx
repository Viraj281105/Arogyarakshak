"use client";

import React, { useState } from "react";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { DocumentUploader } from "./components/DocumentUploader";
import { AgentStreamVisualizer, PipelineStep } from "./components/AgentStreamVisualizer";
import { BillNyayView } from "./components/modules/BillNyayView";
import { BimaNyayView } from "./components/modules/BimaNyayView";
import { DaaviSetuView } from "./components/modules/DaaviSetuView";
import { SchemeSetuView } from "./components/modules/SchemeSetuView";
import { DawaCheckView } from "./components/modules/DawaCheckView";
import { Language, translations } from "./translations";

type ModuleTab = "billnyay" | "bimanyay" | "daavisetu" | "schemesetu" | "dawacheck";

export default function Home() {
  const [currentLang, setCurrentLang] = useState<Language>("en");
  const [activeTab, setActiveTab] = useState<ModuleTab>("billnyay");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>(0);
  const [activeFileName, setActiveFileName] = useState<string>("");

  const t = translations[currentLang];

  const handleStartAudit = (fileName: string) => {
    setActiveFileName(fileName);
    setIsProcessing(true);
    setPipelineStep(1);

    // Simulate multi-agent SSE streaming stages
    setTimeout(() => setPipelineStep(2), 700);
    setTimeout(() => setPipelineStep(3), 1400);
    setTimeout(() => {
      setPipelineStep(4);
      setIsProcessing(false);
    }, 2100);
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header currentLang={currentLang} onLanguageChange={setCurrentLang} />

      <main className="container" style={{ flex: 1 }}>
        {/* Hero Section */}
        <section className="hero-section">
          <h1>
            <span className="hero-gradient-text">{t.appName}</span>
          </h1>
          <p style={{ marginTop: "0.5rem", maxWidth: "680px", marginLeft: "auto", marginRight: "auto" }}>
            {t.tagline}
          </p>
        </section>

        {/* BYOD Document Intake Dropzone */}
        <DocumentUploader
          currentLang={currentLang}
          onStartAudit={handleStartAudit}
          isProcessing={isProcessing}
        />

        {/* Live SSE Multi-Agent Stream Visualizer (if active or just completed) */}
        {pipelineStep > 0 && (
          <AgentStreamVisualizer
            currentLang={currentLang}
            currentStep={pipelineStep}
            activeFileName={activeFileName}
          />
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
          {activeTab === "billnyay" && <BillNyayView currentLang={currentLang} />}
          {activeTab === "bimanyay" && <BimaNyayView currentLang={currentLang} />}
          {activeTab === "daavisetu" && <DaaviSetuView currentLang={currentLang} />}
          {activeTab === "schemesetu" && <SchemeSetuView currentLang={currentLang} />}
          {activeTab === "dawacheck" && <DawaCheckView currentLang={currentLang} />}
        </div>
      </main>

      <Footer currentLang={currentLang} />
    </div>
  );
}
