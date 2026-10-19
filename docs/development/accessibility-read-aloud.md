# Read-aloud and simple language (web)

Decision and rationale: [ADR-016](../architecture/decisions/ADR-016-on-device-read-aloud.md).

## What users see
- A **Simple language** checkbox under the demo banner (per browser).
- A **Summary** box with **Listen** / **Stop** buttons on four panels: BimaNyay deadlines, BimaNyay
  appeal, DaaviSetu document check (after "Check documentation readiness"), DawaCheck result.
- If the browser has no on-device voice for the chosen language, or no speech support at all, the
  buttons are absent and the box says so. Audio never starts by itself.

## Where the code is
| File | Role |
|---|---|
| `app/lib/speech.ts` | Local-voice selection, availability, text sanitiser (markup/emoji, INR → rupees, abbreviations), chunking, `speakWithVoice` |
| `app/lib/listenCopy.ts` | Static en/hi/mr strings in `standard` and `simple` registers (hi/mr: `NEEDS NATIVE-SPEAKER QA`) |
| `app/lib/listenSummaries.ts` | Pure builders that turn structured result fields into a summary |
| `app/hooks/useListen.ts` | `useSyncExternalStore` hooks: simple-language preference, installed voices |
| `app/components/ListenSummary.tsx`, `SimpleLanguageToggle.tsx` | UI |
| `tests/listen.test.ts` | Voice selection, refusal of remote voices, sanitiser, copy parity, builders, no-network source guard |

## Adding a summary
1. Add the sentences to `ListenCopy` (all three languages; keep `{placeholders}` identical).
2. Add a builder in `listenSummaries.ts` that uses structured fields only.
3. Render `<ListenSummary lang panel summary />` in the view. Do not pass server free text.

## Rules
- Never select a voice with `localService !== true`; never use `SpeechRecognition`.
- Do not speak a verdict whose figures are missing; do not speak a percentage unless labelled heuristic.
- Check in a browser: Chrome/Edge on Windows list local voices under Settings → Time & language →
  Speech; Marathi often has none. `speechSynthesis.getVoices().map(v => [v.lang, v.localService])`
  in the console shows what the page can use.
