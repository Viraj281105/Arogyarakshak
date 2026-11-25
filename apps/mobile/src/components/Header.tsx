import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme, textStyles, font, textStyleFor } from '../theme';
import { Language } from '../translations';
import { Pressable } from '../motion';
import { segmentSwatch } from './ui/tones';
import { tr, useTranslation } from '../translations/tr';

export interface HeaderProps {
  title?: string;
  currentLanguage: Language;
  onLanguageChange: (lang: Language) => void;
  /** Shown only while signed in. */
  onSignOut?: () => void;
  signOutLabel?: string;
}

const LANGUAGES: Language[] = ['en', 'hi', 'mr'];
// Each language in its own script, so a person can find theirs whatever is selected.
const LANGUAGE_NAMES: Record<Language, string> = { en: 'English', hi: 'हिंदी', mr: 'मराठी' };

/**
 * App header: pads the top safe-area inset, brand in the display face with the BYOD marker under
 * it, an EN/HI/MR segmented control and a theme toggle (all 44px touch targets, motion Pressable).
 */
export const Header: React.FC<HeaderProps> = ({
  title = 'ArogyaRakshak',
  currentLanguage,
  onLanguageChange,
  onSignOut,
  signOutLabel = tr('Sign out'),
}) => {
  useTranslation();
  const { colors, spacing, radii, isDark, toggleTheme } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.bgSurface,
          borderBottomColor: colors.borderSubtle,
          paddingTop: insets.top + spacing.sm,
          paddingBottom: spacing.sm,
          paddingLeft: Math.max(insets.left, spacing.md),
          paddingRight: Math.max(insets.right, spacing.md),
        },
      ]}
    >
      <View style={styles.brand}>
        <Text
          accessibilityRole="header"
          numberOfLines={1}
          style={[textStyleFor(textStyles.brand, title, '600'), { color: colors.textPrimary }]}
        >
          {title}
        </Text>
        <Text numberOfLines={1} style={[textStyles.caption, styles.byod, { color: colors.brandEmerald }]}>
          BYOD
        </Text>
      </View>

      <View style={styles.controls}>
        <View
          accessibilityRole="radiogroup"
          style={[styles.segmented, { borderColor: colors.borderMedium, borderRadius: radii.md }]}
        >
          {LANGUAGES.map((lang) => {
            const active = currentLanguage === lang;
            const seg = segmentSwatch(colors, active);
            return (
              <Pressable
                key={lang}
                onPress={() => onLanguageChange(lang)}
                accessibilityRole="radio"
                accessibilityState={{ selected: active, checked: active }}
                aria-checked={active}
                accessibilityLabel={tr('Switch to {language}', { language: LANGUAGE_NAMES[lang] })}
                style={[
                  styles.segment,
                  {
                    minHeight: spacing.minTouchTarget,
                    minWidth: spacing.minTouchTarget,
                    borderRadius: radii.md - 2,
                    backgroundColor: active ? seg.bg ?? undefined : 'transparent',
                  },
                ]}
              >
                <Text
                  style={[
                    font('sans', active ? '700' : '500'),
                    styles.segmentText,
                    { color: seg.fg },
                  ]}
                >
                  {lang.toUpperCase()}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Pressable
          onPress={toggleTheme}
          accessibilityRole="button"
          accessibilityLabel={isDark ? tr('Switch to light mode') : tr('Switch to dark mode')}
          style={[
            styles.themeToggle,
            {
              minHeight: spacing.minTouchTarget,
              minWidth: spacing.minTouchTarget,
              borderRadius: radii.md,
              backgroundColor: colors.bgSurfaceElevated,
              borderColor: colors.borderSubtle,
              marginLeft: spacing.xs,
            },
          ]}
        >
          <Text style={styles.themeIcon}>{isDark ? '☀️' : '🌙'}</Text>
        </Pressable>

        {onSignOut && (
          <Pressable
            onPress={onSignOut}
            accessibilityRole="button"
            accessibilityLabel={signOutLabel}
            style={[
              styles.themeToggle,
              {
                minHeight: spacing.minTouchTarget,
                minWidth: spacing.minTouchTarget,
                borderRadius: radii.md,
                backgroundColor: colors.bgSurfaceElevated,
                borderColor: colors.borderSubtle,
                marginLeft: spacing.xs,
              },
            ]}
          >
            <Text style={styles.themeIcon}>⎋</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: StyleSheet.hairlineWidth,
    width: '100%',
  },
  brand: {
    flexShrink: 1,
    marginRight: 8,
  },
  byod: {
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0.8,
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  segmented: {
    flexDirection: 'row',
    borderWidth: 1,
    padding: 1,
  },
  segment: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  segmentText: {
    fontSize: 12,
    letterSpacing: 0.5,
  },
  themeToggle: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  themeIcon: {
    fontSize: 18,
  },
});
