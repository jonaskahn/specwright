import { describe, expect, it } from 'vitest';
import { buildLanes, closedQuery, columnCounts, countsOf, criterionState, needsAttention, percentDone, filterLanes, LOOSE, NO_FILTERS, orderStories, parseClosed, PROGRESS_COLUMNS, storyProgress, tasksByColumn, UNPLACED } from '../src/lib/board';
import { loadAll, type Loaded } from '../src/lib/data/loader';
import { serve } from './golden';

describe('the board lanes', async () => {
  const trace = await loadAll('./data/', serve('trace'));
  const flat = await loadAll('./data/', serve('flat'));
  const program = await loadAll('./data/', serve('program'));
  const lanes = buildLanes(trace, '*');
  const story = (id: string) => lanes.flatMap((l) => l.stories).find((s) => s.id === id)!;
  const patch = (d: Loaded, kind: 'tasks' | 'features', fn: (rows: any[]) => any[]): Loaded => ({ ...d, data: { ...d.data, [kind]: { ...d.data[kind]!, rows: fn(d.data[kind]!.rows) } } });

  it('draws one lane per epic that holds a story, and the stories in no epic last', () => {
    expect(lanes.map((l) => l.key)).toEqual(['REF:EPIC-001', LOOSE]);
    expect(lanes[0].title).toBe('Self-service refunds');
    expect(lanes[0].stories.map((s) => s.id)).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
    expect(lanes[1].title).toBe('Stories in no epic yet');
    expect(lanes[1].stories.map((s) => s.id)).toEqual(['REF:FEAT-003']);
  });

  it('draws no lane for an epic with no story', () => {
    expect(lanes.some((l) => l.key === 'REF:EPIC-002')).toBe(false);
  });

  it('lists a story\'s criteria and tasks in order, with the progress each plan records', () => {
    const s = story('REF:FEAT-001');
    expect(s.criteria.map((c) => c.key)).toEqual(['REF:AC-001-1', 'REF:AC-001-2']);
    expect(s.criteria.every((c) => c.covered)).toBe(true);
    expect(s.tasks.map((t) => [t.id, t.progress])).toEqual([['REF:TASK-001-1', 'planned'], ['REF:TASK-001-2', 'in-progress'], ['REF:TASK-001-3', 'blocked']]);
    expect(s.tasks[0].title).toBe('Record an eligible request');
    expect(s.tasks[0].layer).toBe('backend');
    expect(story('REF:FEAT-002').tasks[0]).toMatchObject({ progress: 'done', evidence: 'make test -> 42 passed, exit 0' });
    expect(story('REF:FEAT-003').tasks[0].progress).toBe('not-started');
  });

  it('shows a criterion no task covers and a task tied to no criterion', () => {
    expect(story('REF:FEAT-003').criteria.filter((c) => !c.covered).map((c) => c.key)).toEqual(['REF:AC-003-2']);
    expect(story('REF:FEAT-001').tasks.filter((t) => t.traces.length === 0).map((t) => t.id)).toEqual(['REF:TASK-001-3']);
    expect(story('REF:FEAT-001').tasks[1].traces).toEqual(['REF:AC-001-1', 'REF:AC-001-2']);
  });

  it('counts a lane', () => {
    expect(lanes[0].counts).toEqual({ stories: 2, tasks: 4, done: 1, blocked: 1, retired: 0 });
    expect(storyProgress(story('REF:FEAT-001'))).toEqual({ done: 0, total: 3, blocked: 1 });
  });

  it('flags what needs a person on each story, blocked task included', () => {
    expect(story('REF:FEAT-001').attention).toBe('question');
    expect(story('REF:FEAT-002').attention).toBe('lint');
    expect(story('REF:FEAT-003').attention).toBeNull();
    const only = patch(trace, 'features', (r) => r.map((f) => ({ ...f, openQuestions: [], openChanges: [], lint: 'review: pass' })));
    expect(buildLanes(only, '*')[0].stories[0].attention).toBe('task');
  });

  it('puts every story of a project with no epic in one lane, with no status when no plan exists', () => {
    const l = buildLanes(flat, '*');
    expect(l.map((x) => [x.key, x.title, x.stories.length])).toEqual([[LOOSE, 'No epic yet', 2]]);
    expect(l[0].stories.every((s) => s.tasks.length === 0)).toBe(true);
  });

  it('lists a task the graph knows but tasks.json does not, with no progress', () => {
    const noRows = patch(trace, 'tasks', (r) => r.filter((t) => t.id !== 'REF:TASK-001-1'));
    const t = buildLanes(noRows, '*')[0].stories[0].tasks.find((x) => x.id === 'REF:TASK-001-1')!;
    expect(t.progress).toBeNull();
    expect(t.title).toBe('[backend] Record an eligible request'.replace(/^\[backend\]\s*/, ''));
  });

  it('leaves out a withdrawn task and hides a retired story until asked', () => {
    const gone = patch(trace, 'tasks', (r) => r.map((t) => (t.id === 'REF:TASK-001-1' ? { ...t, status: 'withdrawn' } : t)));
    expect(buildLanes(gone, '*')[0].stories[0].tasks.map((t) => t.id)).toEqual(['REF:TASK-001-2', 'REF:TASK-001-3']);
    const retired = buildLanes(patch(trace, 'features', (r) => r.map((f) => (f.id === 'REF:FEAT-003' ? { ...f, state: 'withdrawn' } : f))), '*');
    const hidden = filterLanes(retired, NO_FILTERS);
    expect(hidden.map((l) => [l.key, l.stories.length])).toEqual([['REF:EPIC-001', 2], [LOOSE, 0]]);
    expect(hidden[1].counts.retired).toBe(1);
    expect(filterLanes(retired, { ...NO_FILTERS, retired: true }).map((l) => l.key)).toEqual(['REF:EPIC-001', LOOSE]);
    expect(retired[1].counts.retired).toBe(1);
  });

  it('keeps a task that names no known story in a lane of its own', () => {
    const stray = buildLanes(patch(trace, 'tasks', (r) => r.map((t) => (t.id === 'REF:TASK-003-1' ? { ...t, feature: 'REF:FEAT-099' } : t))), '*');
    expect(stray.at(-1)!.key).toBe(UNPLACED);
    expect(stray.at(-1)!.stories[0].tasks.map((t) => t.id)).toEqual(['REF:TASK-003-1']);
  });

  it('puts a story of another project in the epic that holds it, once', () => {
    const l = buildLanes(program, '*');
    expect(l.filter((x) => x.key === 'REF:EPIC-001')).toHaveLength(1);
    expect(l.find((x) => x.key === 'REF:EPIC-001')!.stories.map((s) => s.id)).toEqual(['ORD:FEAT-001', 'REF:FEAT-001']);
    const ord = buildLanes(program, 'ORD');
    expect(ord.find((x) => x.key === 'REF:EPIC-001')).toMatchObject({ foreign: true });
    expect(ord.find((x) => x.key === 'REF:EPIC-001')!.stories.map((s) => s.id)).toEqual(['ORD:FEAT-001']);
  });

  it('filters by text and epic, and drops a lane left with nothing', () => {
    expect(filterLanes(lanes, { ...NO_FILTERS, text: 'duplicate' }).map((l) => l.stories.map((s) => s.id))).toEqual([['REF:FEAT-001']]);
    expect(filterLanes(lanes, { ...NO_FILTERS, text: 'self-service' })[0].stories).toHaveLength(2);
    expect(filterLanes(lanes, { ...NO_FILTERS, epic: LOOSE }).map((l) => l.key)).toEqual([LOOSE]);
    expect(filterLanes(lanes, { ...NO_FILTERS, text: 'zzz' })).toEqual([]);
  });

  it('orders stories by identifier, or blocked and waiting first', () => {
    const list = lanes[0].stories;
    expect(orderStories(list, 'id').map((s) => s.id)).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
    expect(orderStories(list, 'attention').map((s) => s.id)).toEqual(['REF:FEAT-002', 'REF:FEAT-001']);
    expect(countsOf([]).stories).toBe(0);
  });

  it('sorts a story\'s tasks into the five status columns', () => {
    const ids = (id: string) => Object.fromEntries(Object.entries(tasksByColumn(story(id))).map(([k, v]) => [k, v.map((t) => t.id)]));
    expect(ids('REF:FEAT-001')).toMatchObject({ planned: ['REF:TASK-001-1'], 'in-progress': ['REF:TASK-001-2'], blocked: ['REF:TASK-001-3'], done: [], 'not-started': [] });
    expect(ids('REF:FEAT-002').done).toEqual(['REF:TASK-002-1']);
    expect(PROGRESS_COLUMNS).toHaveLength(5);
    const bare = { ...story('REF:FEAT-003'), tasks: [{ id: 'T', title: 't', layer: null, progress: null, evidence: null, traces: [] }] };
    expect(tasksByColumn(bare)['not-started'].map((t) => t.id)).toEqual(['T']);
  });

  it('counts a lane\'s tasks per status column', () => {
    expect(columnCounts(lanes[0].stories)).toEqual({ 'not-started': 0, planned: 1, 'in-progress': 1, blocked: 1, done: 1 });
    expect(columnCounts(lanes[1].stories)['not-started']).toBe(1);
    expect(percentDone(1, 4)).toBe(25);
    expect(percentDone(0, 0)).toBe(0);
  });

  it('says whether a criterion has no task, open tasks, or only finished ones', () => {
    expect(criterionState(story('REF:FEAT-003'), 'REF:AC-003-2')).toBe('none');
    expect(criterionState(story('REF:FEAT-001'), 'REF:AC-001-1')).toBe('open');
    expect(criterionState(story('REF:FEAT-002'), 'REF:AC-002-1')).toBe('met');
  });

  it('lists what needs a person once each: blocked work, questions, lint, then gaps', () => {
    const cards = needsAttention(lanes);
    expect(cards.map((c) => c.key)).toEqual(['task:REF:TASK-001-3', 'question:REF:FEAT-001', 'change:REF:FEAT-002', 'lint:REF:FEAT-002', 'gap:REF:AC-003-2']);
    expect(cards[0]).toMatchObject({ tone: 'danger', code: 'TASK-001-3 · Blocked', target: { kind: 'task', key: 'REF:TASK-001-3' } });
    expect(cards.at(-1)!.sentence).toContain('Rejection notice');
  });

  it('keeps collapsed lanes in the address', () => {
    expect(closedQuery(parseClosed('REF:EPIC-002,REF:EPIC-001'))).toBe('REF:EPIC-001,REF:EPIC-002');
    expect(closedQuery(new Set())).toBeNull();
    expect(parseClosed(null).size).toBe(0);
  });
});
