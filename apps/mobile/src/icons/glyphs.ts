/**
 * The one mobile icon map (Wave 3 decision D3), mirroring apps/web/app/shell/icons/*: the same
 * module, action and evidence keys. Mobile draws them as text glyphs, not SVG: measured on the
 * Android Hermes bundle, react-native-svg alone cost +227,700 B and with lucide-react-native and
 * 38 icons +263,305 B, which put the bundle at 2,662,807 B, over the 2,600,000 B budget
 * (docs/development/performance-budgets.md, Wave 3 M2). Pure data, no react-native import.
 *
 * Two kinds of glyph:
 * - `tintable`: monochrome text symbols (Geometric Shapes, Dingbats, Arrows, Letterlike Symbols),
 *   forced to text presentation with U+FE0E where a codepoint also has an emoji form. They take the
 *   colour of their text style, so they are used inside badges, states and buttons.
 * - emoji: full-colour pictographs (module icons, tab-style icons). They ignore colour.
 * Every glyph is decorative: render it with `Icon` (hidden from accessibility) next to visible text
 * or inside a control that has an accessibilityLabel.
 */
import type { EvidenceState } from '../components/ui/evidence';

const TEXT = '︎';

/** Kadi is shared infrastructure; its user-facing surface is "Documents", not a sixth module. */
export type IconModule = 'kadi' | 'billnyay' | 'daavisetu' | 'bimanyay' | 'schemesetu' | 'dawacheck';

/** Web: file-text, receipt-text, clipboard-check, shield-check, landmark, pill. */
export const MODULE_GLYPHS: Record<IconModule, string> = {
  kadi: '📄',
  billnyay: '🧾',
  daavisetu: '📋',
  bimanyay: '🛡️',
  schemesetu: '🏛️',
  dawacheck: '💊',
};

/**
 * Web keys (minus `command`, the keyboard palette, which mobile does not have) plus the mobile
 * five-tab IA (architecture doc 3.3: Home, Scan, Cases, Tools, Settings) and `offline`.
 */
export const ACTION_GLYPHS = {
  upload: '↑',
  add: '+',
  delete: '🗑️',
  download: '↓',
  next: '→',
  search: '🔍',
  close: '✕',
  home: '⌂',
  workspace: '▦',
  reviewer: `⚕${TEXT}`,
  info: `ℹ${TEXT}`,
  warning: `⚠${TEXT}`,
  error: '!',
  success: '✓',
  scan: '📷',
  cases: '🗂️',
  tools: '🛠️',
  settings: `⚙${TEXT}`,
  offline: '⊘',
} as const;

export type ActionIcon = keyof typeof ACTION_GLYPHS;

/** Keys whose glyph is a monochrome text symbol (takes the text colour). */
export const TINTABLE_ACTIONS: readonly ActionIcon[] = [
  'upload',
  'add',
  'download',
  'next',
  'close',
  'home',
  'workspace',
  'reviewer',
  'info',
  'warning',
  'error',
  'success',
  'settings',
  'offline',
];

/**
 * One distinct, tintable glyph per evidence state (web: badge-check, hourglass, circle-dashed,
 * file-question, sparkles, scale, user-round, book-open). The badge always shows its label too.
 */
export const EVIDENCE_GLYPHS: Record<EvidenceState, string> = {
  verified: '✓',
  provisional: '◐',
  unevaluated: '◌',
  'insufficient-evidence': '?',
  'ai-generated': '✦',
  'rule-engine': '§',
  'user-provided': '✎',
  external: '❝',
};
