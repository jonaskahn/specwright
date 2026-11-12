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

  it('counts the refund fixture', () => {
    const m = computeMetrics(flat, '*', today);
    expect(m.features).toBe(2);
    expect(m.acs).toBe(3);
    expect(m.byState.map((s) => s.state)).toEqual(['draft', 'in-review']);
    expect(m.openQuestions).toBe(1);
    expect(m.lintPass).toBe(1);
    expect(m.lintFail).toBe(1);
    expect(m.bo).toEqual([{ bo: 'BO-001', features: 1 }]);
    expect(m.attention.map((a) => a.id)).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
  });

  it('derives idle features from absolute dates', () => {
    expect(computeMetrics(flat, '*', new Date(Date.UTC(2026, 10, 1))).idle).toBe(0);
    expect(computeMetrics(flat, '*', new Date(Date.UTC(2026, 10, 11))).idle).toBe(1);
    expect(computeMetrics(flat, '*', new Date(Date.UTC(2027, 0, 1))).idle).toBe(2);
  });

  it('narrows to one project', () => {
    expect(computeMetrics(program, '*', today).features).toBe(4);
    expect(computeMetrics(program, 'ORD', today).features).toBe(2);
  });

  it('copes with no data at all', () => {
    const m = computeMetrics(empty('nodata'), '*', today);
    expect(m.features).toBe(0);
    expect(m.ready).toBe(0);
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
