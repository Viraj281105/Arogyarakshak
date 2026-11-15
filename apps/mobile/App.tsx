import React, { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { ThemeProvider, useTheme } from './src/theme';
import { useLanguage } from './src/hooks/useLanguage';
import { useAppFonts } from './src/hooks/useAppFonts';
import { Header, OfflineBanner } from './src/components';
import { RootNavigator } from './src/navigation';
import { reducedMotionStore } from './src/motion/store';

const MOTION_PRIME_TIMEOUT_MS = 1500;

// Keep the native splash screen up until the bundled fonts are ready.
SplashScreen.preventAutoHideAsync().catch(() => {});

const AppContent: React.FC = () => {
  const { isDark, colors } = useTheme();
  const { language, setLanguage, t } = useLanguage('en');

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bgBase }}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <OfflineBanner />
      <Header
        title={t.appName}
        currentLanguage={language}
        onLanguageChange={setLanguage}
      />
      <NavigationContainer>
        <RootNavigator />
      </NavigationContainer>
    </SafeAreaView>
  );
};

export default function App() {
  const fontsReady = useAppFonts();
  const [motionReady, setMotionReady] = useState(false);

  // Learn the reduce-motion preference while the splash screen is up. A slow or failed read
  // must not block the app: the store falls back to "reduced" (final state) until it is known.
  useEffect(() => {
    const done = () => setMotionReady(true);
    const timer = setTimeout(done, MOTION_PRIME_TIMEOUT_MS);
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
        <AppContent />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
