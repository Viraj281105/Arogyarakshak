"use client";

import { useSyncExternalStore } from "react";
import type { VoiceLike } from "../lib/speech";

// --- "Simple language" preference (per-viewer convenience; stored only in this browser) ----------

const SIMPLE_KEY = "arogyarakshak.simpleLanguage";
const simpleListeners = new Set<() => void>();
let simpleValue: boolean | null = null;

function readSimple(): boolean {
  if (simpleValue === null) {
    try {
      simpleValue = window.localStorage.getItem(SIMPLE_KEY) === "1";
    } catch {
      simpleValue = false;
    }
  }
  return simpleValue;
}

export function setSimpleLanguage(on: boolean): void {
  simpleValue = on;
  try {
    window.localStorage.setItem(SIMPLE_KEY, on ? "1" : "0");
  } catch {
    // Storage can be unavailable (private window); the choice then lasts until reload.
  }
  simpleListeners.forEach((l) => l());
}

export function useSimpleLanguage(): boolean {
  return useSyncExternalStore(
    (cb) => {
      simpleListeners.add(cb);
      return () => simpleListeners.delete(cb);
    },
    readSimple,
    () => false
  );
}

// --- Read-aloud on/off (Settings page; per-viewer convenience stored only in this browser) -------

const READ_ALOUD_KEY = "arogyarakshak.readAloud";
const readAloudListeners = new Set<() => void>();
let readAloudValue: boolean | null = null;

function readReadAloud(): boolean {
  if (readAloudValue === null) {
    try {
      readAloudValue = window.localStorage.getItem(READ_ALOUD_KEY) !== "off";
    } catch {
      readAloudValue = true;
    }
  }
  return readAloudValue;
}

export function setReadAloudEnabled(on: boolean): void {
  readAloudValue = on;
  try {
    if (on) window.localStorage.removeItem(READ_ALOUD_KEY);
    else window.localStorage.setItem(READ_ALOUD_KEY, "off");
  } catch {
    // storage unavailable: the choice lasts until reload
  }
  if (!on && typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
  readAloudListeners.forEach((l) => l());
}

/** Whether the Listen buttons are offered (on unless turned off in Settings). */
export function useReadAloudEnabled(): boolean {
  return useSyncExternalStore(
    (cb) => {
      readAloudListeners.add(cb);
      return () => readAloudListeners.delete(cb);
    },
    readReadAloud,
    () => true
  );
}

// --- Installed speech voices ---------------------------------------------------------------------

const EMPTY_VOICES: SpeechSynthesisVoice[] = [];
let voiceSnapshot: SpeechSynthesisVoice[] = EMPTY_VOICES;

function refreshVoices(): void {
  voiceSnapshot = typeof window !== "undefined" && "speechSynthesis" in window ? window.speechSynthesis.getVoices() : EMPTY_VOICES;
}

function subscribeVoices(cb: () => void): () => void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return () => undefined;
  const synth = window.speechSynthesis;
  const onChange = () => {
    refreshVoices();
    cb();
  };
  refreshVoices();
  synth.addEventListener("voiceschanged", onChange);
  return () => synth.removeEventListener("voiceschanged", onChange);
}

/** Installed voices (list may grow after load; the browser fires `voiceschanged`). */
export function useInstalledVoices(): readonly (SpeechSynthesisVoice & VoiceLike)[] {
  return useSyncExternalStore(subscribeVoices, () => voiceSnapshot, () => EMPTY_VOICES);
}

export function useSpeechSupported(): boolean {
  return useSyncExternalStore(
    () => () => undefined,
    () => "speechSynthesis" in window,
    () => true
  );
}
