// Pure logic for the mobile primitives (no react-native import), unit-tested under tsx.
// Shapes and wording follow the web primitives (apps/web/app/components/ui) where sensible.
import type { ChecklistStatus, ConfidenceWord, StepState, ToastTone } from './tones';
import { tr, msg } from '../../translations/tr';

/** Bucket a 0..1 confidence for its visible word. Values outside 0..1 (or NaN) are clamped. Same as web. */
export function confidenceBucket(value: number): { pct: number; word: ConfidenceWord } {
  const v = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  const pct = Math.round(v * 100);
  return { pct, word: v >= 0.85 ? msg('High') : v >= 0.6 ? msg('Medium') : msg('Low') };
}

export function stepState(index: number, current: number): StepState {
  return index < current ? 'done' : index === current ? 'current' : 'upcoming';
}

/** Words read by a screen reader for a step (state is never colour-only). */
export const STEP_WORD: Record<StepState, string> = {
  done: msg('completed'),
  current: msg('current step'),
  upcoming: msg('not started'),
};

export function stepCountText(current: number, total: number): string {
  if (total <= 0) return tr('No steps');
  return tr('Step {current} of {total}', { current: Math.min(Math.max(current, 0) + 1, total), total });
}

export const CHECKLIST_WORD: Record<ChecklistStatus, string> = {
  done: msg('Done'),
  todo: msg('To do'),
  blocked: msg('Blocked'),
  unknown: msg('Not checked'),
};

export function checklistSummary(items: readonly { status: ChecklistStatus }[]): string {
  const done = items.filter((i) => i.status === 'done').length;
  return tr('{done} of {total} done', { done, total: items.length });
}

// ---- Toast queue -------------------------------------------------------------------------------

export interface ToastInput {
  message: string;
  tone?: ToastTone;
  /** Milliseconds before it hides; 0 keeps it until dismissed. Errors default to 0 (as on web). */
  duration?: number;
}

export interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
  duration: number;
}

export const TOAST_DEFAULT_MS = 6000;
export const TOAST_MAX_VISIBLE = 3;

export function toastDuration(input: ToastInput): number {
  const tone = input.tone ?? 'info';
  return input.duration ?? (tone === 'error' ? 0 : TOAST_DEFAULT_MS);
}

/** Warnings and errors interrupt the screen reader; success and info wait their turn. */
export function toastIsAssertive(tone: ToastTone): boolean {
  return tone === 'warning' || tone === 'error';
}

export type ToastAction = { type: 'show'; id: number; input: ToastInput } | { type: 'dismiss'; id: number };

/** Keeps at most TOAST_MAX_VISIBLE toasts; the oldest goes first. */
export function toastReducer(state: readonly ToastItem[], action: ToastAction): ToastItem[] {
  if (action.type === 'dismiss') return state.filter((t) => t.id !== action.id);
  const item: ToastItem = {
    id: action.id,
    message: action.input.message,
    tone: action.input.tone ?? 'info',
    duration: toastDuration(action.input),
  };
  return [...state.slice(-(TOAST_MAX_VISIBLE - 1)), item];
}

// ---- Bottom sheet ------------------------------------------------------------------------------

/** Off-screen distance the sheet slides from; under reduced motion it appears in place (fade only). */
export function sheetOffset(reduced: boolean, height: number): number {
  return reduced ? 0 : Math.max(height, 1);
}

/** Sheet height cap as a share of the window, so the scrim (tap to close) always stays visible. */
export const SHEET_MAX_HEIGHT_RATIO = 0.85;
