import React, { useState } from 'react';
import { LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useTheme, textStyles, fontFor } from '../theme';
import { Pressable, SlidingIndicator } from '../motion';
import {
  indicatorX,
  tabBarHeight,
  tabWidth,
  TAB_BAR_BASE_HEIGHT,
  TAB_LABEL_GAP,
  TAB_MAX_FONT_SCALE,
} from '../shell/logic';

const PILL_INSET = 4;

/**
 * Animated bottom tab bar: one motion Pressable per tab (press scale + light haptic) and a pill
 * that slides behind the active tab. Pads the bottom safe-area inset. Motion is off under reduced
 * motion (the pill jumps). Tab press semantics follow React Navigation (tabPress / tabLongPress).
 */
export function TabBar({ state, descriptors, navigation, insets }: BottomTabBarProps) {
  const { colors, spacing, radii } = useTheme();
  const [width, setWidth] = useState(0);
  const count = state.routes.length;
  const w = tabWidth(width, count);

  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  return (
    <View
      accessibilityRole="tablist"
      style={[
        styles.bar,
        {
          minHeight: tabBarHeight(insets.bottom),
          paddingBottom: Math.max(insets.bottom, spacing.sm),
          paddingLeft: insets.left,
          paddingRight: insets.right,
          backgroundColor: colors.bgSurface,
          borderTopColor: colors.borderSubtle,
        },
      ]}
    >
      <View style={styles.row} onLayout={onLayout}>
        {w > 0 && (
          <SlidingIndicator
            x={indicatorX(state.index, w) + PILL_INSET}
            width={w - PILL_INSET * 2}
            style={{
              top: PILL_INSET,
              bottom: PILL_INSET,
              borderRadius: radii.lg,
              backgroundColor: colors.bgSurfaceElevated,
              borderWidth: StyleSheet.hairlineWidth,
              borderColor: colors.borderMedium,
            }}
          />
        )}
        {state.routes.map((route, index) => {
          const { options } = descriptors[route.key];
          const focused = state.index === index;
          const label =
            typeof options.tabBarLabel === 'string' ? options.tabBarLabel : options.title ?? route.name;
          const color = focused ? colors.textPrimary : colors.textMuted;

          const onPress = () => {
            const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
            if (!focused && !event.defaultPrevented) {
              navigation.navigate(route.name, route.params);
            }
          };
          const onLongPress = () => navigation.emit({ type: 'tabLongPress', target: route.key });

          return (
            <Pressable
              key={route.key}
              onPress={onPress}
              onLongPress={onLongPress}
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              aria-selected={focused}
              accessibilityLabel={options.tabBarAccessibilityLabel ?? label}
              testID={options.tabBarButtonTestID}
              style={[styles.tab, { minHeight: spacing.minTouchTarget }]}
            >
              <View style={{ opacity: focused ? 1 : 0.7 }}>
                {options.tabBarIcon?.({ focused, color, size: 20 })}
              </View>
              <Text
                numberOfLines={1}
                maxFontSizeMultiplier={TAB_MAX_FONT_SCALE}
                adjustsFontSizeToFit
                minimumFontScale={0.8}
                style={[
                  textStyles.tab,
                  fontFor(label, 'sans', '600'),
                  styles.label,
                  { color, opacity: focused ? 1 : 0.9 },
                ]}
              >
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  row: {
    flexDirection: 'row',
    minHeight: TAB_BAR_BASE_HEIGHT,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    marginTop: TAB_LABEL_GAP,
    textAlign: 'center',
  },
});
