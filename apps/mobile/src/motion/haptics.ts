import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';
import { hapticsSupported, shouldHaptic } from './logic';
import { reducedMotionStore } from './store';

export type HapticKind = 'light' | 'success' | 'warning';

/**
 * Haptic tap. No-op under (or before knowing) reduced motion and in the browser preview;
 * swallows errors (no haptic engine).
 */
export async function tap(kind: HapticKind): Promise<void> {
  if (!hapticsSupported(Platform.OS) || !shouldHaptic(reducedMotionStore.get())) return;
  try {
    if (kind === 'light') {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } else {
      await Haptics.notificationAsync(
        kind === 'success'
          ? Haptics.NotificationFeedbackType.Success
          : Haptics.NotificationFeedbackType.Warning,
      );
    }
  } catch {
    // No haptic engine / permission: feedback is optional.
  }
}
