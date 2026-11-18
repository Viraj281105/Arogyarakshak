// Pure shell logic (tab bar geometry, transitions, navigation theme). No react-native import,
// so it is unit-testable under tsx.
import { spacing } from '../generated/tokens';
import { fontFamily } from '../theme/fontFamily';
import type { ColorPalette } from '../theme/colors';

/** Height of the tab bar above the bottom safe-area inset (>= 44px touch target + label). */
export const TAB_BAR_BASE_HEIGHT = 56;

export function tabWidth(containerWidth: number, count: number): number {
  if (count <= 0 || containerWidth <= 0) return 0;
  return containerWidth / count;
}

export function indicatorX(index: number, width: number): number {
  return Math.max(0, index) * width;
}

/** Base height plus the bottom inset; devices without an inset still get a small gap. */
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
