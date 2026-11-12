import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Fetcher } from '../src/lib/data/loader';

export const GOLDEN = resolve(__dirname, '../../workshop/fixtures/console-golden');
export type Variant = 'flat' | 'program';

export function read(variant: Variant, name: string): string {
  return readFileSync(resolve(GOLDEN, variant, name), 'utf-8');
}

/** A fetcher that serves a golden data folder, with optional per-file overrides. */
export function serve(variant: Variant, overrides: Record<string, string | null> = {}): Fetcher {
  return async (url) => {
    const name = url.replace(/^.*\//, '');
    const body = name in overrides ? overrides[name] : read(variant, `data/${name}`);
    if (body === null) return { ok: false, status: 404, text: async () => '' };
    return { ok: true, status: 200, text: async () => body };
  };
}
