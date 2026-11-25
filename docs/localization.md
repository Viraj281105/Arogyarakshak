# Localisation: English, Hindi, Marathi

**Status, 2026-11-25:** every interface string the web and mobile code marks has a Hindi and a
Marathi translation. **All Hindi and Marathi text is machine translation (Claude) and has not been reviewed
by a native speaker.** No translation may be described as verified until it has been.

## 1. How it works (web)

The English sentence is the key (gettext style).

| Where | How |
|---|---|
| Client components | `const tr = useT();` then `tr("Delete {count} cases", { count })` |
| Server components | `const { tr } = await serverT();` |
| Strings kept in constants | `msg("Not found")` where defined, `tr(...)` where shown |
| Server-safe leaf components | `<T k="Data table" />` |
| Public site | `localisedPublicCopy(await requestLanguage())` translates `copy/en.ts` |
| Older module copy | `translations.ts`, `shell/shellCopy.ts`, `workspace/*Copy.ts`, `auth/authCopy.ts` hold their own `en`/`hi`/`mr` blocks |
| Dictionaries | `apps/web/app/i18n/locales/{hi,mr}.ts`, loaded as separate chunks (`i18n/load.ts`) |

A missing key shows the English sentence, never a blank or a key name. Placeholders are `{names}`.
Write whole sentences: do not join translated fragments, because word order differs.

**Choosing a language.** The header switcher writes the functional cookie `arogya_lang` (no
personal data). Server components read it, so the first paint is in the chosen language for
server-rendered text. Client components render English for a moment until their dictionary chunk
arrives. `<html lang>` follows the choice.

**Trade-off.** Because the root layout reads the cookie, every route is now rendered per request;
no page is statically generated. `/platform/<unknown>` still returns 404.

**Dates and numbers.** Use `LOCALE[lang]` from `i18n/format.ts` (`en-IN`, `hi-IN`,
`mr-IN-u-nu-latn`). Digits stay Latin so figures can be matched against documents. Rupee amounts use
Indian digit grouping.

## 1a. How it works (mobile)

| Where | How |
|---|---|
| Any code | `tr('Delete {count} cases', { count })` from `src/translations/tr.ts`; it reads the current language when called |
| Components that render such text | call `useTranslation()` so they redraw after a language change (`useLanguage()` also does) |
| Strings kept in constants | `msg('Not found')` where defined, `tr(...)` where shown |
| Dictionary | `src/translations/ui.ts` (`English: [Hindi, Marathi]`); older keyed blocks stay in `translations/strings.ts` |

`apps/mobile/tests/i18n.test.ts` (scanner in `i18nScan.ts`) fails when user-facing English bypasses
`tr()`/`msg()`, a component never subscribes, a key lacks Hindi or Marathi or is unused, or
placeholders or figures change. Names that are never translated, and the files the scan skips, are
listed in the scanner. The scan is rule-based: it can miss a literal in an unusual position, so
check new screens in Hindi. The development-only primitives gallery stays English.

The screens were checked in the Expo web export at 390 px. **The app has not been run on a device
or emulator**, so fonts, text fitting and screen-reader speech on Android and iOS are unverified.
A message already on screen keeps its language until the action that produced it runs again.

## 2. Checks

`apps/web/tests/i18n.test.ts` fails when a key is missing from either language, is left over from
removed English text, changes its placeholders or edge spaces, is copied untranslated, or loses a
figure or identifier. `npx tsx scripts/i18n-keys.ts` (in `apps/web`) lists missing keys.

The checks prove completeness and that figures survive. **They say nothing about meaning, tone or
terminology.**

The key script sees literal arguments of `tr()`/`msg()`, `<T k>` and the public copy. A new
hardcoded JSX string is not caught by it; review new screens for literals.

## 3. Glossary

Module names (Kadi, BillNyay, DaaviSetu, BimaNyay, SchemeSetu, DawaCheck), scheme and regulator
names, dataset labels, codes, file names, units and the badge ids stay in Latin script.

| English | Hindi | Marathi |
|---|---|---|
| case | केस | केस (feminine) |
| account | खाता | खाते |
| reviewer | समीक्षक | समीक्षक |
| claim | दावा | दावा |
| denial | अस्वीकृति | नकार |
| insurer | बीमा कंपनी | विमा कंपनी |
| draft | मसौदा | मसुदा |
| evidence | साक्ष्य | पुरावा |
| bill line | मद | बाब |
| pre-authorisation | पूर्व-अनुमोदन | पूर्व-मंजुरी |
| ceiling price | अधिकतम मूल्य | कमाल किंमत |
| workspace | कार्यस्थान | कार्यक्षेत्र |
| credential | पहचान-कुंजी | ओळख-किल्ली |

## 4. What stays in English

| Item | Reason |
|---|---|
| Text sent by the API: error details, case timeline events, rule explanations, safety disclaimers, scenario and demo banner text, readiness guidance | The API has no localised responses. This is the largest remaining gap. |
| Document content and extracted values | Quoted as written; translating would change evidence. |
| Bill line names in the landing worked example, CGHS row names, scheme names | Shown as they appear on a bill or in the source dataset. |
| Code references on the security and platform pages | File paths. |
| DaaviSetu "copy summary" clipboard text, BillNyay appeal PDF and Claim Pack content | Produced for the recipient; server-generated. |
| Medicine price basis and unit words ("per strip of 15", "tablet") | Phrases composed by the API, shown inside a translated sentence on web and mobile. |

BimaNyay drafts can be generated in Hindi or Marathi from server templates; BillNyay accepts a
language for its appeal letter. Neither has native review.

## 5. Review needed before relying on Hindi or Marathi

1. Legal and medical wording: consent text, disclaimers, grievance and Ombudsman language,
   "provisional", "not evaluated", "package ready".
2. Consistency with the glossary above, and Marathi gender agreement for "केस".
3. Long strings at 360 px (layout was checked by script only).

Risk until then: a mistranslated qualifier could make a result sound more certain than it is.
Public pages state that the text is machine translated and unreviewed.
