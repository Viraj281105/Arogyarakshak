# ADR-015: On-device read-aloud and simple-language summaries

- **Status:** Accepted (2026-10-19)
- **Context:** Many patients and caregivers read slowly, read mainly Hindi or Marathi, or have low
  vision. The result panels (deadlines, document check, medicine price, appeal) are dense. A
  "Listen" button helps, but the text spoken here can contain medicine names, amounts and claim
  stage — health information. Browser text-to-speech has a privacy trap: on Chrome, voices with
  `localService === false` (for example "Google हिन्दी") stream the text to a remote server. The
  project's network boundary (`AGENTS.md` §1) allows only Groq, the local Postgres and the official
  package registries, and ADR-003 keeps patient content off third parties.
- **Decision:**
  1. Use only `window.speechSynthesis`, and only a voice whose `localService` is `true`
     (`selectLocalVoice` in `apps/web/app/lib/speech.ts`). `speakWithVoice` takes the voice as a
     required argument and throws on a non-local one, so the engine's default voice (possibly
     remote) can never be reached.
  2. If no on-device voice exists for the selected language — common for Marathi — the Listen/Stop
     buttons are not rendered and the panel says "No on-device voice for this language…". There is
     no fallback to a cloud voice and no other language is substituted.
  3. **No speech recognition** (Chrome's `SpeechRecognition` sends audio to a remote server) and no
     third-party TTS package or service.
  4. What is spoken is a short summary composed from **curated static strings** filled with
     structured fields (counts, dates, amounts, statuses) — never server free text, an LLM output
     or a runtime translation. The summary is shown on screen, so the person sees exactly what is
     read. A "Simple language" switch selects a second, shorter register of the same sentences.
  5. Strings live in `apps/web/app/lib/listenCopy.ts` with the same en/hi/mr shape. Hindi and
     Marathi are flagged `NEEDS NATIVE-SPEAKER QA`; `tests/listen.test.ts` enforces key and
     `{placeholder}` parity and the flag.
  6. Playback never starts by itself; Stop is always available while speaking; speech stops when
     the text, language or panel changes. The Simple-language choice is a per-browser convenience in
     `localStorage` (try/catch guarded) and is never sent anywhere.
- **Consequences:**
  - Marathi (and sometimes Hindi) users on browsers/OSes without an installed local voice get the
    on-screen summary but no audio. This is the honest outcome; installing a system voice enables it.
  - Summaries do not read server free text (appeal letter bodies, document labels), so they carry
    less detail than the screen. They say what the figures are, not why.
  - Heuristic figures are only spoken together with the sentence that says they are a rule-based
    estimate, not a probability from past cases (and not at all if the server did not label them so).
  - Voice quality depends on the device. Pronunciation of mixed-script names is not controlled.
- **Not verified:** actual audio playback with a real local voice (the embedded test browser had no
  voices). Selection, refusal, sanitising, chunking, copy parity and rendering are unit/browser tested.
- **Alternatives rejected:** cloud TTS (network boundary, ADR-003); server-side TTS (new service,
  patient text leaves the device); LLM "plain language" rewriting (no-fabrication rule, Groq cost, and
  unreviewable output in a medical-administrative context); voice input (remote recognition).
