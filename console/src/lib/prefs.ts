// Appearance preferences, kept in this browser only. Storage can be blocked, so every access is guarded.

export const THEMES = ['light', 'dark', 'system'] as const;
export const ACCENTS = ['red', 'orange', 'amber', 'green', 'teal', 'cyan', 'blue', 'rose'] as const;
export const DENSITIES = ['comfortable', 'compact'] as const;
export const CRITERIA_VIEWS = ['cards', 'table'] as const;

export interface Prefs {
  theme: (typeof THEMES)[number];
  accent: (typeof ACCENTS)[number];
  density: (typeof DENSITIES)[number];
  folded: boolean;
  /** Keep the preview docked beside the page instead of floating over it. */
  previewPinned: boolean;
  /** Width of the preview panel in pixels; 0 means half the screen. */
  previewWidth: number;
  /** How a story's criteria are laid out in the preview. */
  criteriaView: (typeof CRITERIA_VIEWS)[number];
}

const KEY = 'specwright-';
export const DEFAULTS: Prefs = { theme: 'system', accent: 'red', density: 'comfortable', folded: false, previewPinned: false, previewWidth: 0, criteriaView: 'cards' };
/** The preview is half the screen until the user drags it; 0 stands for that. */
export const PREVIEW_WIDTH = { min: 380, share: 0.85 };

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

export function clampWidth(value: number): number {
  const room = Math.floor((globalThis.innerWidth ?? 1400) * PREVIEW_WIDTH.share);
  return Number.isFinite(value) && value > 0 ? Math.min(Math.max(PREVIEW_WIDTH.min, room), Math.max(PREVIEW_WIDTH.min, Math.round(value))) : DEFAULTS.previewWidth;
}

export function loadPrefs(): Prefs {
  return {
    theme: pick(THEMES, read('theme'), DEFAULTS.theme),
    accent: pick(ACCENTS, read('accent'), DEFAULTS.accent),
    density: pick(DENSITIES, read('density'), DEFAULTS.density),
    folded: read('folded') === '1',
    previewPinned: read('previewPinned') === '1',
    previewWidth: clampWidth(Number(read('previewWidth'))),
    criteriaView: pick(CRITERIA_VIEWS, read('criteriaView'), DEFAULTS.criteriaView),
  };
}

export function savePref(name: keyof Prefs, value: string | boolean | number): void {
  try {
    localStorage.setItem(KEY + name, typeof value === 'boolean' ? (value ? '1' : '0') : String(value));
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
