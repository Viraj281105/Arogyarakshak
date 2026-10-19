import { test, describe } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import type { Language } from "../app/translations";
import { listenCopy } from "../app/lib/listenCopy";
import {
  getListenAvailability,
  sanitizeForSpeech,
  selectLocalVoice,
  speakWithVoice,
  splitIntoChunks,
  type UtteranceLike,
  type VoiceLike,
} from "../app/lib/speech";
import {
  buildAppealSummary,
  buildDeadlineSummary,
  buildMedicineSummary,
  buildReadinessSummary,
  formatSpokenDate,
} from "../app/lib/listenSummaries";

const LANGS: Language[] = ["en", "hi", "mr"];
const v = (name: string, lang: string, localService: boolean, def = false): VoiceLike => ({ name, lang, localService, default: def });

/** Flattens an object tree into "a.b.c" -> string leaves. */
function leaves(o: unknown, prefix = ""): Record<string, string> {
  if (typeof o === "string") return { [prefix]: o };
  return Object.entries(o as Record<string, unknown>).reduce(
    (acc, [k, val]) => ({ ...acc, ...leaves(val, prefix ? `${prefix}.${k}` : k) }),
    {}
  );
}
const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");
const makeUtterance = (text: string): UtteranceLike<VoiceLike> => ({ text, lang: "", voice: null, rate: 1, onend: null, onerror: null });

describe("voice selection (on-device only)", () => {
  test("prefers a local voice with the exact regional tag", () => {
    const voices = [v("A", "hi-IN", true), v("B", "en-US", true), v("C", "en-IN", true)];
    assert.strictEqual(selectLocalVoice(voices, "en")?.name, "C");
  });

  test("falls back to another local voice of the same language", () => {
    assert.strictEqual(selectLocalVoice([v("US", "en-US", true)], "en")?.name, "US");
  });

  test("refuses remote-only voices even when they are the only voice for the language", () => {
    const voices = [v("Google Hindi", "hi-IN", false), v("Google Marathi", "mr-IN", false)];
    assert.strictEqual(selectLocalVoice(voices, "hi"), null);
    assert.strictEqual(selectLocalVoice(voices, "mr"), null);
  });

  test("ignores a remote default voice when a local one exists", () => {
    const voices = [v("Remote", "hi-IN", false, true), v("Local", "hi-IN", true)];
    assert.strictEqual(selectLocalVoice(voices, "hi")?.name, "Local");
  });

  test("underscore tags and other languages are handled", () => {
    assert.strictEqual(selectLocalVoice([v("x", "mr_IN", true)], "mr")?.name, "x");
    assert.strictEqual(selectLocalVoice([v("x", "hi-IN", true)], "mr"), null);
  });

  test("availability: unsupported, no-local-voice, ready", () => {
    assert.strictEqual(getListenAvailability(false, [v("a", "en-IN", true)], "en").status, "unsupported");
    assert.strictEqual(getListenAvailability(true, [], "mr").status, "no-local-voice");
    assert.strictEqual(getListenAvailability(true, [v("a", "mr-IN", false)], "mr").status, "no-local-voice");
    assert.strictEqual(getListenAvailability(true, [v("a", "en-IN", true)], "en").status, "ready");
  });

  test("speakWithVoice refuses a non-local voice and uses the chosen voice otherwise", () => {
    const spoken: UtteranceLike<VoiceLike>[] = [];
    const synth = {
      speak: (u: UtteranceLike<VoiceLike>) => {
        spoken.push(u);
        u.onend?.();
      },
      cancel: () => undefined,
    };
    assert.throws(() => speakWithVoice(synth, makeUtterance, v("R", "en-IN", false), "Hello.", "en"));
    assert.strictEqual(spoken.length, 0);
    let done = false;
    const local = v("L", "en-IN", true);
    speakWithVoice(synth, makeUtterance, local, "First sentence. Second sentence.", "en", { onDone: () => (done = true) });
    assert.ok(spoken.length >= 1 && spoken.every((u) => u.voice === local && u.lang === "en-IN"));
    assert.ok(done);
  });

  test("stop prevents later chunks", () => {
    const spoken: string[] = [];
    let pending: (() => void) | null = null;
    const synth = {
      speak: (u: UtteranceLike<VoiceLike>) => {
        spoken.push(u.text);
        pending = () => u.onend?.();
      },
      cancel: () => undefined,
    };
    const long = Array.from({ length: 20 }, (_, i) => `Sentence number ${i} is here.`).join(" ");
    const stop = speakWithVoice(synth, makeUtterance, v("L", "en-IN", true), long, "en");
    stop();
    (pending as (() => void) | null)?.();
    assert.strictEqual(spoken.length, 1);
  });
});

