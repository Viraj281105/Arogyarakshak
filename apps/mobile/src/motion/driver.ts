import { Easing, Platform } from 'react-native';
import { STANDARD_BEZIER } from './logic';

/**
 * The motion system animates with React Native's built-in Animated API (already in the bundle)
 * rather than Reanimated: Reanimated measured +785,115 B on the Android Hermes bundle, over the
 * 2,900,000 B budget (docs/development/performance-budgets.md). Only opacity/transform are
 * animated, so the native driver runs them off the JS thread on device. react-native-web has no
 * native driver, so the browser preview runs them on JS.
 */
export const NATIVE_DRIVER = Platform.OS !== 'web';

export const STANDARD_EASING = Easing.bezier(...STANDARD_BEZIER);
