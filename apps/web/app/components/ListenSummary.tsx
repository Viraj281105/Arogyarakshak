"use client";

import React, { useEffect, useRef, useState } from "react";
import type { Language } from "../translations";
import { listenCopy } from "../lib/listenCopy";
import { fill, type Summary } from "../lib/listenSummaries";
import { getListenAvailability, speakWithVoice, type UtteranceLike } from "../lib/speech";
import { useInstalledVoices, useSimpleLanguage, useSpeechSupported } from "../hooks/useListen";

export type ListenPanelKind = "deadline" | "readiness" | "medicine" | "appeal";

/**
 * Visible summary (standard or simple wording) with Listen / Stop buttons. What is read aloud is
 * exactly the text shown. Uses only the browser's on-device speech voices (ADR-015); when none
 * exists for the language the buttons are replaced by an honest message, never a cloud voice.
 * Never starts by itself.
 */
export const ListenSummary: React.FC<{ lang: Language; panel: ListenPanelKind; summary: Summary }> = ({ lang, panel, summary }) => {
  const ui = listenCopy[lang].ui;
  const panelTitle = listenCopy[lang].panels[panel];
  const simple = useSimpleLanguage();
  const supported = useSpeechSupported();
  const voices = useInstalledVoices();
  const availability = getListenAvailability(supported, voices, lang);
  const [speaking, setSpeaking] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);
  const text = simple ? summary.simple : summary.standard;

  const stop = () => {
    stopRef.current?.();
    stopRef.current = null;
    setSpeaking(false);
  };

  // Changing text, language or mode, or leaving the panel, silences any ongoing speech.
  useEffect(() => {
    return () => {
      stopRef.current?.();
      stopRef.current = null;
    };
  }, [text, lang]);

  const listen = () => {
    if (availability.status !== "ready") return;
    stop();
    setSpeaking(true);
    stopRef.current = speakWithVoice(
      {
        speak: (u) => window.speechSynthesis.speak(u as unknown as SpeechSynthesisUtterance),
        cancel: () => window.speechSynthesis.cancel(),
      },
      (t) => new SpeechSynthesisUtterance(t) as UtteranceLike<SpeechSynthesisVoice>,
      availability.voice,
      text,
      lang,
      { onDone: () => setSpeaking(false), onError: () => setSpeaking(false) }
    );
  };

  return (
    <div
      className="card"
      role="group"
      aria-label={`${ui.summaryLabel}: ${panelTitle}`}
      style={{ margin: "0.75rem 0", padding: "0.75rem 1rem" }}
      lang={lang}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", justifyContent: "space-between" }}>
        <strong style={{ fontSize: "0.9rem" }}>
          {ui.summaryLabel}: {panelTitle}
        </strong>
        {availability.status === "ready" && (
          <span style={{ display: "flex", gap: "0.5rem" }}>
            <button type="button" className="btn btn-secondary btn-compact" onClick={listen} disabled={speaking} aria-label={fill(ui.listenAria, { panel: panelTitle })}>
              🔊 {ui.listen}
            </button>
            <button type="button" className="btn btn-secondary btn-compact" onClick={stop} disabled={!speaking} aria-label={ui.stopAria}>
              ⏹ {ui.stop}
            </button>
          </span>
        )}
      </div>
      <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", lineHeight: 1.6 }}>{text}</p>
      <p role="status" style={{ margin: "0.4rem 0 0", fontSize: "0.78rem", opacity: 0.85 }}>
        {availability.status === "ready" && (speaking ? ui.reading : ui.onDeviceNote)}
        {availability.status === "no-local-voice" && ui.noLocalVoice}
        {availability.status === "unsupported" && ui.unsupported}
      </p>
    </div>
  );
};
