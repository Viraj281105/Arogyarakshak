import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useTheme } from '../theme';
import { Explanation, explanationToText } from '../services/explanation';
import { tr, useTranslation } from '../translations/tr';

/** "Why am I seeing this?" — collapsed plain-text explanation under a finding (ADR-017). */
export const ExplainToggle: React.FC<{ explanation?: Explanation | null }> = ({ explanation }) => {
  useTranslation();
  const { colors, typography } = useTheme();
  const [open, setOpen] = useState(false);
  if (!explanation) return null;
  return (
    <View style={{ marginTop: 4 }}>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={tr('Why am I seeing this?')}
        style={{ minHeight: 44, justifyContent: 'center' }}
      >
        <Text style={{ color: colors.brandCyan, fontSize: typography.sizes.xs }}>
          {open ? '▾' : '▸'} {tr('Why am I seeing this?')}
        </Text>
      </Pressable>
      {open && (
        <Text selectable style={{ color: colors.textSecondary, fontSize: typography.sizes.xs }}>
          {explanationToText(explanation)}
        </Text>
      )}
    </View>
  );
};
