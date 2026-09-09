/**
 * ArogyaRakshak Mobile Typography Tokens
 * Accommodates Devanagari script (Hindi/Marathi) ascenders and descenders safely.
 */

export const typography = {
  sizes: {
    xs: 12,
    sm: 14,
    md: 16,
    lg: 18,
    xl: 20,
    xxl: 24,
    display: 30,
  },
  lineHeights: {
    xs: 18,
    sm: 22,
    md: 26,
    lg: 28,
    xl: 32,
    xxl: 36,
    display: 40,
  },
  weights: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
    extrabold: '800' as const,
  },
};
