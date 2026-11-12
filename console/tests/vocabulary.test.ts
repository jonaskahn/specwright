import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { classWords, kindWords, knownKinds, knownRelations, relationWords, resolutionWords, stationWords } from '../src/lib/vocabulary';
import { GOLDEN, read, type Variant } from './golden';

const src = resolve(__dirname, '../src');
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

describe('kinds and relations are named in plain words', () => {
  it('names every kind and relation the graph model defines', () => {
    expect(kindWords('ac')).toBe('Acceptance criterion');
    expect(kindWords('ac', true)).toBe('Acceptance criteria');
    expect(kindWords('feat')).toBe('Feature');
    expect(kindWords('bo')).toBe('Business objective');
    expect(kindWords('cr')).toBe('Change request');
    expect(relationWords('has_ac', 'out')).toBe('has acceptance criterion');
    expect(relationWords('has_ac', 'in')).toBe('is an acceptance criterion of');
    expect(relationWords('implements', 'in')).toBe('is implemented by');
    expect(stationWords('dev')).toBe('Development');
    expect(classWords('mentioned')).toContain('passing');
    expect(resolutionWords('unresolved')).toBe('Not defined anywhere');
  });

  it('has words for every kind and relation in the golden data', () => {
    for (const variant of ['flat', 'program'] as Variant[]) {
      const graph = JSON.parse(read(variant, 'data/graph.json'));
      for (const node of graph.nodes) expect(knownKinds(), node.kind).toContain(node.kind);
      for (const edge of graph.edges) expect(knownRelations(), edge.rel).toContain(edge.rel);
    }
    expect(GOLDEN).toBeTruthy();
  });

  it('turns an unknown token into readable words rather than showing it raw', () => {
    expect(kindWords('some-new-kind')).toBe('Some new kind');
    expect(relationWords('brand_new_link')).toBe('brand new link');
  });
});

/** The words a person reads: template text, and a few attributes, of every component. */
function visibleText(file: string): string[] {
  const raw = readFileSync(file, 'utf-8');
  if (!file.endsWith('.svelte')) {
    return [...raw.matchAll(/(['"`])((?:(?!\1)[^\\\n]){6,})\1/g)].map((m) => m[2]).filter((t) => t.includes(' '));
  }
  const template = raw.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '');
  const text = [...template.matchAll(/>([^<>{}]+)</g)].map((m) => m[1]);
  const attrs = [...template.matchAll(/\s(?:placeholder|aria-label|title|lede|alt|label)="([^"{}]+)"/g)].map((m) => m[1]);
  const script = raw.match(/<script[\s\S]*?<\/script>/)?.[0] ?? '';
  const strings = [...script.matchAll(/(['"`])((?:(?!\1)[^\\\n]){6,})\1/g)].map((m) => m[2]).filter((t) => t.includes(' ') && !t.includes('/'));
  return [...text, ...attrs, ...strings];
}

const SHORT_FORMS: [RegExp, string][] = [
  [/\bACs?\b/, 'AC'],
  [/\bBOs?\b/, 'BO'],
  [/\bRTM\b/, 'RTM'],
  [/\bCRs?\b/, 'CR'],
  [/\bDEC\b/, 'DEC'],
  [/\bKPIs?\b/, 'KPI'],
  [/\bIDs?\b/, 'ID'],
  [/\bdev\b/i, 'dev'],
  [/\bNFRs?\b/, 'NFR'],
  [/\b\d+ (?:d|w|mo) ago\b/, 'short age'],
  [/\bwithout\b.*\bw\/o\b|\bw\/o\b/, 'w/o'],
];

describe('the screens spell words out', () => {
  it('uses no short form in any text a person reads', () => {
    const problems: string[] = [];
    for (const file of files(src).filter((f) => /\.(svelte|ts)$/.test(f))) {
      for (const text of visibleText(file)) {
        for (const [pattern, name] of SHORT_FORMS) {
          if (pattern.test(text)) problems.push(`${file.replace(src, 'src')}: ${name} in "${text.trim().slice(0, 70)}"`);
        }
      }
    }
    expect(problems).toEqual([]);
  });
});
