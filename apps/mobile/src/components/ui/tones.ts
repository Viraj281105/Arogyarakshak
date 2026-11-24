/**
 * Every colour pairing the shared mobile components draw, as pure functions of the palette.
 * Components take their colours ONLY from here (a test bans colour literals in them), and
 * `contrastPairs()` enumerates the same functions for every variant, so the contrast test in
 * tests/contrast.test.ts covers exactly what is drawn, in both themes. No react-native import.
 *
 * Rule from the web stream (wave3-components.md): filled controls use actionPrimary/textOnAction.
 * White on a coloured fill is never assumed: textOnAction is navy in the dark theme.
 */
import type { ColorPalette } from '../../theme/colors';
import { EVIDENCE_STATES, evidenceTokenPrefix, type EvidenceState } from './evidence';

/** `bg: null` means transparent: the control sits on whatever page background is under it. */
export interface Swatch {
  fg: string;
  bg: string | null;
  border: string | null;
}

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export const BUTTON_VARIANTS: readonly ButtonVariant[] = ['primary', 'secondary', 'outline', 'ghost', 'danger'];

export function buttonSwatch(p: ColorPalette, variant: ButtonVariant, disabled = false): Swatch {
  if (disabled) return { fg: p.textMuted, bg: p.bgSurfaceElevated, border: p.borderSubtle };
  switch (variant) {
    case 'primary':
      return { fg: p.textOnAction, bg: p.actionPrimary, border: null };
    case 'danger':
      return { fg: p.textOnAction, bg: p.statusDanger, border: null };
    case 'secondary':
      return { fg: p.textPrimary, bg: p.bgSurfaceElevated, border: p.borderMedium };
    case 'outline':
      return { fg: p.actionPrimary, bg: null, border: p.actionPrimary };
    case 'ghost':
    default:
      return { fg: p.textPrimary, bg: null, border: null };
  }
}

/** Legacy `Badge` variants (used by screens). Status colour text on the elevated surface. */
export type BadgeVariant = 'info' | 'success' | 'warning' | 'danger' | 'brand';
export const BADGE_VARIANTS: readonly BadgeVariant[] = ['info', 'success', 'warning', 'danger', 'brand'];

export function badgeSwatch(p: ColorPalette, variant: BadgeVariant): Swatch {
  const fg = {
    info: p.statusInfo,
    success: p.statusSuccess,
    warning: p.statusWarning,
    danger: p.statusDanger,
    brand: p.brandCyan,
  }[variant];
  return { fg, bg: p.bgSurfaceElevated, border: p.borderSubtle };
}

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';
export const STATUS_TONES: readonly StatusTone[] = ['success', 'warning', 'danger', 'info', 'neutral'];

/** Colour of a status tone used as a mark (dot, bar, icon), never as the only signal. */
export function toneColor(p: ColorPalette, tone: StatusTone): string {
  return {
    success: p.statusSuccess,
    warning: p.statusWarning,
    danger: p.statusDanger,
    info: p.statusInfo,
    neutral: p.textMuted,
  }[tone];
}

/** StatusBadge: primary text on the elevated surface; the tone is a dot beside the text. */
export function statusBadgeSwatch(p: ColorPalette, tone: StatusTone): Swatch & { dot: string } {
  return { fg: p.textPrimary, bg: p.bgSurfaceElevated, border: p.borderSubtle, dot: toneColor(p, tone) };
}

export function evidenceSwatch(p: ColorPalette, state: EvidenceState): Swatch {
  const k = evidenceTokenPrefix(state);
  const get = (suffix: string) => (p as unknown as Record<string, string>)[`${k}${suffix}`];
  return { fg: get('Fg'), bg: get('Bg'), border: get('Border') };
}

export type ToastTone = 'success' | 'info' | 'warning' | 'error';
export const TOAST_TONES: readonly ToastTone[] = ['success', 'info', 'warning', 'error'];

export function toastSwatch(p: ColorPalette, tone: ToastTone): Swatch & { accent: string } {
  const accent = { success: p.statusSuccess, info: p.statusInfo, warning: p.statusWarning, error: p.statusDanger }[tone];
  return { fg: p.textPrimary, bg: p.bgSurfaceElevated, border: p.borderMedium, accent };
}

export type StateKind = 'loading' | 'empty' | 'error' | 'partial' | 'insufficient' | 'offline';
export const STATE_KINDS: readonly StateKind[] = ['loading', 'empty', 'error', 'partial', 'insufficient', 'offline'];

