/**
 * On-device read-aloud helpers (ADR-015).
 *
 * Only the browser's built-in `speechSynthesis` is used, and only with voices that report
 * `localService === true`. A remote ("cloud") voice would send the text — which can contain
 * a patient's medicine names, claim details and amounts — to a third party, so such voices are
 * never selected: if no local voice exists for the language, reading aloud is unavailable.
 * Speech *recognition* is deliberately not used at all (it sends audio to a remote server in
 * Chrome). Everything here is pure or takes its browser objects as parameters, so it is
 * unit-tested without a browser.
 */

import type { Language } from "../translations";

/** The subset of `SpeechSynthesisVoice` this module reads. */
export interface VoiceLike {
  name: string;
  lang: string;
  localService: boolean;
  default?: boolean;
}

/** Preferred BCP-47 tag per UI language. */
export const SPEECH_LANG_TAG: Record<Language, string> = {
  en: "en-IN",
  hi: "hi-IN",
  mr: "mr-IN",
};

const primarySubtag = (tag: string) => tag.toLowerCase().replace("_", "-").split("-")[0];

/**
 * Picks an on-device voice for the language, or null. Remote-only voices are never returned,
 * even when they are the only voice for the language.
 */
export function selectLocalVoice<V extends VoiceLike>(voices: readonly V[], lang: Language): V | null {
  const wanted = primarySubtag(SPEECH_LANG_TAG[lang]);
  const local = voices.filter((v) => v.localService === true && primarySubtag(v.lang) === wanted);
  if (local.length === 0) return null;
  const exactTag = SPEECH_LANG_TAG[lang].toLowerCase();
  return (
    local.find((v) => v.lang.toLowerCase().replace("_", "-") === exactTag) ??
    local.find((v) => v.default) ??
    local[0]
  );
}

export type ListenAvailability<V extends VoiceLike = VoiceLike> =
  | { status: "ready"; voice: V }
  | { status: "unsupported" }
  | { status: "no-local-voice" };

/** `synthSupported` is false when `window.speechSynthesis` does not exist. */
export function getListenAvailability<V extends VoiceLike>(
  synthSupported: boolean,
  voices: readonly V[],
  lang: Language
): ListenAvailability<V> {
  if (!synthSupported) return { status: "unsupported" };
  const voice = selectLocalVoice(voices, lang);
  return voice ? { status: "ready", voice } : { status: "no-local-voice" };
}

// ---------------------------------------------------------------------------------------------
// Text preparation
// ---------------------------------------------------------------------------------------------

const RUPEES: Record<Language, string> = { en: "rupees", hi: "रुपये", mr: "रुपये" };

/** Initialisms read letter by letter (otherwise a voice may try to pronounce them as words). */
const SPELLED = ["IRDAI", "NPPA", "CGHS", "PMJAY", "MJPJAY", "GRO", "OCR", "TPA"];

// Emoji and pictographs, variation selectors, joiners, and the ✓/✗ marks used in checklists.
const EMOJI = /[\p{Extended_Pictographic}\u{FE0F}\u{200D}\u{20E3}✓✔✗✘]/gu;

/**
 * Turns on-screen text into something a speech engine reads cleanly: strips HTML/markdown and
 * emoji, spells out rupee amounts and a few abbreviations, and collapses whitespace.
 */
export function sanitizeForSpeech(input: string, lang: Language = "en"): string {
  const rupees = RUPEES[lang];
  let s = input
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, " and ")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*[-*•]\s+/gm, "")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/[*_~]{1,3}/g, " ")
    .replace(EMOJI, " ");

  // Amounts: "₹33.00", "Rs. 1,200", "INR 500", "500 INR".
  const spokenAmount = (_m: string, n: string) => `${n.replace(/,/g, "")} ${rupees}`;
  s = s
    .replace(/(?:₹|\bINR\b|\bRs\.?)\s*(\d[\d,]*(?:\.\d+)?)/gi, spokenAmount)
    .replace(/(\d[\d,]*(?:\.\d+)?)\s*(?:₹|\bINR\b|\bRs\b\.?)/gi, spokenAmount)
    .replace(/₹|\bINR\b/g, rupees);

  if (lang === "en") s = s.replace(/\bMRP\b/g, "maximum retail price");
  for (const a of SPELLED) s = s.replace(new RegExp(`\\b${a}\\b`, "g"), a.split("").join(" "));

  return s.replace(/\s+/g, " ").replace(/\s+([.,;:!?।])/g, "$1").trim();
}

/** Splits into sentence-sized chunks; long single utterances are cut off by some engines. */
export function splitIntoChunks(text: string, maxLen = 220): string[] {
  const sentences = text.match(/[^.!?।]+[.!?।]*\s*/g) ?? [text];
  const chunks: string[] = [];
  let current = "";
  const flush = () => {
    if (current.trim()) chunks.push(current.trim());
    current = "";
  };
  for (const raw of sentences) {
    let sentence = raw;
    while (sentence.length > maxLen) {
      const cut = sentence.lastIndexOf(" ", maxLen);
      const at = cut > 0 ? cut : maxLen;
      if (current && current.length + at > maxLen) flush();
      current += sentence.slice(0, at);
      flush();
      sentence = sentence.slice(at).trimStart();
    }
    if (current && current.length + sentence.length > maxLen) flush();
    current += sentence;
  }
  flush();
  return chunks;
}

// ---------------------------------------------------------------------------------------------
// Playback (browser objects injected)
// ---------------------------------------------------------------------------------------------

export interface SynthLike<V extends VoiceLike> {
  speak(u: UtteranceLike<V>): void;
  cancel(): void;
}
export interface UtteranceLike<V extends VoiceLike> {
  text: string;
  lang: string;
  voice: V | null;
  rate: number;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}

/**
 * Speaks `text` with the given on-device voice, one chunk at a time. Returns a `stop` function.
 * The voice is required (not optional) so a caller cannot reach the engine's default voice,
 * which may be a remote one.
 */
export function speakWithVoice<V extends VoiceLike>(
  synth: SynthLike<V>,
  makeUtterance: (text: string) => UtteranceLike<V>,
  voice: V,
  text: string,
  lang: Language,
  callbacks: { onDone?: () => void; onError?: () => void } = {}
): () => void {
  if (voice.localService !== true) throw new Error("Refusing to speak with a non-local voice");
  const chunks = splitIntoChunks(sanitizeForSpeech(text, lang));
  let stopped = false;
  synth.cancel();
  if (chunks.length === 0) {
    callbacks.onDone?.();
    return () => undefined;
  }
  const next = (i: number) => {
    if (stopped) return;
    if (i >= chunks.length) {
      callbacks.onDone?.();
      return;
    }
    const u = makeUtterance(chunks[i]);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = 0.95;
    u.onend = () => next(i + 1);
    u.onerror = () => {
      if (stopped) return;
      stopped = true;
      callbacks.onError?.();
    };
    synth.speak(u);
  };
  next(0);
  return () => {
    stopped = true;
    synth.cancel();
  };
}
