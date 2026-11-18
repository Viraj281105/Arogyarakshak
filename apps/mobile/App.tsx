import React, { useEffect, useMemo, useState } from 'react';
import { View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { ThemeProvider, useTheme } from './src/theme';
import { useLanguage } from './src/hooks/useLanguage';
import { useAppFonts } from './src/hooks/useAppFonts';
import { Header, OfflineBanner } from './src/components';
import { RootNavigator } from './src/navigation';
import { reducedMotionStore } from './src/motion/store';
import { navigationTheme } from './src/shell/logic';

const MOTION_PRIME_TIMEOUT_MS = 1500;

// Keep the native splash screen up until the bundled fonts are ready.
SplashScreen.preventAutoHideAsync().catch(() => {});

/**
 * App shell: themed status bar, header (pads the top safe-area inset), offline banner, and the
 * navigators (the tab bar pads the bottom inset). The navigation theme comes from the tokens so
 * navigator backgrounds match the app in both schemes.
 */
const AppShell: React.FC = () => {
  const { isDark, colors } = useTheme();
  const { language, setLanguage, t } = useLanguage('en');
  const navTheme = useMemo(() => navigationTheme(isDark, colors), [isDark, colors]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.bgBase }}>
      <StatusBar style={isDark ? 'light' : 'dark'} backgroundColor={colors.bgSurface} />
      <Header title={t.appName} currentLanguage={language} onLanguageChange={setLanguage} />
      <OfflineBanner />
      <NavigationContainer theme={navTheme}>
        <RootNavigator />
      </NavigationContainer>
    </View>
  );
};

export default function App() {
  const fontsReady = useAppFonts();
  const [motionReady, setMotionReady] = useState(false);

  // Learn the reduce-motion preference while the splash screen is up. A slow or failed read
  // must not block the app: the store falls back to "reduced" (final state) until it is known.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const done = () => {
      clearTimeout(timer);
      setMotionReady(true);
    };
    timer = setTimeout(done, MOTION_PRIME_TIMEOUT_MS);
    reducedMotionStore.prime().then(done, done);
    return () => clearTimeout(timer);
  }, []);

  const ready = fontsReady && motionReady;

  useEffect(() => {
    if (ready) {
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [ready]);

  if (!ready) {
    return null;
  }

  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AppShell />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