/** Panel states: title/body text on the surface; the kind's colour marks the icon and left border. */
export function stateSwatch(
  p: ColorPalette,
  kind: StateKind,
): { title: string; body: string; bg: string; border: string; accent: string } {
  const accent = {
    loading: p.actionPrimary,
    empty: p.textMuted,
    error: p.statusDanger,
    partial: p.statusWarning,
    insufficient: p.statusInsufficient,
    offline: p.statusWarning,
  }[kind];
  return { title: p.textPrimary, body: p.textSecondary, bg: p.bgSurface, border: p.borderSubtle, accent };
}

/** The offline strip under the header: the provisional (amber) evidence pair, AA in both themes. */
export function offlineBannerSwatch(p: ColorPalette): Swatch {
  return { fg: p.evidenceProvisionalFg, bg: p.evidenceProvisionalBg, border: p.evidenceProvisionalBorder };
}

export type ChecklistStatus = 'done' | 'todo' | 'blocked' | 'unknown';
export const CHECKLIST_STATUSES: readonly ChecklistStatus[] = ['done', 'todo', 'blocked', 'unknown'];

export function checklistColor(p: ColorPalette, status: ChecklistStatus): string {
  return { done: p.statusSuccess, todo: p.textSecondary, blocked: p.statusDanger, unknown: p.textMuted }[status];
}

export type StepState = 'done' | 'current' | 'upcoming';
export const STEP_STATES: readonly StepState[] = ['done', 'current', 'upcoming'];

/** Step marker (the numbered circle): filled when done, outlined when current/upcoming. */
export function stepMarkerSwatch(p: ColorPalette, state: StepState): Swatch {
  switch (state) {
    case 'done':
      return { fg: p.textOnAction, bg: p.actionPrimary, border: p.actionPrimary };
    case 'current':
      return { fg: p.actionPrimary, bg: p.bgSurface, border: p.actionPrimary };
    case 'upcoming':
    default:
      // borderMedium was 1.5-1.8:1 on the surface (the contrast test caught it); textMuted is AA.
      return { fg: p.textSecondary, bg: p.bgSurface, border: p.textMuted };
  }
}

/** Grab handle on the bottom sheet (a UI part: 3:1). borderSpecular was 1.95-2.5:1. */
export function sheetHandleColor(p: ColorPalette): string {
  return p.textMuted;
}

export type ConfidenceWord = 'High' | 'Medium' | 'Low';

export function confidenceColor(p: ColorPalette, word: ConfidenceWord): string {
  return { High: p.statusSuccess, Medium: p.statusWarning, Low: p.statusDanger }[word];
}

/** "Estimate" label on MetricCard: secondary text on the secondary surface. */
export function estimateSwatch(p: ColorPalette): Swatch {
  return { fg: p.textSecondary, bg: p.bgSurfaceSecondary, border: p.borderMedium };
}

/** Header language segment (radio): filled = action pair; idle = secondary text on the header. */
export function segmentSwatch(p: ColorPalette, active: boolean): Swatch {
  return active
    ? { fg: p.textOnAction, bg: p.actionPrimary, border: null }
    : { fg: p.textSecondary, bg: p.bgSurface, border: null };
}

// ---------------------------------------------------------------------------------------------
// The pairs the contrast test checks.

export interface ContrastPair {
  id: string;
  fg: string;
  bg: string;
  /** 4.5 for text, 3 for UI parts and marks (WCAG 1.4.3 / 1.4.11). */
  min: number;
}

const TEXT = 4.5;
const NON_TEXT = 3;

/** Backgrounds a transparent control (outline/ghost button, text) can sit on. */
export function pageBackgrounds(p: ColorPalette): Record<string, string> {
  return { bgBase: p.bgBase, bgSurface: p.bgSurface, bgSurfaceElevated: p.bgSurfaceElevated };
}

function onBackgrounds(id: string, fg: string, bg: string | null, p: ColorPalette, min: number): ContrastPair[] {
  if (bg) return [{ id, fg, bg, min }];
  return Object.entries(pageBackgrounds(p)).map(([name, b]) => ({ id: `${id} on ${name}`, fg, bg: b, min }));
}

