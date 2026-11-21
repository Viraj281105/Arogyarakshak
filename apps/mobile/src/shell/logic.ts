// Pure shell logic (tab bar geometry, transitions, navigation theme). No react-native import,
// so it is unit-testable under tsx.
import { spacing } from '../generated/tokens';
import { fontFamily } from '../theme/fontFamily';
import type { ColorPalette } from '../theme/colors';

/** Minimum height of the tab bar above the bottom safe-area inset (>= 44px touch target + label). */
export const TAB_BAR_BASE_HEIGHT = 56;

/**
 * Cap on OS font scaling for the tab icon and label (maxFontSizeMultiplier). With this cap the tab
 * content still fits TAB_BAR_BASE_HEIGHT; the bar uses minHeight, so it grows rather than clips if a
 * platform ignores the cap. Long labels shrink to fit their width (adjustsFontSizeToFit) on device.
 */
export const TAB_MAX_FONT_SCALE = 1.2;
export const TAB_ICON = { fontSize: 20, lineHeight: 24 } as const;
export const TAB_LABEL_GAP = 2;

/** Height of icon + gap + label at a given font scale (capped at TAB_MAX_FONT_SCALE). */
export function tabContentHeight(fontScale: number, labelLineHeight: number): number {
  const s = Math.min(Math.max(fontScale, 1), TAB_MAX_FONT_SCALE);
  return TAB_ICON.lineHeight * s + TAB_LABEL_GAP + labelLineHeight * s;
}

export function tabWidth(containerWidth: number, count: number): number {
  if (count <= 0 || containerWidth <= 0) return 0;
  return containerWidth / count;
}

export function indicatorX(index: number, width: number): number {
  return Math.max(0, index) * width;
}

/** Minimum bar height: base plus the bottom inset; devices without an inset still get a small gap. */
export function tabBarHeight(bottomInset: number): number {
  return TAB_BAR_BASE_HEIGHT + Math.max(bottomInset, spacing.sm);
}

/** `reduced` is the value of useReducedMotion (true while unknown). */
export function tabTransition(reduced: boolean): 'shift' | 'none' {
  return reduced ? 'none' : 'shift';
}

export function stackTransition(reduced: boolean): 'slide_from_bottom' | 'none' {
  return reduced ? 'none' : 'slide_from_bottom';
}

type NavFont = { fontFamily: string; fontWeight: 'normal' };

/**
 * React Navigation v7 theme from the design tokens, so navigator backgrounds match the app
 * (no white flash between screens). fontWeight stays 'normal': the weight is in the family name.
 */
export function navigationTheme(isDark: boolean, c: ColorPalette) {
  const f = (w: '400' | '500' | '600' | '700'): NavFont => ({ fontFamily: fontFamily('sans', w), fontWeight: 'normal' });
  return {
    dark: isDark,
    colors: {
      primary: c.brandCyan,
      background: c.bgBase,
      card: c.bgSurface,
      text: c.textPrimary,
      border: c.borderSubtle,
      notification: c.statusDanger,
    },
    fonts: { regular: f('400'), medium: f('500'), bold: f('600'), heavy: f('700') },
  };
}

/** Style keys that position or size a component in its parent's layout. */
export const LAYOUT_STYLE_KEYS = [
  'flex', 'flexGrow', 'flexShrink', 'flexBasis',
  'width', 'height', 'minWidth', 'maxWidth', 'minHeight', 'maxHeight',
  'alignSelf', 'position', 'top', 'left', 'right', 'bottom', 'start', 'end', 'zIndex',
  'margin', 'marginTop', 'marginBottom', 'marginLeft', 'marginRight',
  'marginHorizontal', 'marginVertical', 'marginStart', 'marginEnd',
] as const;

const VERTICAL_SIZE_KEYS = ['flex', 'flexGrow', 'flexBasis', 'height', 'minHeight'];

/**
 * Splits a flattened style for a component wrapped in an outer view (e.g. Card inside Reveal):
 * layout keys go to the wrapper, the rest stays on the inner element. When the wrapper gets a
 * vertical size, the inner element grows to fill it.
 */
export function splitLayoutStyle(style: Record<string, unknown> | null | undefined): {
  outer: Record<string, unknown>;
  inner: Record<string, unknown>;
} {
  const outer: Record<string, unknown> = {};
  const inner: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(style ?? {})) {
    if ((LAYOUT_STYLE_KEYS as readonly string[]).includes(k)) outer[k] = v;
    else inner[k] = v;
  }
  if (VERTICAL_SIZE_KEYS.some((k) => k in outer)) inner.flexGrow = 1;
  return { outer, inner };
}
