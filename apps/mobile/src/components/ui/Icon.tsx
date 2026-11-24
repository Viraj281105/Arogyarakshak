import React from 'react';
import { StyleSheet, Text, TextStyle } from 'react-native';
import { ACTION_GLYPHS, EVIDENCE_GLYPHS, MODULE_GLYPHS, type ActionIcon, type IconModule } from '../../icons/glyphs';
import type { EvidenceState } from './evidence';

export type IconName =
  | { action: ActionIcon }
  | { module: IconModule }
  | { evidence: EvidenceState }
  | { glyph: string };

function glyphFor(name: IconName): string {
  if ('action' in name) return ACTION_GLYPHS[name.action];
  if ('module' in name) return MODULE_GLYPHS[name.module];
  if ('evidence' in name) return EVIDENCE_GLYPHS[name.evidence];
  return name.glyph;
}

/**
 * Decorative glyph from the icon map (src/icons/glyphs.ts). Always hidden from assistive tech:
 * the surrounding text or the control's accessibilityLabel carries the meaning. Tintable glyphs
 * take `color`; emoji ignore it. Scales with OS text size, capped like the tab icons.
 */
export function Icon({
  name,
  size = 16,
  color,
  style,
}: {
  name: IconName;
  size?: number;
  color?: string;
  style?: TextStyle;
}) {
  return (
    <Text
      accessible={false}
      importantForAccessibility="no-hide-descendants"
      accessibilityElementsHidden
      aria-hidden
      maxFontSizeMultiplier={1.4}
      style={[styles.glyph, { fontSize: size, lineHeight: Math.round(size * 1.25), color }, style]}
    >
      {glyphFor(name)}
    </Text>
  );
}

const styles = StyleSheet.create({
  glyph: { textAlign: 'center', includeFontPadding: false },
});
