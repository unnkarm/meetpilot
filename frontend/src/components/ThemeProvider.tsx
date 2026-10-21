import { createContext, useContext, useEffect, useLayoutEffect, useState, type ReactNode } from 'react';
import { paletteColor, parseColorPalette, parseThemePreference, resolveTheme, PALETTE_STORAGE_KEY, THEME_STORAGE_KEY, type ColorPalette, type ResolvedTheme, type ThemePreference } from '../utils/theme';

const ThemeContext = createContext<{
  preference: ThemePreference; theme: ResolvedTheme; setPreference: (value: ThemePreference) => void;
  palette: ColorPalette; setPalette: (value: ColorPalette) => void;
} | null>(null);

function readPreference() {
  try { return parseThemePreference(localStorage.getItem(THEME_STORAGE_KEY)); }
  catch { return 'dark' as const; }
}

function readPalette() {
  try { return parseColorPalette(localStorage.getItem(PALETTE_STORAGE_KEY)); }
  catch { return 'indigo' as const; }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(readPreference);
  const [palette, setPaletteState] = useState<ColorPalette>(readPalette);
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches);
  const theme = resolveTheme(preference, systemDark);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const updateSystem = () => setSystemDark(media.matches);
    const updateStorage = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY || event.key === null) setPreferenceState(readPreference());
      if (event.key === PALETTE_STORAGE_KEY || event.key === null) setPaletteState(readPalette());
    };
    updateSystem();
    media.addEventListener('change', updateSystem);
    window.addEventListener('storage', updateStorage);
    return () => { media.removeEventListener('change', updateSystem); window.removeEventListener('storage', updateStorage); };
  }, []);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.palette = palette;
    document.documentElement.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#090b10' : paletteColor(palette, theme));
  }, [theme, palette]);

  function setPreference(value: ThemePreference) {
    setPreferenceState(value);
    try { localStorage.setItem(THEME_STORAGE_KEY, value); } catch { /* Works for this tab when browser storage is unavailable. */ }
  }
  function setPalette(value: ColorPalette) {
    setPaletteState(value);
    try { localStorage.setItem(PALETTE_STORAGE_KEY, value); } catch { /* Retain the choice for this tab. */ }
  }
  return <ThemeContext.Provider value={{ preference, theme, setPreference, palette, setPalette }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme requires ThemeProvider');
  return context;
}
