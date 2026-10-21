"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "../lib/apiBase";
import type { PipelineStep } from "../components/AgentStreamVisualizer";
import type { DemoScenario, DemoScenarioResult } from "../lib/demo";

// A processing stream silent for this long is reported as "taking longer than expected".
const PROCESSING_SILENCE_MS = 90_000;

/**
 * The patient's case for this tab: creation with consent, document upload, the live
 * processing stream (SSE), adding documents, demo scenario loading and deletion.
 * Extracted from the home page so the page only lays out what this state drives.
 */
export function useCaseSession({ consentRequiredMessage }: { consentRequiredMessage: string }) {
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
  // Bumped whenever the case changes server-side (a document added, a scenario loaded), so
  // the timeline re-reads it.
  const [caseVersion, setCaseVersion] = useState(0);
  // SEC-03: the server also purges a case automatically once its retention deadline
  // passes (app/case_retention.py — does not depend on the patient coming back), but
  // this lets them ask for the same real erasure DELETE /cases/{id} already performs
  // (P1-10) right now, from the UI, instead of only via a direct API call.
  const [isDeletingCase, setIsDeletingCase] = useState<boolean>(false);

  const clearSilenceTimer = () => {
    if (silenceTimer.current) clearTimeout(silenceTimer.current);
    silenceTimer.current = null;
  };

  const connectStream = useCallback((id: string, token: string) => {
    streamRef.current?.close();
    setStreamIssue(null);
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

  const handleDeleteCase = async () => {
    if (!caseId || !caseToken) return;
    const confirmed = window.confirm(
      "Delete this case permanently? This removes everything derived from it — extracted entities, audits, and any generated documents. This cannot be undone."
    );
    if (!confirmed) return;

    setIsDeletingCase(true);
    setErrorMessage(null);
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
      setErrorMessage(consentRequiredMessage);
      return;
    }

    setActiveFileName(fileName || file.name);
    setIsProcessing(true);
    setPipelineStep(1);
    setErrorMessage(null);
    setLiveLog("Initializing case session with Kadi layer...");

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
      // when nothing had actually happened. An upload failure must be reported honestly,
      // not disguised (see AuditResponse's not_benchmarked state, the 422s in DaaviSetu/
      // BillNyay, etc.).
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
  // replayed from the server's status stream.
  const handleScenarioLoaded = (result: DemoScenarioResult, scenario: DemoScenario) => {
    resetCaseView();
    setErrorMessage(null);
    setCaseId(result.case_id);
    setCaseToken(result.access_token);
    setActiveFileName(result.documents.join(" + "));
    setIsProcessing(true);
    setPipelineStep(1);
    setLiveLog(`Demo Scenario ${scenario.id} loaded — reading its processing log…`);
    setCaseVersion((v) => v + 1);
    connectStream(result.case_id, result.access_token);
  };

  // A case can hold several documents (e.g. a bill and its discharge summary); both feed
  // the same entities, plausibility check and evidence packet.
  const handleAddDocument = async (file: File | undefined) => {
    if (!file || !caseId || !caseToken || isProcessing) return;
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
    }
  };

  const caseReady = !!caseId && pipelineStep === 4 && !isProcessing;

  return {
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
  };
}
