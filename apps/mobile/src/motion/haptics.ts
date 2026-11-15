import { AccessibilityInfo } from 'react-native';
import * as Haptics from 'expo-haptics';
import { readReducedMotion, shouldAnimate } from './logic';

export type HapticKind = 'light' | 'success' | 'warning';

/** Haptic tap. No-op under reduced motion; swallows errors (devices without a haptic engine). */
export async function tap(kind: HapticKind): Promise<void> {
  try {
    if (!shouldAnimate(await readReducedMotion(AccessibilityInfo))) return;
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
