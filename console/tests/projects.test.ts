import { describe, expect, it } from 'vitest';
import { loadAll } from '../src/lib/data/loader';
import { acrossProjects, buildTree, crossLinks, filterTree, pathTo, projectGraph, type TreeNode } from '../src/lib/data/selectors';
import { buildTrace, traceCoverage } from '../src/lib/graph/trace';
import { serve } from './golden';

const walk = (n: TreeNode): TreeNode[] => [n, ...n.children.flatMap(walk)];

describe('a graph for one project', async () => {
  const program = await loadAll('./data/', serve('program'));

  it('holds that project\'s own items and nothing else of the other project', () => {
    const ord = projectGraph(program, 'ORD');
    const own = ord.nodes.filter((n) => !ord.foreign.has(n.key));
    expect(own.every((n) => n.scope === 'ORD' || n.scope === null)).toBe(true);
    expect(own.some((n) => n.key === 'ORD:FEAT-001')).toBe(true);
    expect(ord.nodes.some((n) => n.key === 'REF:FEAT-001')).toBe(false);
  });

  it('brings in the epic of another project that its feature belongs to', () => {
    const ord = projectGraph(program, 'ORD');
    expect([...ord.foreign]).toEqual(['REF:EPIC-001']);
    expect(ord.edges.some((e) => e.from === 'ORD:FEAT-001' && e.rel === 'member_of' && e.to === 'REF:EPIC-001')).toBe(true);
    expect(ord.edges.some((e) => e.from === 'REF:EPIC-001' && e.rel === 'realizes' && e.to === 'ORD:BO-001')).toBe(true);
  });

  it('draws that epic as another project\'s, and asks nothing of it', () => {
    const ord = projectGraph(program, 'ORD');
    const model = buildTrace(ord.nodes, ord.edges, { foreign: ord.foreign });
    const epic = model.nodes.find((n) => n.key === 'REF:EPIC-001')!;
    expect([epic.foreign, epic.scope]).toEqual([true, 'REF']);
    expect(model.links.some((l) => l.gap && l.rel === 'member_of' && l.right === 'ORD:FEAT-001')).toBe(false);
    expect(model.nodes.some((n) => n.gap === 'epic-bo')).toBe(false);
    expect(model.nodes.filter((n) => n.foreign).map((n) => n.key)).toEqual(['REF:EPIC-001']);
  });

  it('counts only the project\'s own items in its coverage', () => {
    const ord = projectGraph(program, 'ORD');
    const cover = Object.fromEntries(traceCoverage(ord.nodes, ord.edges, ord.foreign).map((c) => [c.id, [c.have, c.total]]));
    expect(cover.epic).toEqual([1, 2]);
    expect(traceCoverage(ord.nodes, ord.edges, ord.foreign).find((c) => c.id === 'epic-bo')).toBeUndefined();
  });

  it('keeps a feature without a link to another project missing it, as before', async () => {
    const flat = await loadAll('./data/', serve('flat'));
    const only = projectGraph(flat, 'REF');
    expect(only.foreign.size).toBe(0);
    expect(only.nodes.length).toBe(flat.data.graph!.nodes.length);
  });
});

describe('the links between projects', async () => {
  const program = await loadAll('./data/', serve('program'));

  it('counts links that join two projects', () => {
    expect(crossLinks(program)).toBe(2);
    return loadAll('./data/', serve('flat')).then((flat) => expect(crossLinks(flat)).toBe(0));
  });

  it('keeps only those links and the objective, epic and feature they join', () => {
    const across = acrossProjects(program);
    expect(across.nodes.map((n) => n.key).sort()).toEqual(['ORD:BO-001', 'ORD:FEAT-001', 'REF:EPIC-001']);
    expect(across.edges.map((e) => `${e.from} ${e.rel} ${e.to}`).sort()).toEqual([
      'ORD:FEAT-001 member_of REF:EPIC-001',
      'ORD:FEAT-001 realizes ORD:BO-001',
      'REF:EPIC-001 realizes ORD:BO-001',
    ]);
  });

  it('shows the project on every card of that map', () => {
    const across = acrossProjects(program);
    const model = buildTrace(across.nodes, across.edges, { gaps: false });
    expect(new Set(model.nodes.map((n) => n.scope))).toEqual(new Set(['ORD', 'REF']));
    expect(model.nodes.every((n) => !n.foreign)).toBe(true);
  });
});

describe('the outline follows the project graph', async () => {
  const program = await loadAll('./data/', serve('program'));

  it('shows another project\'s epic under the project whose feature belongs to it', () => {
    const [ord] = buildTree(program, 'ORD');
    const epic = walk(ord).find((n) => n.key === 'REF:EPIC-001')!;
    expect(epic.foreign).toBe('REF');
    expect(epic.children.map((c) => [c.key, c.foreign ?? null])).toEqual([
      ['ORD:FEAT-001', null],
      ['REF:FEAT-001', 'REF'],
    ]);
    expect(walk(ord).filter((n) => n.key === 'ORD:FEAT-001')).toHaveLength(1);
  });

  it('gives every feature a count of its criteria and tasks', () => {
    const [, ref] = buildTree(program, '*');
    const feature = walk(ref).find((n) => n.key === 'REF:FEAT-001' && n.kind === 'feat')!;
    expect(feature.counts).toEqual({ ac: 2, task: 0 });
  });

  it('filters to the matches and the parents above them', () => {
    const [ord] = buildTree(program, 'ORD');
    const hit = filterTree(ord, 'duplicate')!;
    const keys = walk(hit).map((n) => n.key);
    expect(keys).toContain('ORD:AC-001-2');
    expect(keys).toContain('ORD:FEAT-001');
    expect(keys).not.toContain('ORD:AC-001-1');
    expect(filterTree(ord, 'zzzz-no-such')).toBeNull();
    expect(filterTree(ord, '  ')).toBe(ord);
  });

  it('lists the items above a key, so the path to it can be opened', () => {
    const [ord] = buildTree(program, 'ORD');
    expect(pathTo(ord, 'ORD:AC-001-2')).toEqual(['ORD', 'REF:EPIC-001', 'ORD:FEAT-001']);
    expect(pathTo(ord, 'nope')).toBeNull();
  });
});
