import { describe, expect, it } from 'vitest';
import type { GraphData } from '../contract/types';
import { GraphIndex } from '../src/lib/query/engine';
import { runQuery } from '../src/lib/query/parse';
import { read, type Variant } from './golden';

interface Case {
  type: string;
  args: Record<string, unknown>;
  expect: unknown;
}

for (const variant of ['flat', 'program'] as Variant[]) {
  describe(`graph query parity (${variant})`, () => {
    const graph: GraphData = JSON.parse(read(variant, 'data/graph.json'));
    const index = new GraphIndex(graph.nodes, graph.edges);
    const cases: Case[] = JSON.parse(read(variant, 'expected-queries.json'));

    it('has cases to replay', () => expect(cases.length).toBeGreaterThan(40));

    for (const c of cases) {
      it(`${c.type} ${JSON.stringify(c.args)}`, () => {
        const a = c.args as Record<string, any>;
        switch (c.type) {
          case 'find':
            expect(index.find({ text: a.text, kind: a.kind ?? undefined, status: a.status ?? undefined }).map((n) => n.key)).toEqual(c.expect);
            break;
          case 'neighbors':
            expect(index.neighbors(a.key, a.dir, undefined, a.declaredOnly ?? false).map((r) => [r.side, r.rel, r.other, r.cls, r.res])).toEqual(c.expect);
            break;
          case 'up':
            expect(index.up(a.key).map((r) => [r.level, r.key, r.rel])).toEqual(c.expect);
            break;
          case 'down':
            expect(index.down(a.key, a.depth).map((r) => [r.level, r.key, r.rel])).toEqual(c.expect);
            break;
          case 'impact':
            expect(index.impact(a.key)).toEqual(c.expect);
            break;
          case 'path': {
            const r = index.path(a.from, a.to);
            expect({ found: r.found, hops: r.hops.map((h) => [h.from, h.side, h.rel, h.to, h.cls, h.res]) }).toEqual(c.expect);
            break;
          }
          default:
            throw new Error(`unknown case ${c.type}`);
        }
      });
    }
  });
}

describe('query text', () => {
  const graph: GraphData = JSON.parse(read('flat', 'data/graph.json'));
  const index = new GraphIndex(graph.nodes, graph.edges);

  it('treats bare words as find', () => {
    const r = runQuery(index, 'refund');
    expect(r.type).toBe('nodes');
  });

  it('runs path with two names', () => {
    const r = runQuery(index, 'path REF:Q-001 REF:AC-001-1');
    expect(r).toMatchObject({ type: 'path', found: true });
  });

  it('reports an unknown ID as an error, not an exception', () => {
    const r = runQuery(index, 'impact REF:NOPE-9');
    expect(r).toMatchObject({ type: 'error' });
  });

  it('resolves names, aliases and titles', () => {
    expect(index.resolve('FEAT-001')).toBe('REF:FEAT-001');
    expect(index.resolve('Submit a refund', true)).toBe('REF:FEAT-001');
    expect(() => index.resolve('does not exist')).toThrow();
  });

  it('asks which one when a name exists in several projects', () => {
    const program: GraphData = JSON.parse(read('program', 'data/graph.json'));
    const both = new GraphIndex(program.nodes, program.edges);
    expect(() => both.resolve('FEAT-001')).toThrow(/several/);
    expect(both.resolve('ORD:FEAT-001')).toBe('ORD:FEAT-001');
  });
});
