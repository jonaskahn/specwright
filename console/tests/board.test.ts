import { describe, expect, it } from 'vitest';
import { applyFilters, buildCards, columnOf, COLUMNS, conditionOf, idleTone, lanes, layerSplit, NO_FILTERS, sortCards, statsOf, summary } from '../src/lib/board';
import { loadAll } from '../src/lib/data/loader';
import { serve } from './golden';

const today = new Date('2026-11-12T00:00:00Z');

describe('the board', async () => {
  const trace = await loadAll('./data/', serve('trace'));
  const program = await loadAll('./data/', serve('program'));
  const cards = buildCards(trace, today, false);
  const byId = (id: string) => cards.find((c) => c.feature.id === id)!;

  it('puts a feature in the column of its station, and a planned one under ready for dev', () => {
    expect(byId('REF:FEAT-001').column).toBe('review');
    expect(byId('REF:FEAT-002').column).toBe('spec');
    expect(columnOf({ station: 'plan', condition: 'in-progress' })).toBe('plan');
    expect(columnOf({ station: 'plan', condition: 'complete' })).toBe('dev');
    expect(columnOf({ station: 'inactive', condition: 'complete' })).toBe('inactive');
    expect(columnOf({ station: null, condition: null })).toBe('other');
    expect(columnOf({ station: 'somewhere', condition: null })).toBe('other');
  });

  it('knows what skill moves each column on, and that the last ones have none', () => {
    const skill = Object.fromEntries(COLUMNS.map((c) => [c.id, c.skill]));
    expect(skill).toMatchObject({ shape: 'sw-spec', spec: 'sw-review', review: 'sw-review', plan: 'sw-plan', publish: 'sw-publish', dev: null, inactive: null });
  });

  it('gives the command to run, with the project only when several are in view', () => {
    expect(byId('REF:FEAT-001').command).toBe('/sw-review FEAT-001');
    expect(buildCards(program, today, true).find((c) => c.feature.id === 'ORD:FEAT-001')!.command).toBe('/sw-review ORD:FEAT-001');
    expect(buildCards({ ...trace, data: { ...trace.data, features: { ...trace.data.features!, rows: [{ ...trace.data.features!.rows[0], station: 'dev', condition: 'complete' }] } } }, today, false)[0].command).toBeNull();
  });

  it('adds the epics of a feature, from the graph', () => {
    expect(byId('REF:FEAT-001').epics).toEqual([{ key: 'REF:EPIC-001', title: 'Self-service refunds' }]);
    expect(byId('REF:FEAT-003').epics).toEqual([]);
  });

  it('splits a feature\'s tasks by layer', () => {
    expect(byId('REF:FEAT-001').layers).toEqual([['backend', 3]]);
    expect(layerSplit([['backend', 2], ['frontend', 1], ['qa', 1]])).toBe('BE 2 · FE 1 · QA 1');
  });

  it('measures how long a feature has been idle, and when that is too long', () => {
    expect(byId('REF:FEAT-001').idle).toBe(2);
    expect(byId('REF:FEAT-002').idle).toBe(16);
    expect([idleTone(null), idleTone(14), idleTone(15), idleTone(30), idleTone(31)]).toEqual(['ok', 'ok', 'warn', 'warn', 'danger']);
  });

  it('reads the condition, treating anything unknown as other', () => {
    expect(conditionOf({ condition: 'blocked' })).toBe('blocked');
    expect(conditionOf({ condition: null })).toBe('other');
  });

  it('filters by text, epic, condition, turn, project and idleness together', () => {
    const ids = (f: Partial<typeof NO_FILTERS>) => applyFilters(cards, { ...NO_FILTERS, ...f }).map((c) => c.feature.id);
    expect(ids({ text: 'self-service' })).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
    expect(ids({ epic: 'REF:EPIC-001' })).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
    expect(ids({ turn: 'BA' })).toEqual(['REF:FEAT-003']);
    expect(ids({ stale: true })).toEqual(['REF:FEAT-002']);
    expect(ids({ stale: true, turn: 'BA' })).toEqual([]);
    expect(ids({ condition: 'blocked' })).toEqual([]);
    expect(ids({ scope: 'ORD' })).toEqual([]);
    expect(ids({})).toHaveLength(3);
  });

  it('orders blocked first, then the longest idle, or by identifier', () => {
    const blocked = { ...byId('REF:FEAT-003'), condition: 'blocked' as const };
    const order = (by: 'rank' | 'id' | 'updated') => sortCards([byId('REF:FEAT-001'), byId('REF:FEAT-002'), blocked], by).map((c) => c.feature.id);
    expect(order('rank')).toEqual(['REF:FEAT-003', 'REF:FEAT-002', 'REF:FEAT-001']);
    expect(order('updated')).toEqual(['REF:FEAT-002', 'REF:FEAT-001', 'REF:FEAT-003']);
    expect(order('id')).toEqual(['REF:FEAT-001', 'REF:FEAT-002', 'REF:FEAT-003']);
  });

  it('groups cards in swimlanes by project, epic or turn, putting the unplaced group last', () => {
    expect(lanes(cards, 'none')).toHaveLength(1);
    expect(lanes(cards, 'epic', (s) => s).map((l) => [l.title, l.cards.length])).toEqual([['Self-service refunds', 2], ['No epic yet', 1]]);
    expect(lanes(cards, 'turn').map((l) => l.title)).toEqual(['BA', 'PO']);
    const both = buildCards(program, today, true);
    expect(lanes(both, 'project', (s) => `Project ${s}`).map((l) => [l.title, l.cards.length])).toEqual([['Project ORD', 2], ['Project REF', 2]]);
  });

  it('counts a column and the whole board', () => {
    expect(statsOf(cards)).toEqual({ total: 3, blocked: 0, inProgress: 3, complete: 0 });
    const s = summary(cards);
    expect(s.total).toBe(3);
    expect(s.waiting).toEqual([['PO', 2], ['BA', 1]]);
    expect(s.stale).toBe(1);
    expect(summary([{ ...byId('REF:FEAT-001'), column: 'inactive' }]).total).toBe(0);
  });
});
