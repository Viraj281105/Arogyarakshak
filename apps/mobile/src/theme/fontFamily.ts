/**
 * Typography helper: maps a role + weight to the font family name that `useAppFonts` registers
 * with expo-font. React Native cannot use the CSS stacks in the generated `fonts` tokens, so
 * components must use these names. Pure (no react-native import).
 *
 * Use `font(role, weight)` and do NOT also set `fontWeight`: the weight is baked into the family,
 * and Android synthesises or falls back when both are given.
 */
import { typography } from './typography';

export type FontRole = 'display' | 'headline' | 'sans' | 'mono';
export type FontWeight = '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900';

const SUFFIX: Record<string, string> = {
  '400': '400Regular',
  '500': '500Medium',
  '600': '600SemiBold',
  '700': '700Bold',
  '800': '800ExtraBold',
};

/** Families and weights actually loaded in src/hooks/useAppFonts.ts (a test keeps them in sync). */
const LOADED: Record<FontRole, { prefix: string; weights: number[] }> = {
  display: { prefix: 'Fraunces', weights: [400, 500, 600] },
  headline: { prefix: 'PlusJakartaSans', weights: [500, 600, 700, 800] },
  sans: { prefix: 'Inter', weights: [400, 500, 600, 700] },
  mono: { prefix: 'JetBrainsMono', weights: [400, 500, 600, 700] },
};

export const LOADED_FONT_FAMILIES: readonly string[] = Object.values(LOADED).flatMap(({ prefix, weights }) =>
  weights.map((w) => `${prefix}_${SUFFIX[String(w)]}`),
);

/** Nearest loaded weight; ties go to the heavier weight. */
function nearest(weights: number[], target: number): number {
  return weights.reduce((best, w) => {
    const d = Math.abs(w - target);
    const bd = Math.abs(best - target);
    return d < bd || (d === bd && w > best) ? w : best;
  }, weights[0]);
}

export function fontFamily(role: FontRole, weight: FontWeight = '400'): string {
  const { prefix, weights } = LOADED[role];
  return `${prefix}_${SUFFIX[String(nearest(weights, Number(weight)))]}`;
}

/** Style fragment `{ fontFamily }` for a role + weight. */
export function font(role: FontRole, weight: FontWeight = '400'): { fontFamily: string } {
  return { fontFamily: fontFamily(role, weight) };
}

const { sizes, lineHeights } = typography;

/** Shell type ramp: family + size + line height (Devanagari-safe line heights from the scale). */
export const textStyles = {
  brand: { ...font('display', '600'), fontSize: sizes.lg, lineHeight: lineHeights.lg },
  title: { ...font('headline', '700'), fontSize: sizes.lg, lineHeight: lineHeights.lg },
  body: { ...font('sans', '400'), fontSize: sizes.md, lineHeight: lineHeights.md },
  bodySmall: { ...font('sans', '400'), fontSize: sizes.sm, lineHeight: lineHeights.sm },
  label: { ...font('sans', '600'), fontSize: sizes.md, lineHeight: lineHeights.md },
  labelSmall: { ...font('sans', '600'), fontSize: sizes.sm, lineHeight: lineHeights.sm },
  caption: { ...font('sans', '500'), fontSize: sizes.xs, lineHeight: lineHeights.xs },
  tab: { ...font('sans', '600'), fontSize: 10, lineHeight: 14 },
  mono: { ...font('mono', '500'), fontSize: sizes.xs, lineHeight: lineHeights.xs },
} as const;
