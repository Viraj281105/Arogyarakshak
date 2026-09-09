"use client";

import React, { useEffect, useState } from "react";
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
  const [liveLog, setLiveLog] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  const handleStartAudit = async (file: File | null, fileName: string) => {
    if (!file) {
      setErrorMessage("Please select or drop a valid document file before starting the audit.");
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
        body: JSON.stringify({ consent_opt_in: true }),
      });

      if (!caseRes.ok) {
        throw new Error(`API /kadi/cases returned HTTP ${caseRes.status}`);
      }

      const caseData = await caseRes.json();
      const newCaseId: string = caseData.id;
      setCaseId(newCaseId);
      setLiveLog(`Case ${newCaseId} created. Uploading document for transient OCR...`);

      // 2. Upload document to /kadi/cases/{case_id}/upload
      const formData = new FormData();
      formData.append("file", file);

      const uploadRes = await fetch(`${API_BASE}/api/v1/kadi/cases/${newCaseId}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) {
        throw new Error(`API /upload returned HTTP ${uploadRes.status}`);
      }

      // 3. Connect real-time Server-Sent Events (SSE) stream
      setLiveLog("Document received. Listening to live multi-agent SSE status stream...");
      const es = new EventSource(`${API_BASE}/api/v1/kadi/cases/${newCaseId}/stream`);

      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.log) {
            setLiveLog(payload.log);
          }

          if (payload.status === "upload_received" || payload.status === "ocr_start") {
            setPipelineStep(1);
          } else if (payload.status === "extraction_start") {
            setPipelineStep(2);
          } else if (payload.status === "database_write") {
            setPipelineStep(3);
          } else if (payload.status === "completed") {
            setPipelineStep(4);
            setIsProcessing(false);
            setLiveLog("Document processed successfully. Entities extracted.");
            es.close();
          } else if (payload.status === "failed") {
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
        setIsProcessing(false);
      };
    } catch (err) {
      console.warn("FastAPI backend unreachable or offline. Falling back to transient simulation:", err);
      setLiveLog("Backend offline — executing transient simulated audit (DPDP compliant)");
      setTimeout(() => setPipelineStep(2), 700);
      setTimeout(() => setPipelineStep(3), 1400);
      setTimeout(() => {
        setPipelineStep(4);
        setIsProcessing(false);
        setLiveLog("Transient audit completed.");
      }, 2100);
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
          {activeTab === "billnyay" && <BillNyayView currentLang={currentLang} caseId={caseId} />}
          {activeTab === "bimanyay" && <BimaNyayView currentLang={currentLang} />}
          {activeTab === "daavisetu" && <DaaviSetuView currentLang={currentLang} caseId={caseId} />}
          {activeTab === "schemesetu" && <SchemeSetuView currentLang={currentLang} />}
          {activeTab === "dawacheck" && <DawaCheckView currentLang={currentLang} />}
        </div>
      </main>

      <Footer currentLang={currentLang} />
    </div>
  );
}
