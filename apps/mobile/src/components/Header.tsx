import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTheme } from '../theme';
import { Language } from '../translations';
import { Badge } from './Badge';

export interface HeaderProps {
  title?: string;
  currentLanguage: Language;
  onLanguageChange: (lang: Language) => void;
}

export const Header: React.FC<HeaderProps> = ({
  title = 'ArogyaRakshak',
  currentLanguage,
  onLanguageChange,
}) => {
  const { colors, spacing, typography, isDark, toggleTheme } = useTheme();

  return (
    <View
      style={[
        styles.headerContainer,
        {
          backgroundColor: colors.bgSurface,
          borderBottomColor: colors.borderSubtle,
          paddingHorizontal: spacing.md,
          paddingVertical: spacing.sm,
        },
      ]}
    >
      <View style={styles.topRow}>
        <View style={styles.brandGroup}>
          <Text
            style={[
              styles.brandTitle,
              {
                color: colors.textPrimary,
                fontSize: typography.sizes.lg,
                fontWeight: typography.weights.bold,
              },
            ]}
          >
            🛡️ {title}
          </Text>
          <Badge label="BYOD" variant="brand" style={styles.byodBadge} />
        </View>

        <View style={styles.controlsGroup}>
          {/* Language Toggle Controls */}
          {(['en', 'hi', 'mr'] as Language[]).map((lang) => {
            const isActive = currentLanguage === lang;
            return (
              <TouchableOpacity
                key={lang}
                onPress={() => onLanguageChange(lang)}
                accessible={true}
                accessibilityRole="button"
                accessibilityLabel={`Switch to ${lang}`}
                style={[
                  styles.controlButton,
                  {
                    backgroundColor: isActive ? colors.brandCyan : 'transparent',
                    borderColor: isActive ? colors.brandCyan : colors.borderMedium,
                    minHeight: spacing.minTouchTarget, // 44px touch target
                    minWidth: spacing.minTouchTarget,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.langText,
                    {
                      color: isActive ? '#ffffff' : colors.textSecondary,
                      fontWeight: isActive ? '700' : '500',
                      fontSize: typography.sizes.xs,
                    },
                  ]}
                >
                  {lang.toUpperCase()}
                </Text>
              </TouchableOpacity>
            );
          })}

          {/* Theme Toggle Button */}
          <TouchableOpacity
            onPress={toggleTheme}
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            style={[
              styles.controlButton,
              {
                backgroundColor: colors.bgSurfaceElevated,
                borderColor: colors.borderSubtle,
                minHeight: spacing.minTouchTarget, // 44px touch target
                minWidth: spacing.minTouchTarget,
                marginLeft: spacing.xs,
              },
            ]}
          >
            <Text style={{ fontSize: typography.sizes.md }}>
              {isDark ? '☀️' : '🌙'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  headerContainer: {
    borderBottomWidth: 1,
    width: '100%',
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  brandGroup: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  brandTitle: {
    letterSpacing: -0.3,
  },
  byodBadge: {
    marginLeft: 8,
  },
  controlsGroup: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  controlButton: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: 8,
    marginHorizontal: 2,
  },
  langText: {
    letterSpacing: 0.5,
  },
});
