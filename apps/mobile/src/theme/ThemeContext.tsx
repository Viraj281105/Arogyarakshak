import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { ColorPalette, darkColors, lightColors } from './colors';
import { spacing, radii } from './spacing';
import { typography } from './typography';

export type ThemeMode = 'dark' | 'light';

interface ThemeContextType {
  mode: ThemeMode;
  isDark: boolean;
  colors: ColorPalette;
  spacing: typeof spacing;
  radii: typeof radii;
  typography: typeof typography;
  toggleTheme: () => void;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const systemScheme = useColorScheme();
  const [mode, setMode] = useState<ThemeMode>(systemScheme === 'light' ? 'light' : 'dark');

  useEffect(() => {
    if (systemScheme) {
      setMode(systemScheme);
    }
  }, [systemScheme]);

  const toggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const colors = mode === 'dark' ? darkColors : lightColors;

  return (
    <ThemeContext.Provider
      value={{
        mode,
        isDark: mode === 'dark',
        colors,
        spacing,
        radii,
        typography,
        toggleTheme,
        setMode,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
