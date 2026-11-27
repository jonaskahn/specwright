import { describe, expect, it } from 'vitest';
import type { DataKinds } from '../contract/types';
import { empty, loadAll } from '../src/lib/data/loader';
import { computeMetrics } from '../src/lib/data/metrics';
import { buildTree } from '../src/lib/data/selectors';
import { daysSince } from '../src/lib/format';
import { rungSteps, stateLook } from '../src/lib/status';
import { serve } from './golden';

const today = new Date(Date.UTC(2026, 10, 12));

describe('metrics', async () => {
  const flat = await loadAll('./data/', serve('flat'));
  const program = await loadAll('./data/', serve('program'));
  const trace = await loadAll('./data/', serve('trace'));

  it('counts the refund fixture', () => {
    const m = computeMetrics(flat, '*');
    expect(m.features).toBe(2);
    expect(m.acs).toBe(3);
    expect(m.tasks).toBe(0);
    expect(m.openQuestions).toBe(1);
    expect(m.lintPass).toBe(1);
    expect(m.lintFail).toBe(1);
    expect(m.attention.map((a) => a.id)).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
    expect(m.progress.every((p) => p.count === 0)).toBe(true);
  });

  it('lists one reason per story, then blocked tasks', () => {
    const m = computeMetrics(flat, '*');
    expect(m.attention).toEqual([
      { id: 'REF:FEAT-001', kind: 'feature', reason: '1 open question' },
      { id: 'REF:FEAT-002', kind: 'feature', reason: 'lint failing' },
    ]);
  });

  it('counts epics and records', () => {
    expect(computeMetrics(trace, '*').epics).toBe(2);
    expect(computeMetrics(flat, '*').epics).toBe(0);
    expect(computeMetrics(flat, '*').records).toBe(2);
  });

  it('puts a blocked task on the attention list and tallies progress', () => {
    const rows = trace.data.tasks!.rows.map((r, i) => ({ ...r, progress: (['done', 'in-progress', 'blocked', 'planned', 'not-started'] as const)[i] }));
    const m = computeMetrics({ ...trace, data: { ...trace.data, tasks: { ...trace.data.tasks!, rows } } }, '*');
    expect(m.blockedTasks).toBe(1);
    expect(m.attention.filter((a) => a.kind === 'task')).toEqual([{ id: 'REF:TASK-001-3', kind: 'task', reason: 'task blocked' }]);
    expect(m.progress.map((p) => [p.progress, p.count])).toEqual([['done', 1], ['in-progress', 1], ['blocked', 1], ['planned', 1], ['not-started', 1]]);
  });

  it('leaves a withdrawn task and a retired story out', () => {
    const tasks = trace.data.tasks!.rows.map((r, i) => (i === 0 ? { ...r, status: 'withdrawn' as const } : r));
    const feats = trace.data.features!.rows.map((r, i) => (i === 2 ? { ...r, state: 'withdrawn' } : r));
    const m = computeMetrics({ ...trace, data: { ...trace.data, tasks: { ...trace.data.tasks!, rows: tasks }, features: { ...trace.data.features!, rows: feats } } }, '*');
    expect(m.tasks).toBe(4);
    expect(m.features).toBe(2);
  });

  it('narrows to one project', () => {
    expect(computeMetrics(program, '*').features).toBe(4);
    expect(computeMetrics(program, 'ORD').features).toBe(2);
  });

  it('copes with no data at all', () => {
    const m = computeMetrics(empty('nodata'), '*');
    expect(m.features).toBe(0);
    expect(m.attention).toEqual([]);
  });

  it('builds the tree from graph links', () => {
    const roots = buildTree(program, '*');
    expect(roots.map((r) => r.key)).toEqual(['ORD', 'REF']);
    const find = (n: (typeof roots)[number]): (typeof roots)[number] | undefined => (n.key === 'ORD:FEAT-001' ? n : n.children.map(find).find(Boolean));
    const feature = find(roots[0]);
    expect(feature?.children.map((c) => c.key)).toEqual(['ORD:AC-001-1', 'ORD:AC-001-2']);
  });
});

describe('status and dates', () => {
  it('maps states to a shape, not only a colour', () => {
    expect(stateLook('in-review').shape).toBe('diamond');
    expect(stateLook('ready-for-dev').shape).toBe('check');
    expect(stateLook('withdrawn').shape).toBe('square');
    expect(stateLook('in-review', 'blocked').shape).toBe('triangle');
  });

  it('places the rung', () => {
    expect(rungSteps('in-review', null)).toEqual(['done', 'current', 'todo', 'todo', 'todo']);
    expect(rungSteps('in-review', 'blocked')[1]).toBe('blocked');
    expect(rungSteps('withdrawn', null)).toEqual(['off', 'off', 'off', 'off', 'off']);
  });

  it('counts days between absolute dates', () => {
    expect(daysSince('2026-11-10', today)).toBe(2);
    expect(daysSince(null, today)).toBeNull();
    expect(daysSince('not a date', today)).toBeNull();
  });
});

export type _Unused = DataKinds;
