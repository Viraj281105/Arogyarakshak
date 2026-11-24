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

/**
 * `forcedMode` pins a nested provider to one theme regardless of the system scheme (used by the
 * dev primitives gallery to show both themes on one screen). The app root does not pass it.
 */
export const ThemeProvider = ({ children, forcedMode }: { children: ReactNode; forcedMode?: ThemeMode }) => {
  const systemScheme = useColorScheme();
  const [mode, setMode] = useState<ThemeMode>(forcedMode ?? (systemScheme === 'light' ? 'light' : 'dark'));

  useEffect(() => {
    if (forcedMode) {
      setMode(forcedMode);
    } else if (systemScheme) {
      setMode(systemScheme);
    }
  }, [systemScheme, forcedMode]);

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
