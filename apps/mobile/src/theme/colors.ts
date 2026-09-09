/**
 * ArogyaRakshak Mobile Theme Color Tokens
 * Mirrors the production palette from apps/web/app/globals.css
 */

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
  brandCyan: string;
  brandTeal: string;
  brandEmerald: string;
  statusWarning: string;
  statusDanger: string;
  statusSuccess: string;
  statusInfo: string;
}

export const darkColors: ColorPalette = {
  bgBase: '#0a0e17',
  bgSurface: '#111827',
  bgSurfaceElevated: '#1e293b',
  borderSubtle: 'rgba(255, 255, 255, 0.08)',
  borderMedium: 'rgba(255, 255, 255, 0.15)',
  borderFocus: '#06b6d4',
  textPrimary: '#f8fafc',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  brandCyan: '#06b6d4',
  brandTeal: '#14b8a6',
  brandEmerald: '#10b981',
  statusWarning: '#f59e0b',
  statusDanger: '#ef4444',
  statusSuccess: '#10b981',
  statusInfo: '#3b82f6',
};

export const lightColors: ColorPalette = {
  bgBase: '#f8fafc',
  bgSurface: '#ffffff',
  bgSurfaceElevated: '#f1f5f9',
  borderSubtle: 'rgba(0, 0, 0, 0.08)',
  borderMedium: 'rgba(0, 0, 0, 0.16)',
  borderFocus: '#0891b2',
  textPrimary: '#0f172a',
  textSecondary: '#475569',
  textMuted: '#64748b',
  brandCyan: '#0891b2',
  brandTeal: '#0d9488',
  brandEmerald: '#059669',
  statusWarning: '#d97706',
  statusDanger: '#dc2626',
  statusSuccess: '#059669',
  statusInfo: '#2563eb',
};
