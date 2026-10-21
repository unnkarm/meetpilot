export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';
export const THEME_STORAGE_KEY = 'meetpilot:theme';
export const PALETTE_STORAGE_KEY = 'meetpilot:palette';
export const COLOR_PALETTES = [
  { id: 'indigo', label: 'Blue & purple', description: 'The original MeetPilot colors.', light: '#6640d8', dark: '#b7a5ff', swatches: ['#8b5cf6', '#5b8def', '#c7b7ff'] },
  { id: 'blue', label: 'Ocean blue', description: 'Cool, clear and focused.', light: '#2362c6', dark: '#8dbbff', swatches: ['#3478db', '#5ac8e4', '#a8d6ff'] },
  { id: 'teal', label: 'Teal', description: 'Calm greens and fresh accents.', light: '#176b5e', dark: '#75d7bf', swatches: ['#268b78', '#75d7bf', '#b4e8cb'] },
  { id: 'rose', label: 'Rose', description: 'Warm pink with a softer feel.', light: '#ac3469', dark: '#f2a6c7', swatches: ['#cf5b8f', '#ee92b7', '#e3b2e8'] },
  { id: 'amber', label: 'Amber', description: 'Warm gold and earthy tones.', light: '#8a580b', dark: '#efc27a', swatches: ['#bb821e', '#efc27a', '#e6d2a7'] },
] as const;
export type ColorPalette = typeof COLOR_PALETTES[number]['id'];

export function parseThemePreference(value: string | null): ThemePreference {
  return value === 'light' || value === 'system' ? value : 'dark';
}

export function parseColorPalette(value: string | null): ColorPalette {
  return COLOR_PALETTES.find(palette => palette.id === value)?.id || 'indigo';
}

export function paletteColor(palette: ColorPalette, theme: ResolvedTheme) {
  return COLOR_PALETTES.find(choice => choice.id === palette)![theme];
}

export function resolveTheme(preference: ThemePreference, systemDark: boolean): ResolvedTheme {
  return preference === 'system' ? (systemDark ? 'dark' : 'light') : preference;
}
