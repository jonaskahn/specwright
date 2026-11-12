import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = resolve(__dirname, '../src');
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

describe('imported text is data, and the page stays CSP-clean', () => {
  const sources = files(src).filter((f) => /\.(svelte|ts|css)$/.test(f));

  it('never renders text as HTML', () => {
    for (const file of sources) expect(readFileSync(file, 'utf-8'), file).not.toMatch(/\{@html/);
  });

  it('writes no inline style attributes or inline event handler strings', () => {
    for (const file of files(src).filter((f) => f.endsWith('.svelte'))) {
      const text = readFileSync(file, 'utf-8');
      expect(text, file).not.toMatch(/\sstyle="/);
      expect(text, file).not.toMatch(/\son[a-z]+="/);
    }
  });

  it('makes no network calls beyond its own origin', () => {
    for (const file of sources) {
      expect(readFileSync(file, 'utf-8'), file).not.toMatch(/https?:\/\/(?!www\.w3\.org)/);
    }
  });

  it('ships a strict policy and no inline script', () => {
    const html = readFileSync(resolve(__dirname, '../index.html'), 'utf-8');
    const config = readFileSync(resolve(__dirname, '../vite.config.ts'), 'utf-8');
    expect(config).toContain("default-src 'none'");
    expect(config).toContain("script-src 'self'");
    expect(config).toContain("style-src 'self'");
    expect(html).not.toMatch(/<script(?![^>]*\ssrc=)/);
  });
});
