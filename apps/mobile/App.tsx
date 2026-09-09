import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { ThemeProvider, useTheme } from './src/theme';
import { useLanguage } from './src/hooks/useLanguage';
import { Header, OfflineBanner } from './src/components';
import { RootNavigator } from './src/navigation';

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
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
