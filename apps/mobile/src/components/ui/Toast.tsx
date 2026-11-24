import React, { createContext, useCallback, useContext, useEffect, useReducer, useRef } from 'react';
import { AccessibilityInfo, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme, textStyles, textStyleFor } from '../../theme';
import { Pressable, Reveal } from '../../motion';
import { Icon } from './Icon';
import { toastIsAssertive, toastReducer, type ToastInput, type ToastItem } from './logic';
import { toastSwatch, type ToastTone } from './tones';

const ToastContext = createContext<((t: ToastInput) => void) | null>(null);

/** Shows a toast from any component under <ToastProvider>. Same call shape as the web useToast. */
export function useToast(): (t: ToastInput) => void {
  const show = useContext(ToastContext);
  if (!show) throw new Error('useToast must be used inside <ToastProvider>');
  return show;
}

const TONE_ICON: Record<ToastTone, 'success' | 'info' | 'warning' | 'error'> = {
  success: 'success',
  info: 'info',
  warning: 'warning',
  error: 'error',
};

/**
 * Toast stack above the bottom inset. Each message is announced to screen readers (Android live
 * region: assertive for warnings/errors, polite otherwise) and has a 44pt dismiss button; errors
 * stay until dismissed. At most three are shown; the oldest goes first.
 */
export function ToastProvider({ children, bottomOffset = 0 }: { children: React.ReactNode; bottomOffset?: number }) {
  const [toasts, dispatch] = useReducer(toastReducer, [] as ToastItem[]);
  const nextId = useRef(1);
  const insets = useSafeAreaInsets();
  const { spacing } = useTheme();

  const show = useCallback((input: ToastInput) => {
    const id = nextId.current++;
    dispatch({ type: 'show', id, input });
    AccessibilityInfo.announceForAccessibility(input.message);
  }, []);
  const dismiss = useCallback((id: number) => dispatch({ type: 'dismiss', id }), []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <View
        pointerEvents="box-none"
        style={[styles.stack, { bottom: insets.bottom + bottomOffset + spacing.md, left: spacing.md, right: spacing.md }]}
      >
        {toasts.map((t) => (
          <ToastView key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </View>
    </ToastContext.Provider>
  );
}

function ToastView({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  const { colors, spacing, radii } = useTheme();
  const s = toastSwatch(colors, toast.tone);

  useEffect(() => {
    if (!toast.duration) return undefined;
    const h = setTimeout(() => onDismiss(toast.id), toast.duration);
    return () => clearTimeout(h);
  }, [toast, onDismiss]);

  return (
    <Reveal>
      <View
        accessibilityRole={toastIsAssertive(toast.tone) ? 'alert' : 'text'}
        accessibilityLiveRegion={toastIsAssertive(toast.tone) ? 'assertive' : 'polite'}
        testID={`toast-${toast.tone}`}
        style={[
          styles.toast,
          {
            backgroundColor: s.bg ?? undefined,
            borderColor: s.border ?? undefined,
            borderLeftColor: s.accent,
            borderRadius: radii.md,
            paddingLeft: spacing.md,
            marginTop: spacing.sm,
          },
        ]}
      >
        <Icon name={{ action: TONE_ICON[toast.tone] }} size={18} color={s.accent} style={{ marginRight: spacing.sm }} />
        <Text style={[textStyleFor(textStyles.bodySmall, toast.message, '400'), styles.message, { color: s.fg }]}>
          {toast.message}
        </Text>
        <Pressable
          onPress={() => onDismiss(toast.id)}
          accessibilityRole="button"
          accessibilityLabel="Dismiss notification"
          style={[styles.dismiss, { minWidth: spacing.minTouchTarget, minHeight: spacing.minTouchTarget }]}
        >
          <Icon name={{ action: 'close' }} size={16} color={colors.textSecondary} />
        </Pressable>
      </View>
    </Reveal>
  );
}

const styles = StyleSheet.create({
  stack: { position: 'absolute' },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderLeftWidth: 4,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 10,
    elevation: 6,
  },
  message: { flex: 1, paddingVertical: 10 },
  dismiss: { alignItems: 'center', justifyContent: 'center' },
});
