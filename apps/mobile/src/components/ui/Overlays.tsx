import React, { useEffect, useRef, useState } from 'react';
import { Animated, Modal, Pressable as RNPressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { motion } from '../../generated/tokens';
import { useTheme, textStyles, textStyleFor } from '../../theme';
import { Pressable, useReducedMotion } from '../../motion';
import { NATIVE_DRIVER, STANDARD_EASING } from '../../motion/driver';
import { Button } from '../Button';
import { Icon } from './Icon';
import { SHEET_MAX_HEIGHT_RATIO, sheetOffset } from './logic';
import { sheetHandleColor } from './tones';

/**
 * Modal overlays on React Native's own Modal + Animated (no gesture library: Gesture Handler is
 * about +934 KB of JS and is banned by tests/shell.test.ts). Closing is by the close button, a tap
 * on the scrim, or the Android back button (onRequestClose). Under reduced motion they appear and
 * disappear in place without sliding or fading.
 */
function useOverlayProgress(open: boolean) {
  const reduced = useReducedMotion();
  const [mounted, setMounted] = useState(open);
  const progress = useRef(new Animated.Value(open ? 1 : 0)).current;

  useEffect(() => {
    if (open) setMounted(true);
    if (reduced) {
      progress.setValue(open ? 1 : 0);
      if (!open) setMounted(false);
      return undefined;
    }
    const anim = Animated.timing(progress, {
      toValue: open ? 1 : 0,
      duration: motion.duration.base,
      easing: STANDARD_EASING,
      useNativeDriver: NATIVE_DRIVER,
    });
    anim.start(({ finished }) => {
      if (finished && !open) setMounted(false);
    });
    return () => anim.stop();
  }, [open, reduced, progress]);

  return { mounted, progress, reduced };
}

function Scrim({ progress, onPress, label }: { progress: Animated.Value; onPress: () => void; label: string }) {
  const { colors } = useTheme();
  return (
    <Animated.View style={[StyleSheet.absoluteFill, { backgroundColor: colors.overlayScrim, opacity: progress }]}>
      <RNPressable
        style={StyleSheet.absoluteFill}
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={label}
      />
    </Animated.View>
  );
}

export function BottomSheet({
  open,
  onClose,
  title,
  children,
  closeLabel = 'Close',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  closeLabel?: string;
}) {
  const { colors, spacing, radii } = useTheme();
  const insets = useSafeAreaInsets();
  const { height } = useWindowDimensions();
  const { mounted, progress, reduced } = useOverlayProgress(open);
  if (!mounted) return null;

  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [sheetOffset(reduced, height), 0] });

  return (
    <Modal visible transparent animationType="none" onRequestClose={onClose} statusBarTranslucent>
      <View style={styles.fill}>
        <Scrim progress={progress} onPress={onClose} label={closeLabel} />
        <Animated.View
          accessibilityViewIsModal
          aria-modal
          role="dialog"
          aria-label={title}
          style={[
            styles.sheet,
            {
              maxHeight: height * SHEET_MAX_HEIGHT_RATIO,
              backgroundColor: colors.bgSurface,
              borderColor: colors.borderSubtle,
              borderTopLeftRadius: radii.xl,
              borderTopRightRadius: radii.xl,
              paddingBottom: Math.max(insets.bottom, spacing.md),
              transform: [{ translateY }],
            },
          ]}
        >
          <View style={[styles.handle, { backgroundColor: sheetHandleColor(colors) }]} />
          <View style={[styles.head, { paddingHorizontal: spacing.md }]}>
            <Text accessibilityRole="header" style={[textStyleFor(textStyles.title, title, '700'), styles.title, { color: colors.textPrimary }]}>
              {title}
            </Text>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel={closeLabel}
              style={[styles.close, { minWidth: spacing.minTouchTarget, minHeight: spacing.minTouchTarget, borderRadius: radii.md }]}
            >
              <Icon name={{ action: 'close' }} size={18} color={colors.textSecondary} />
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={{ paddingHorizontal: spacing.md, paddingBottom: spacing.sm }}>{children}</ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
}

/**
 * Confirmation for consequential actions. The consequence is stated in words; the confirm button
 * names the action (never just "OK"); Cancel comes first. Same props as the web ConfirmationDialog
 * (the consequence is a string here).
 */
export function ConfirmationDialog({
  open,
  onCancel,
  onConfirm,
  title,
  consequence,
  confirmLabel,
  cancelLabel = 'Cancel',
  destructive = false,
}: {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  title: string;
  consequence: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
}) {
  const { colors, spacing, radii } = useTheme();
  const { mounted, progress, reduced } = useOverlayProgress(open);
  if (!mounted) return null;
  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [reduced ? 0 : 12, 0] });

  return (
    <Modal visible transparent animationType="none" onRequestClose={onCancel} statusBarTranslucent>
      <View style={[styles.fill, styles.center, { padding: spacing.lg }]}>
        <Scrim progress={progress} onPress={onCancel} label={cancelLabel} />
        <Animated.View
          accessibilityViewIsModal
          aria-modal
          role="alertdialog"
          aria-label={title}
          style={[
            styles.dialog,
            {
              backgroundColor: colors.bgSurface,
              borderColor: colors.borderSubtle,
              borderRadius: radii.lg,
              padding: spacing.lg,
              opacity: progress,
              transform: [{ translateY }],
            },
          ]}
        >
          <Text accessibilityRole="header" style={[textStyleFor(textStyles.title, title, '700'), { color: colors.textPrimary }]}>
            {title}
          </Text>
          <Text style={[textStyleFor(textStyles.body, consequence, '400'), { color: colors.textSecondary, marginTop: spacing.sm }]}>
            {consequence}
          </Text>
          <View style={[styles.actions, { marginTop: spacing.lg }]}>
            <Button title={cancelLabel} onPress={onCancel} variant="secondary" style={styles.action} />
            <Button
              title={confirmLabel}
              onPress={onConfirm}
              variant={destructive ? 'danger' : 'primary'}
              style={{ ...styles.action, marginLeft: spacing.sm }}
            />
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  center: { alignItems: 'center', justifyContent: 'center' },
  sheet: { position: 'absolute', left: 0, right: 0, bottom: 0, borderWidth: 1, borderBottomWidth: 0 },
  handle: { alignSelf: 'center', width: 40, height: 4, borderRadius: 2, marginTop: 8 },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 52 },
  title: { flex: 1, marginRight: 8 },
  close: { alignItems: 'center', justifyContent: 'center' },
  dialog: { width: '100%', maxWidth: 420, borderWidth: 1 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end' },
  action: { flexGrow: 1, flexBasis: 120 },
});
