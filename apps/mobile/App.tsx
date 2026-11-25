import React, { useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { DevSettings, Platform, View } from 'react-native';
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
import { getSessionStatus, hydrateSession, signOut, subscribeSession } from './src/api/session';
import { hydrateLanguage } from './src/services/languageStore';
import { SignInScreen } from './src/screens/SignInScreen';
import { LoadingState } from './src/components/ui/States';

const MOTION_PRIME_TIMEOUT_MS = 1500;

// DEV ONLY primitives gallery (Wave 3 M2). The require sits inside a `__DEV__` conditional, so
// Metro's production transform folds it away and the gallery is not in release bundles
// (tests/primitives.test.ts keeps this shape; the M2 handoff records the bundle check).
const PrimitivesGallery: React.ComponentType<{ onExit?: () => void }> | null = __DEV__
  ? require('./src/dev/PrimitivesGallery').PrimitivesGallery
  : null;

/** Web preview: `?gallery` in the URL opens the gallery. Native: the dev menu item below. */
function galleryRequested(): boolean {
  if (!__DEV__ || Platform.OS !== 'web') return false;
  try {
    return new URLSearchParams(globalThis.location?.search ?? '').has('gallery');
  } catch {
    return false;
  }
}

function useDevGallery(): [boolean, (open: boolean) => void] {
  const [open, setOpen] = useState(galleryRequested);
  useEffect(() => {
    if (__DEV__ && Platform.OS !== 'web') {
      DevSettings.addMenuItem('Primitives gallery', () => setOpen((v) => !v));
    }
  }, []);
  return [open, setOpen];
}

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
  const [galleryOpen, setGalleryOpen] = useDevGallery();
  const session = useSyncExternalStore(subscribeSession, getSessionStatus, getSessionStatus);

  useEffect(() => {
    void hydrateLanguage();
    void hydrateSession();
  }, []);

  if (__DEV__ && PrimitivesGallery && galleryOpen) {
    return <PrimitivesGallery onExit={Platform.OS === 'web' ? undefined : () => setGalleryOpen(false)} />;
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bgBase }}>
      <StatusBar style={isDark ? 'light' : 'dark'} backgroundColor={colors.bgSurface} />
      <Header
        title={t.appName}
        currentLanguage={language}
        onLanguageChange={setLanguage}
        onSignOut={session === 'signed-in' ? () => void signOut() : undefined}
        signOutLabel={t.auth.signOut}
      />
      <OfflineBanner />
      {/* Everything behind the sign-in screen needs an account session (ADR-029). */}
      {session === 'signed-in' ? (
        <NavigationContainer theme={navTheme}>
          <RootNavigator />
        </NavigationContainer>
      ) : session === 'loading' ? (
        <LoadingState label={t.auth.checking} />
      ) : (
        <SignInScreen status={session} />
      )}
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