describe("text sanitiser", () => {
  test("strips markup, markdown and emoji", () => {
    assert.strictEqual(sanitizeForSpeech("<b>Hello</b> 💊 **world** ✓ [link](http://x.y) `code`"), "Hello world link code");
  });

  test("expands rupee amounts and INR", () => {
    assert.strictEqual(sanitizeForSpeech("Billed ₹33.00 and INR 1,200 or 500 INR"), "Billed 33.00 rupees and 1200 rupees or 500 rupees");
    assert.strictEqual(sanitizeForSpeech("Rs. 40", "hi"), "40 रुपये");
  });

  test("expands abbreviations", () => {
    assert.strictEqual(sanitizeForSpeech("MRP above NPPA ceiling"), "maximum retail price above N P P A ceiling");
    assert.strictEqual(sanitizeForSpeech("IRDAI GRO"), "I R D A I G R O");
  });

  test("collapses whitespace and keeps Devanagari punctuation", () => {
    assert.strictEqual(sanitizeForSpeech("  नमस्ते \n\n दुनिया  ।", "hi"), "नमस्ते दुनिया।");
  });

  test("splits long text into bounded chunks", () => {
    const text = Array.from({ length: 30 }, (_, i) => `Sentence number ${i} is here.`).join(" ");
    const chunks = splitIntoChunks(text, 100);
    assert.ok(chunks.length > 1);
    chunks.forEach((c) => assert.ok(c.length <= 100, `chunk too long: ${c.length}`));
    assert.strictEqual(chunks.join(" ").replace(/\s+/g, " "), text);
  });
});

describe("plain-language copy parity (en/hi/mr)", () => {
  const flat = Object.fromEntries(LANGS.map((l) => [l, leaves(listenCopy[l])])) as Record<Language, Record<string, string>>;

  test("every language has exactly the same keys, all non-empty", () => {
    const enKeys = Object.keys(flat.en).sort();
    for (const l of ["hi", "mr"] as const) {
      assert.deepStrictEqual(Object.keys(flat[l]).sort(), enKeys, `${l} keys differ from en`);
    }
    for (const l of LANGS) for (const [k, s] of Object.entries(flat[l])) assert.ok(s.trim().length > 0, `empty ${l}.${k}`);
  });

  test("placeholders match the English string for every key", () => {
    for (const l of ["hi", "mr"] as const) {
      for (const [k, s] of Object.entries(flat[l])) {
        assert.strictEqual(placeholders(s), placeholders(flat.en[k]), `${l}.${k} placeholders differ`);
      }
    }
  });

  test("hi/mr strings are written in Devanagari, not left in English", () => {
    for (const l of ["hi", "mr"] as const) {
      for (const [k, s] of Object.entries(flat[l])) {
        if (s.replace(/\{\w+\}|[\s.]/g, "") === "") continue; // pure placeholder frame
        assert.ok(/[ऀ-ॿ]/.test(s), `${l}.${k} has no Devanagari text`);
      }
    }
  });

  test("copy file carries the NEEDS NATIVE-SPEAKER QA flag for hi and mr", () => {
    const src = fs.readFileSync(path.join(__dirname, "..", "app", "lib", "listenCopy.ts"), "utf-8");
    assert.ok(src.includes("NEEDS NATIVE-SPEAKER QA"));
    assert.ok(src.includes("hi: {\n    // NEEDS NATIVE-SPEAKER QA"));
    assert.ok(src.includes("mr: {\n    // NEEDS NATIVE-SPEAKER QA"));
  });

  test("the heuristic-estimate caveat keeps its figure in every language and register", () => {
    for (const l of LANGS) {
      assert.ok(listenCopy[l].appeal.estimate.standard.includes("{pct}"));
      assert.ok(listenCopy[l].appeal.estimate.simple.includes("{pct}"));
    }
  });
});

