import { useEffect, useState } from 'react';
import { useFonts } from 'expo-font';
// Deep imports so only the weights we use are bundled (the package root pulls in every weight).
import { Fraunces_400Regular } from '@expo-google-fonts/fraunces/400Regular';
import { Fraunces_500Medium } from '@expo-google-fonts/fraunces/500Medium';
import { Fraunces_600SemiBold } from '@expo-google-fonts/fraunces/600SemiBold';
import { PlusJakartaSans_500Medium } from '@expo-google-fonts/plus-jakarta-sans/500Medium';
import { PlusJakartaSans_600SemiBold } from '@expo-google-fonts/plus-jakarta-sans/600SemiBold';
import { PlusJakartaSans_700Bold } from '@expo-google-fonts/plus-jakarta-sans/700Bold';
import { PlusJakartaSans_800ExtraBold } from '@expo-google-fonts/plus-jakarta-sans/800ExtraBold';
import { Inter_400Regular } from '@expo-google-fonts/inter/400Regular';
import { Inter_500Medium } from '@expo-google-fonts/inter/500Medium';
import { Inter_600SemiBold } from '@expo-google-fonts/inter/600SemiBold';
import { Inter_700Bold } from '@expo-google-fonts/inter/700Bold';
import { JetBrainsMono_400Regular } from '@expo-google-fonts/jetbrains-mono/400Regular';
import { JetBrainsMono_500Medium } from '@expo-google-fonts/jetbrains-mono/500Medium';
import { JetBrainsMono_600SemiBold } from '@expo-google-fonts/jetbrains-mono/600SemiBold';
import { JetBrainsMono_700Bold } from '@expo-google-fonts/jetbrains-mono/700Bold';
import { devWarn } from '../logging';
import { FONT_LOAD_TIMEOUT_MS, fontGate } from './fontGate';

/**
 * Loads the bundled font files (Fraunces, Plus Jakarta Sans, Inter, JetBrains Mono).
 * The files ship inside the app binary — nothing is fetched at runtime.
 *
 * Returns true once the app may render: fonts loaded, loading failed, or FONT_LOAD_TIMEOUT_MS
 * passed (a never-settling load must not hold the splash screen forever). In the last two cases
 * the app proceeds with system fonts. Use `font()` / `textStyles` from src/theme to apply them.
 */
export function useAppFonts(): boolean {
  const [loaded, error] = useFonts({
    Fraunces_400Regular,
    Fraunces_500Medium,
    Fraunces_600SemiBold,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
    PlusJakartaSans_800ExtraBold,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    JetBrainsMono_400Regular,
    JetBrainsMono_500Medium,
    JetBrainsMono_600SemiBold,
    JetBrainsMono_700Bold,
  });
  const [timedOut, setTimedOut] = useState(false);
  const settled = loaded || error != null;

  useEffect(() => {
    if (settled) return;
    const timer = setTimeout(() => setTimedOut(true), FONT_LOAD_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [settled]);

  const gate = fontGate({ loaded, error, timedOut });

  useEffect(() => {
    if (gate.reason === 'error') {
      devWarn('[useAppFonts] Font load failed, continuing with system fonts:', error);
    } else if (gate.reason === 'timeout') {
      devWarn(`[useAppFonts] Fonts not ready after ${FONT_LOAD_TIMEOUT_MS} ms, continuing with system fonts.`);
    }
  }, [gate.reason, error]);

  return gate.ready;
}