/** Every text/background and mark/background pairing the shared components draw. */
export function contrastPairs(p: ColorPalette): ContrastPair[] {
  const out: ContrastPair[] = [];

  // Button (all variants, enabled and disabled). The outline border is a UI part (3:1).
  for (const v of BUTTON_VARIANTS) {
    for (const disabled of [false, true]) {
      const s = buttonSwatch(p, v, disabled);
      const id = `Button ${v}${disabled ? ' disabled' : ''} label`;
      out.push(...onBackgrounds(id, s.fg, s.bg, p, TEXT));
    }
  }
  out.push(...onBackgrounds('Button outline border', buttonSwatch(p, 'outline').border!, null, p, NON_TEXT));
  // A filled button must stand out from the surface it sits on.
  for (const v of ['primary', 'danger'] as const) {
    out.push(...onBackgrounds(`Button ${v} fill`, buttonSwatch(p, v).bg!, null, p, NON_TEXT));
  }

  for (const v of BADGE_VARIANTS) out.push({ id: `Badge ${v}`, ...pick(badgeSwatch(p, v)), min: TEXT });

  for (const t of STATUS_TONES) {
    const s = statusBadgeSwatch(p, t);
    out.push({ id: `StatusBadge ${t} label`, fg: s.fg, bg: s.bg!, min: TEXT });
    out.push({ id: `StatusBadge ${t} dot`, fg: s.dot, bg: s.bg!, min: NON_TEXT });
  }

  for (const e of EVIDENCE_STATES) {
    const s = evidenceSwatch(p, e);
    out.push({ id: `EvidenceBadge ${e} label`, fg: s.fg, bg: s.bg!, min: TEXT });
  }

  for (const t of TOAST_TONES) {
    const s = toastSwatch(p, t);
    out.push({ id: `Toast ${t} message`, fg: s.fg, bg: s.bg!, min: TEXT });
    out.push({ id: `Toast ${t} icon/accent`, fg: s.accent, bg: s.bg!, min: NON_TEXT });
  }

  for (const k of STATE_KINDS) {
    const s = stateSwatch(p, k);
    out.push({ id: `${k} state title`, fg: s.title, bg: s.bg, min: TEXT });
    out.push({ id: `${k} state body`, fg: s.body, bg: s.bg, min: TEXT });
    out.push({ id: `${k} state icon/accent`, fg: s.accent, bg: s.bg, min: NON_TEXT });
  }
  // Insufficient-evidence and partial states also print a note in the muted colour.
  out.push({ id: 'state note (muted)', fg: p.textMuted, bg: p.bgSurface, min: TEXT });

  out.push({ id: 'OfflineBanner text', ...pick(offlineBannerSwatch(p)), min: TEXT });

  for (const c of CHECKLIST_STATUSES) {
    out.push({ id: `Checklist ${c} status word`, fg: checklistColor(p, c), bg: p.bgSurface, min: TEXT });
  }

  for (const st of STEP_STATES) {
    const s = stepMarkerSwatch(p, st);
    out.push({ id: `StepWizard ${st} marker number`, fg: s.fg, bg: s.bg!, min: TEXT });
    out.push({ id: `StepWizard ${st} marker ring`, fg: s.border!, bg: p.bgSurface, min: NON_TEXT });
  }
  out.push({ id: 'StepWizard current label', fg: p.textPrimary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'StepWizard other labels / count', fg: p.textSecondary, bg: p.bgSurface, min: TEXT });

  for (const w of ['High', 'Medium', 'Low'] as const) {
    out.push({ id: `ConfidenceIndicator ${w} fill`, fg: confidenceColor(p, w), bg: p.bgSurfaceSecondary, min: NON_TEXT });
  }
  out.push({ id: 'ConfidenceIndicator value', fg: p.textPrimary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'ConfidenceIndicator label/source', fg: p.textSecondary, bg: p.bgSurface, min: TEXT });

  out.push({ id: 'MetricCard estimate label', ...pick(estimateSwatch(p)), min: TEXT });
  out.push({ id: 'MetricCard value', fg: p.textPrimary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'MetricCard label', fg: p.textSecondary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'MetricCard source/period', fg: p.textMuted, bg: p.bgSurface, min: TEXT });

  // Dialog and bottom sheet: text on the surface (scrim is behind the panel, not behind text).
  out.push({ id: 'Dialog/BottomSheet title', fg: p.textPrimary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'Dialog/BottomSheet body', fg: p.textSecondary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'BottomSheet handle', fg: sheetHandleColor(p), bg: p.bgSurface, min: NON_TEXT });

  // Shell parts.
  for (const active of [true, false]) {
    out.push({ id: `Header language ${active ? 'active' : 'idle'}`, ...pick(segmentSwatch(p, active)), min: TEXT });
  }
  out.push({ id: 'Header title', fg: p.textPrimary, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'Header BYOD marker', fg: p.brandEmerald, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'TabBar active label', fg: p.textPrimary, bg: p.bgSurfaceElevated, min: TEXT });
  out.push({ id: 'TabBar idle label', fg: p.textMuted, bg: p.bgSurface, min: TEXT });
  out.push({ id: 'EmptyState title on page', fg: p.textPrimary, bg: p.bgBase, min: TEXT });
  out.push({ id: 'EmptyState body on page', fg: p.textSecondary, bg: p.bgBase, min: TEXT });
  out.push({ id: 'Focus/selected ring', fg: p.borderFocus, bg: p.bgSurface, min: NON_TEXT });

  return out;
}

function pick(s: Swatch): { fg: string; bg: string } {
  if (!s.bg) throw new Error('pick() needs an opaque background');
  return { fg: s.fg, bg: s.bg };
}
