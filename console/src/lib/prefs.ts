// Appearance preferences, kept in this browser only. Storage can be blocked, so every access is guarded.

export const THEMES = ['light', 'dark', 'system'] as const;
export const ACCENTS = ['red', 'orange', 'amber', 'green', 'teal', 'cyan', 'blue', 'rose'] as const;
export const DENSITIES = ['comfortable', 'compact'] as const;

export interface Prefs {
  theme: (typeof THEMES)[number];
  accent: (typeof ACCENTS)[number];
  density: (typeof DENSITIES)[number];
  folded: boolean;
}

const KEY = 'specwright-';
export const DEFAULTS: Prefs = { theme: 'system', accent: 'red', density: 'comfortable', folded: false };

function read(name: string): string | null {
  try {
    return localStorage.getItem(KEY + name);
  } catch {
    return null;
  }
}

function pick<T extends string>(list: readonly T[], value: string | null, fallback: T): T {
  return (list as readonly string[]).includes(value ?? '') ? (value as T) : fallback;
}

export function loadPrefs(): Prefs {
  return {
    theme: pick(THEMES, read('theme'), DEFAULTS.theme),
    accent: pick(ACCENTS, read('accent'), DEFAULTS.accent),
    density: pick(DENSITIES, read('density'), DEFAULTS.density),
    folded: read('folded') === '1',
  };
}

export function savePref(name: keyof Prefs, value: string | boolean): void {
  try {
    localStorage.setItem(KEY + name, typeof value === 'boolean' ? (value ? '1' : '0') : value);
  } catch {
    /* blocked storage: the choice lasts for this page only */
  }
}

export function applyPrefs(prefs: Prefs, root: HTMLElement = document.documentElement): void {
  const dark = prefs.theme === 'dark' || (prefs.theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  root.setAttribute('data-theme', dark ? 'dark' : 'light');
  root.setAttribute('data-accent', prefs.accent);
  root.setAttribute('data-density', prefs.density);
}