describe("summary builders", () => {
  test("deadline summary uses structured fields, localises the date, and handles unknown tiers", () => {
    const s = buildDeadlineSummary(
      [
        { tier: "LEVEL_1_GRO", status: "ACTIVE", deadline_date: "2026-11-12" },
        { tier: "SOMETHING_NEW", status: "WEIRD", deadline_date: null },
      ],
      "en"
    );
    assert.ok(s.standard.includes("12 November 2026"));
    assert.ok(s.simple.includes("Do this now"));
    assert.ok(s.simple.includes("Step 2."));
    assert.ok(!/\{\w+\}/.test(s.standard + s.simple), "unfilled placeholder");
    assert.strictEqual(formatSpokenDate("not a date", "en"), "not a date");
  });

  test("readiness summary counts statuses and never predicts approval", () => {
    const items = [
      { status: "PRESENT" },
      { status: "CONFIRMED_BY_REVIEWER" },
      { status: "MISSING" },
      { status: "NEEDS_CLINICAL_CONFIRMATION" },
    ];
    for (const l of LANGS) {
      const s = buildReadinessSummary(items, l);
      assert.ok(!/\{\w+\}/.test(s.standard + s.simple));
      assert.ok(s.standard.includes("2") && s.standard.includes("4"));
    }
    assert.ok(buildReadinessSummary(items, "en").standard.includes("does not predict"));
    assert.ok(buildReadinessSummary([{ status: "PRESENT" }], "en").standard.includes("No documents are missing"));
  });

  test("medicine summary refuses to state a verdict without figures", () => {
    const base = { brandName: "Dolo", activeIngredient: "Paracetamol" };
    const above = buildMedicineSummary({ ...base, verdict: "above", billedUnitPrice: 3.5, ceilingUnitPrice: 2.3 }, "en");
    assert.ok(above.standard.includes("3.50") && above.standard.includes("above the ceiling"));
    const none = buildMedicineSummary({ ...base, verdict: "above" }, "en");
    assert.ok(!none.standard.includes("above the ceiling"));
    assert.ok(none.standard.includes("no comparison"));
    const cannot = buildMedicineSummary({ ...base, verdict: "cannot_compare", billedUnitPrice: 1, ceilingUnitPrice: 1 }, "hi");
    assert.ok(!cannot.standard.includes("1.00"));
  });

  test("appeal summary only speaks the percentage when it is a labelled heuristic", () => {
    const heuristic = buildAppealSummary({ isWrongfulDenial: true, violationCount: 2, reversalScore: 0.72, heuristic: true }, "en");
    assert.ok(heuristic.standard.includes("72 percent") && heuristic.standard.includes("not a probability from past cases"));
    const unlabelled = buildAppealSummary({ isWrongfulDenial: false, violationCount: 0, reversalScore: 0.72, heuristic: false }, "en");
    assert.ok(!unlabelled.standard.includes("72"));
    for (const l of LANGS) {
      const s = buildAppealSummary({ isWrongfulDenial: true, violationCount: 1, reversalScore: 0.5, heuristic: true }, l);
      assert.ok(!/\{\w+\}/.test(s.standard + s.simple));
    }
  });
});

describe("privacy guard: no network speech paths in the client", () => {
  test("source never uses speech recognition or remote TTS", () => {
    const files = ["app/lib/speech.ts", "app/hooks/useListen.ts", "app/components/ListenSummary.tsx", "app/components/SimpleLanguageToggle.tsx"];
    for (const f of files) {
      const src = fs
        .readFileSync(path.join(__dirname, "..", f), "utf-8")
        .split("\n")
        .filter((line) => !line.trim().startsWith("*") && !line.trim().startsWith("//") && !line.trim().startsWith("/*"))
        .join("\n");
      assert.ok(!/SpeechRecognition|fetch\(|XMLHttpRequest|https?:\/\//.test(src), `${f} has a network/recognition path`);
    }
  });
});
