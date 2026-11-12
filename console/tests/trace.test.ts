import { describe, expect, it } from 'vitest';
import type { GraphEdge, GraphNode } from '../contract/types';
import { BOX, buildTrace, chainOf, focusModel, traceCoverage } from '../src/lib/graph/trace';
import { read, type Variant } from './golden';

function load(variant: Variant): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const doc = JSON.parse(read(variant, 'data/graph.json'));
  return { nodes: doc.nodes, edges: doc.edges };
}

const { nodes, edges } = load('trace');
const jira = new Map(
  (JSON.parse(read('trace', 'data/registry.json')).rows as { id: string; jiraKey: string | null }[]).filter((r) => r.jiraKey).map((r) => [r.id, r.jiraKey as string]),
);
const model = buildTrace(nodes, edges, { code: true, jira });
const plain = buildTrace(nodes, edges, { jira });
const byKey = (key: string) => model.nodes.find((n) => n.key === key)!;
const gaps = () => model.nodes.filter((n) => n.gap).map((n) => `${n.gap}:${n.id.split(':').slice(2).join(':')}`).sort();

describe('the trace map lays the chain out from why to how', () => {
  it('puts each kind in its own column, left to right', () => {
    expect(model.levels).toEqual([0, 1, 2, 3, 4, 5]);
    const xs = (kind: string) => new Set(model.nodes.filter((n) => n.kind === kind && !n.gap).map((n) => n.x));
    for (const kind of ['bo', 'epic', 'feat', 'ac', 'task', 'code']) expect(xs(kind).size, kind).toBe(1);
    expect([...xs('bo')][0]).toBeLessThan([...xs('epic')][0]);
    expect([...xs('ac')][0]).toBeLessThan([...xs('task')][0]);
    expect([...xs('task')][0]).toBeLessThan([...xs('code')][0]);
  });

  it('draws only links the data holds, each from the lower level to the higher one', () => {
    const real = model.links.filter((l) => !l.gap);
    expect(real.every((l) => byKey(l.left).level < byKey(l.right).level)).toBe(true);
    const sentence = (text: string) => real.some((l) => l.sentence === text);
    expect(sentence('Submit a refund request belongs to epic Self-service refunds')).toBe(true);
    expect(sentence('Submit a refund request serves business objective Reduce refund waiting time')).toBe(true);
    expect(sentence('Refuse a duplicate implements Duplicate request')).toBe(true);
    expect(real.filter((l) => l.rel === 'implements')).toHaveLength(5);
    expect(real.filter((l) => l.rel === 'has_ac')).toHaveLength(5);
  });

  it('stops at tasks unless code files are asked for', () => {
    expect(plain.levels).toEqual([0, 1, 2, 3, 4]);
    expect(plain.nodes.some((n) => n.kind === 'code')).toBe(false);
    expect(model.nodes.filter((n) => n.kind === 'code').map((n) => n.title)).toEqual(['src/decide.py', 'src/notify.py', 'src/refund.py']);
  });

  it('shows a Jira issue on the card of any item the registry gives one, never as a node', () => {
    expect(byKey('REF:FEAT-001').jira).toBe('PROJ-101');
    expect(byKey('REF:EPIC-001').jira).toBe('PROJ-100');
    expect(byKey('REF:FEAT-002').jira).toBeNull();
    expect(model.nodes.some((n) => n.kind === 'jira')).toBe(false);
  });

  it('never gives a task a Jira key: tasks stay in Markdown', () => {
    expect(model.nodes.filter((n) => n.kind === 'task').every((n) => n.jira === null)).toBe(true);
  });

  it('shows every missing link as a placeholder that names the skill to ask', () => {
    expect(gaps()).toEqual([
      'bo:REF:FEAT-002',
      'epic:REF:FEAT-003',
      'task-criterion:REF:TASK-001-3',
      'task:REF:AC-003-2',
    ]);
    const epic = model.nodes.find((n) => n.id === 'gap:epic:REF:FEAT-003')!;
    expect([epic.title, epic.next, epic.level]).toEqual(['No epic yet', 'sw-shape', 1]);
    expect(model.nodes.find((n) => n.id === 'gap:task:REF:AC-003-2')!.next).toBe('sw-plan');
    expect(model.nodes.find((n) => n.id === 'gap:bo:REF:FEAT-002')!.next).toBe('sw-shape');
  });

  it('lists a reference to something nobody defined', () => {
    expect(model.broken.map((b) => b.sentence)).toEqual(['Decide a refund request mentions FEAT-009, which is not defined anywhere']);
  });

  it('measures how complete the chain is', () => {
    const cover = Object.fromEntries(traceCoverage(nodes, edges).map((c) => [c.id, [c.have, c.total, c.gaps]]));
    expect(cover).toEqual({
      epic: [2, 3, ['REF:FEAT-003']],
      bo: [2, 3, ['REF:FEAT-002']],
      ac: [3, 3, []],
      covered: [4, 5, ['REF:AC-003-2']],
      tied: [4, 5, ['REF:TASK-001-3']],
    });
  });

  it('follows the whole chain up and down from any item', () => {
    const criterion = chainOf(model, 'REF:AC-001-2').nodes;
    for (const key of ['REF:FEAT-001', 'REF:EPIC-001', 'REF:BO-001', 'REF:TASK-001-2', 'REF:code/src/notify.py']) expect(criterion.has(key), key).toBe(true);
    expect(criterion.has('REF:FEAT-002')).toBe(false);
    const feature = chainOf(model, 'REF:FEAT-003').nodes;
    expect(feature.has('gap:epic:REF:FEAT-003')).toBe(true);
    expect(feature.has('REF:BO-002')).toBe(true);
  });

  it('is deterministic and never overlaps two items in a column', () => {
    expect(JSON.stringify(buildTrace(nodes, edges, { code: true, jira }))).toBe(JSON.stringify(model));
    const seen = new Set<string>();
    for (const n of model.nodes) {
      const at = `${n.x},${n.y}`;
      expect(seen.has(at), at).toBe(false);
      seen.add(at);
    }
    expect(model.height).toBeGreaterThanOrEqual(BOX.top + BOX.h);
  });

  it('can keep just one chain when the map is too large to read whole', () => {
    const slim = focusModel(nodes, edges, 'REF:AC-003-1');
    const keys = slim.nodes.map((n) => n.id);
    expect(keys).toContain('REF:AC-003-2');
    expect(keys).toContain('REF:BO-002');
    expect(keys).not.toContain('REF:FEAT-001');
  });

  it('says so when a level does not exist yet instead of drawing placeholders for all', () => {
    const flat = load('flat');
    const sparse = buildTrace(flat.nodes, flat.edges);
    expect(sparse.notes).toEqual(['No epic is defined, so features are shown without one.', 'No task is planned yet, so criteria are shown without tasks.']);
    expect(sparse.nodes.filter((n) => n.gap).map((n) => n.gap)).toEqual(['bo']);
    expect(traceCoverage(flat.nodes, flat.edges).map((c) => c.id)).toEqual(['bo', 'ac']);
  });
});
