/**
 * ArogyaRakshak Mobile Theme Color Tokens
 * Values come from the generated design tokens (packages/design-tokens/tokens.json),
 * the single source shared with apps/web. Since Wave 3 M2 the palette is the whole generated
 * set (action, evidence, chart and status tokens included), so components never need a literal.
 */
import { colors, type Palette } from '../generated/tokens';

export type ColorPalette = Palette;

export const darkColors: ColorPalette = { ...colors.dark };
export const lightColors: ColorPalette = { ...colors.light };
