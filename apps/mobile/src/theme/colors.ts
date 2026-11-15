/**
 * ArogyaRakshak Mobile Theme Color Tokens
 * Values come from the generated design tokens (packages/design-tokens/tokens.json),
 * the single source shared with apps/web. ColorPalette is the subset the app uses.
 */
import { colors } from '../generated/tokens';

export interface ColorPalette {
  bgBase: string;
  bgSurface: string;
  bgSurfaceElevated: string;
  borderSubtle: string;
  borderMedium: string;
  borderFocus: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  brandForest: string;
  brandBrass: string;
  brandSage: string;
  brandCyan: string;
  brandTeal: string;
  brandEmerald: string;
  statusWarning: string;
  statusDanger: string;
  statusSuccess: string;
  statusInfo: string;
}

function pick(source: ColorPalette): ColorPalette {
  return {
    bgBase: source.bgBase,
    bgSurface: source.bgSurface,
    bgSurfaceElevated: source.bgSurfaceElevated,
    borderSubtle: source.borderSubtle,
    borderMedium: source.borderMedium,
    borderFocus: source.borderFocus,
    textPrimary: source.textPrimary,
    textSecondary: source.textSecondary,
    textMuted: source.textMuted,
    brandForest: source.brandForest,
    brandBrass: source.brandBrass,
    brandSage: source.brandSage,
    brandCyan: source.brandCyan,
    brandTeal: source.brandTeal,
    brandEmerald: source.brandEmerald,
    statusWarning: source.statusWarning,
    statusDanger: source.statusDanger,
    statusSuccess: source.statusSuccess,
    statusInfo: source.statusInfo,
  };
}

export const darkColors: ColorPalette = pick(colors.dark);
export const lightColors: ColorPalette = pick(colors.light);
