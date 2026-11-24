"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { PipelineStep } from "../AgentStreamVisualizer";
import { useAccount } from "../../hooks/useAccount";
import { useActiveCase } from "../../hooks/useCases";
import { CaseApiError, deleteCase, fetchCaseDetail, openCaseStream, uploadDocument, type CaseEntity, type CaseSummary } from "../../lib/caseApi";
import { clearActiveCase, removeGuestCase, type CaseRef } from "../../lib/caseStore";
import { refreshAccount } from "../../lib/session";

// A processing stream silent for this long is reported as "taking longer than expected".
const PROCESSING_SILENCE_MS = 90_000;

/** Why the open case cannot be shown (from the API's answer, never guessed). */
export type CaseProblem = "gone" | "forbidden" | "signed-out" | "unreachable" | null;

export interface CaseContextValue {
  /** False during the server render and hydration: sessionStorage has not been read yet. */
  hydrated: boolean;
  ref: CaseRef | null;
  detail: { case: CaseSummary; entities: CaseEntity[] } | null;
  detailLoading: boolean;
  problem: CaseProblem;
  problemText: string | null;
  step: PipelineStep;
  processing: boolean;
  liveLog: string;
  processingError: string | null;
  streamIssue: "lost" | "timeout" | null;
  /** Extraction finished: module checks and the overview may read the case. */
  ready: boolean;
  /** Bumped whenever the case changes server-side, so views re-read it. */
  version: number;
  reconnect: () => void;
  addDocument: (file: File) => Promise<void>;
  removeCase: () => Promise<void>;
}

const CaseContext = createContext<CaseContextValue | null>(null);

const noop = () => () => {};
function useHydrated(): boolean {
  return useSyncExternalStore(noop, () => true, () => false);
}

export function useCase(): CaseContextValue {
  const v = useContext(CaseContext);
  if (!v) throw new Error("useCase must be used inside <CaseProvider>");
  return v;
}

function stepFor(status: string): PipelineStep | null {
  if (status === "upload_received" || status === "ocr_start") return 1;
  if (status === "extraction_start") return 2;
  if (["database_write", "entity_resolution", "transcription_flags", "module_checks"].includes(status)) return 3;
  return null;
}

/**
 * The open case for every /app/case route (overview, the five checks, reports). Lives in the
 * /app/case layout, so moving between those pages keeps the processing stream and the loaded case.
 * The case comes from sessionStorage (lib/caseStore), never from the URL.
 */
export function CaseProvider({ children }: { children: React.ReactNode }) {
  const hydrated = useHydrated();
  const ref = useActiveCase();
  const account = useAccount();
  const [detail, setDetail] = useState<CaseContextValue["detail"]>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [problem, setProblem] = useState<CaseProblem>(null);
  const [problemText, setProblemText] = useState<string | null>(null);
  const [step, setStep] = useState<PipelineStep>(0);
  const [processing, setProcessing] = useState(false);
  const [liveLog, setLiveLog] = useState("");
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [streamIssue, setStreamIssue] = useState<"lost" | "timeout" | null>(null);
  const [version, setVersion] = useState(0);
  const streamRef = useRef<EventSource | null>(null);
  const silence = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refKey = ref ? `${ref.id}|${ref.owned}` : "";

  const clearSilence = () => {
    if (silence.current) clearTimeout(silence.current);
    silence.current = null;
  };

  const connect = useCallback((r: CaseRef) => {
    streamRef.current?.close();
    setStreamIssue(null);
    const es = openCaseStream(r);
    streamRef.current = es;
    let settled = false;
    const arm = () => {
      clearSilence();
      silence.current = setTimeout(() => {
        if (!settled) setStreamIssue("timeout");
      }, PROCESSING_SILENCE_MS);
    };
    arm();
    es.onmessage = (event) => {
      let payload: { status?: string; log?: string };
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      arm();
      setStreamIssue(null);
      const status = String(payload.status ?? "");
      if (payload.log) setLiveLog(payload.log);
      const s = stepFor(status);
      if (s) {
        setStep(s);
        setProcessing(true);
      } else if (status === "completed" || status === "idle" || status === "duplicate") {
        settled = true;
        clearSilence();
        setStep(4);
        setProcessing(false);
        setVersion((v) => v + 1);
        es.close();
      } else if (status === "timeout") {
        settled = true;
        clearSilence();
        setStreamIssue("timeout");
        es.close();
      } else if (status === "failed" || status === "interrupted") {
        settled = true;
        clearSilence();
        setProcessing(false);
        setStep(4);
        setProcessingError(payload.log || null);
        es.close();
      }
    };
    es.onerror = () => {
      es.close();
      if (!settled) {
        clearSilence();
        setStreamIssue("lost");
        // EventSource hides the HTTP status: ask whether the session is still alive.
        if (r.owned) void refreshAccount();
      }
    };
  }, []);

  // Load the case and follow its processing whenever the open case changes.
  useEffect(() => {
    if (!ref) {
      streamRef.current?.close();
      return;
    }
    let cancelled = false;
    // Resetting for a different case (the open case lives in sessionStorage, an external store).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDetail(null);
    setProblem(null);
    setProblemText(null);
    setProcessingError(null);
    setStep(0);
    setLiveLog("");
    setDetailLoading(true);
    fetchCaseDetail(ref)
      .then((d) => {
        if (cancelled) return;
        setDetail(d);
        connect(ref);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const status = err instanceof CaseApiError ? err.status : 0;
        setProblemText(err instanceof Error ? err.message : null);
        setProblem(status === 404 ? "gone" : status === 403 ? "forbidden" : status === 401 ? "signed-out" : "unreachable");
      })
      .finally(() => !cancelled && setDetailLoading(false));
    return () => {
      cancelled = true;
      streamRef.current?.close();
      clearSilence();
    };
    // refKey captures id + owned; the token never changes for a given guest case.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refKey, connect]);

  // Re-read the case (entities, total) after each completed processing run.
  useEffect(() => {
    if (!ref || version === 0) return;
    let cancelled = false;
    fetchCaseDetail(ref)
      .then((d) => !cancelled && setDetail(d))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version]);

  // An owned case cannot be opened once the session is gone.
  const sessionGone = !!ref?.owned && (account.status === "expired" || account.status === "signed-out");

  const reconnect = useCallback(() => {
    if (ref) connect(ref);
  }, [ref, connect]);

  const addDocument = useCallback(
    async (file: File) => {
      if (!ref) return;
      setProcessingError(null);
      setProcessing(true);
      setStep(1);
      setLiveLog("");
      try {
        await uploadDocument(ref, file);
        connect(ref);
      } catch (err) {
        setProcessing(false);
        setStep(4);
        setProcessingError(err instanceof Error ? err.message : null);
        throw err;
      }
    },
    [ref, connect],
  );

  const removeCase = useCallback(async () => {
    if (!ref) return;
    await deleteCase(ref);
    streamRef.current?.close();
    clearSilence();
    if (!ref.owned) removeGuestCase(ref.id);
    clearActiveCase();
  }, [ref]);

  const value = useMemo<CaseContextValue>(
    () => ({
      hydrated,
      ref,
      detail,
      detailLoading,
      problem: sessionGone ? "signed-out" : problem,
      problemText,
      step,
      processing,
      liveLog,
      processingError,
      streamIssue,
      ready: !!ref && !!detail && step === 4 && !processing && !sessionGone,
      version,
      reconnect,
      addDocument,
      removeCase,
    }),
    [hydrated, ref, detail, detailLoading, sessionGone, problem, problemText, step, processing, liveLog, processingError, streamIssue, version, reconnect, addDocument, removeCase],
  );

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
}
