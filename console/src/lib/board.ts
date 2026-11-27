// The board: one lane per epic, and in each lane one row per story with its acceptance criteria and
// its tasks. Pure functions over the loaded data, so the rules (which lane a story is in, which
// criterion has no task, which task is tied to nothing) are tested without a page.
//
// Nothing here is implemented or advanced by the console. A task shows the progress its plan file
// records (`tasks.json`); a task the graph knows but `tasks.json` does not carries no progress.

import type { FeaturesRow, TasksRow } from '../../contract/types';
import type { Loaded } from './data/loader';
import { inScope, rows } from './data/selectors';
import { plural, shortKey } from './format';
import { label } from './status';

export type Progress = TasksRow['progress'];

/** Key of the lane for stories in no epic, and of the lane for tasks that name no known story. */
export const LOOSE = '~';
export const UNPLACED = '~none';

export interface LaneTask {
  id: string;
  title: string;
  layer: string | null;
  /** The recorded progress, or null when the graph knows the task but `tasks.json` does not. */
  progress: Progress | null;
  evidence: string | null;
  /** Keys of the story's criteria this task implements. Empty means it is tied to none. */
  traces: string[];
}

export interface LaneCriterion {
  key: string;
  title: string;
  /** Some task implements it. */
  covered: boolean;
}

export type Attention = 'blocked' | 'lint' | 'question' | 'change' | 'task';

export interface LaneStory {
  /** Null when only a task names this story and `features.json` does not list it. */
  feature: FeaturesRow | null;
  id: string;
  title: string;
  scope: string;
  criteria: LaneCriterion[];
  tasks: LaneTask[];
  retired: boolean;
  /** The first reason a person is needed, or null. */
  attention: Attention | null;
}

export interface LaneCounts {
  stories: number;
  tasks: number;
  done: number;
  blocked: number;
  retired: number;
}

export interface Lane {
  key: string;
  title: string;
  /** The project the epic belongs to; null for the two synthetic lanes. */
  scope: string | null;
  /** An epic of another project than the one in view, drawn because one of its stories is. */
  foreign: boolean;
  stories: LaneStory[];
  counts: LaneCounts;
}

export interface LaneFilters {
  text: string;
  /** A lane key; empty for every lane. */
  epic: string;
  /** Show retired stories (superseded or withdrawn). */
  retired: boolean;
}

export const NO_FILTERS: LaneFilters = { text: '', epic: '', retired: false };
export type StoryOrder = 'id' | 'attention';

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });
export const compareKeys = (a: string, b: string): number => collator.compare(a, b);

const RETIRED = new Set(['superseded', 'withdrawn']);
const stripLayer = (title: string) => title.replace(/^\[[A-Za-z-]+\]\s*/, '');

function attentionOf(feature: FeaturesRow | null, tasks: LaneTask[]): Attention | null {
  if (feature) {
    if (feature.condition === 'blocked') return 'blocked';
    if (/fail/i.test(feature.lint ?? '')) return 'lint';
    if (feature.openQuestions.length) return 'question';
    if (feature.openChanges.length) return 'change';
  }
  return tasks.some((t) => t.progress === 'blocked') ? 'task' : null;
}

export function countsOf(stories: LaneStory[], retired = stories.filter((s) => s.retired).length): LaneCounts {
  const tasks = stories.flatMap((s) => s.tasks);
  return {
    stories: stories.length,
    tasks: tasks.length,
    done: tasks.filter((t) => t.progress === 'done').length,
    blocked: tasks.filter((t) => t.progress === 'blocked').length,
    retired,
  };
}

export function buildLanes(d: Loaded, scope: string): Lane[] {
  const nodes = new Map((d.data.graph?.nodes ?? []).map((n) => [n.key, n]));
  const edges = d.data.graph?.edges ?? [];
  const features = inScope(rows.features(d), scope);
  const taskRows = inScope(rows.tasks(d), scope).filter((t) => t.status === 'active');
  const rowOf = new Map(taskRows.map((t) => [t.id, t]));
  const withdrawn = new Set(rows.tasks(d).filter((t) => t.status === 'withdrawn').map((t) => t.id));

  const criteriaOf = new Map<string, string[]>();
  const taskKeysOf = new Map<string, string[]>();
  const implemented = new Map<string, string[]>();
  const epicsOf = new Map<string, string[]>();
  for (const e of edges) {
    if (e.rel === 'has_ac') criteriaOf.set(e.from, [...(criteriaOf.get(e.from) ?? []), e.to]);
    else if (e.rel === 'has_task') taskKeysOf.set(e.from, [...(taskKeysOf.get(e.from) ?? []), e.to]);
    else if (e.rel === 'implements') implemented.set(e.from, [...(implemented.get(e.from) ?? []), e.to]);
    else if (e.rel === 'member_of' && e.resolution === 'resolved' && nodes.get(e.to)?.kind === 'epic' && nodes.get(e.from)?.kind === 'feat') {
      epicsOf.set(e.from, [...(epicsOf.get(e.from) ?? []), e.to]);
    }
  }

  const taskOf = (key: string, own: Set<string>): LaneTask => {
    const row = rowOf.get(key);
    const node = nodes.get(key);
    const traces = (row ? row.traces : (implemented.get(key) ?? [])).filter((t) => own.has(t));
    return {
      id: key,
      title: stripLayer(row?.title ?? node?.title ?? key),
      layer: row?.layer ?? null,
      progress: row ? row.progress : null,
      evidence: row?.evidence ?? null,
      traces: [...traces].sort(compareKeys),
    };
  };

  const storyOf = (feature: FeaturesRow): LaneStory => {
    const own = new Set(criteriaOf.get(feature.id) ?? []);
    const keys = new Set<string>(taskRows.filter((t) => t.feature === feature.id).map((t) => t.id));
    for (const k of taskKeysOf.get(feature.id) ?? []) {
      if (nodes.get(k)?.status !== 'withdrawn' && !withdrawn.has(k)) keys.add(k);
    }
    const tasks = [...keys].sort(compareKeys).map((k) => taskOf(k, own));
    const covered = new Set(tasks.flatMap((t) => t.traces));
    const criteria = [...own]
      .sort(compareKeys)
      .filter((k) => nodes.get(k)?.status !== 'withdrawn')
      .map((key) => ({ key, title: nodes.get(key)?.title ?? key, covered: covered.has(key) }));
    return {
      feature,
      id: feature.id,
      title: feature.title,
      scope: feature.scope,
      criteria,
      tasks,
      retired: RETIRED.has(feature.state),
      attention: attentionOf(feature, tasks),
    };
  };

  const stories = new Map(features.map((f) => [f.id, storyOf(f)]));
  const lanes: Lane[] = [];
  const byEpic = new Map<string, LaneStory[]>();
  const loose: LaneStory[] = [];
  for (const story of [...stories.values()].sort((a, b) => compareKeys(a.id, b.id))) {
    const epics = epicsOf.get(story.id) ?? [];
    if (!epics.length) loose.push(story);
    for (const epic of epics) byEpic.set(epic, [...(byEpic.get(epic) ?? []), story]);
  }
  for (const key of [...byEpic.keys()].sort(compareKeys)) {
    const node = nodes.get(key)!;
    const list = byEpic.get(key)!;
    lanes.push({ key, title: node.title || key, scope: node.scope, foreign: scope !== '*' && !!node.scope && node.scope !== scope, stories: list, counts: countsOf(list) });
  }
  if (loose.length) {
    lanes.push({ key: LOOSE, title: lanes.length ? 'Stories in no epic yet' : 'No epic yet', scope: null, foreign: false, stories: loose, counts: countsOf(loose) });
  }

  const stray = taskRows.filter((t) => !stories.has(t.feature));
  if (stray.length) {
    const story: LaneStory = {
      feature: null,
      id: UNPLACED,
      title: 'Tasks that name no known story',
      scope: stray[0].scope,
      criteria: [],
      tasks: stray.map((t) => taskOf(t.id, new Set())).sort((a, b) => compareKeys(a.id, b.id)),
      retired: false,
      attention: null,
    };
    story.attention = attentionOf(null, story.tasks);
    lanes.push({ key: UNPLACED, title: 'Tasks with no story', scope: null, foreign: false, stories: [story], counts: countsOf([story]) });
  }
  return lanes;
}

const matches = (s: LaneStory, needle: string) =>
  `${s.id} ${s.title} ${s.criteria.map((c) => c.title).join(' ')} ${s.tasks.map((t) => `${t.id} ${t.title}`).join(' ')}`.toLowerCase().includes(needle);

export function filterLanes(lanes: Lane[], f: LaneFilters): Lane[] {
  const needle = f.text.trim().toLowerCase();
  const filtering = !!needle || !!f.epic;
  const out: Lane[] = [];
  for (const lane of lanes) {
    if (f.epic && lane.key !== f.epic) continue;
    const whole = !!needle && lane.title.toLowerCase().includes(needle);
    const visible = lane.stories.filter((s) => (f.retired || !s.retired) && (!needle || whole || matches(s, needle)));
    if (!visible.length && filtering) continue;
    if (!visible.length && !lane.stories.length) continue;
    out.push({ ...lane, stories: visible, counts: countsOf(visible, lane.counts.retired) });
  }
  return out;
}

const RANK: Record<Attention, number> = { blocked: 0, lint: 1, question: 2, change: 3, task: 4 };

export function orderStories(stories: LaneStory[], by: StoryOrder): LaneStory[] {
  const sorted = [...stories];
  if (by === 'id') return sorted.sort((a, b) => compareKeys(a.id, b.id));
  const rank = (s: LaneStory) => (s.attention ? RANK[s.attention] : 9);
  return sorted.sort((a, b) => rank(a) - rank(b) || compareKeys(a.id, b.id));
}

/** Done and total of a story's tasks, and how many are blocked. */
export function storyProgress(story: LaneStory): { done: number; total: number; blocked: number } {
  return {
    done: story.tasks.filter((t) => t.progress === 'done').length,
    total: story.tasks.length,
    blocked: story.tasks.filter((t) => t.progress === 'blocked').length,
  };
}

/** The status columns of a lane, left to right. A task sits in the column its plan records. */
export const PROGRESS_COLUMNS = ['not-started', 'planned', 'in-progress', 'blocked', 'done'] as const;
export type Column = (typeof PROGRESS_COLUMNS)[number];

/** A story's tasks split by column; a task with no recorded status counts as not started. */
export function tasksByColumn(story: LaneStory): Record<Column, LaneTask[]> {
  const out: Record<Column, LaneTask[]> = { 'not-started': [], planned: [], 'in-progress': [], blocked: [], done: [] };
  for (const t of story.tasks) out[t.progress ?? 'not-started'].push(t);
  return out;
}

/** How many tasks of these stories sit in each status column. */
export function columnCounts(stories: LaneStory[]): Record<Column, number> {
  const out: Record<Column, number> = { 'not-started': 0, planned: 0, 'in-progress': 0, blocked: 0, done: 0 };
  for (const s of stories) for (const t of s.tasks) out[t.progress ?? 'not-started'] += 1;
  return out;
}

/** The whole-number percentage of tasks done; zero when there are none. */
export const percentDone = (done: number, total: number): number => (total ? Math.round((done / total) * 100) : 0);

/** What a criterion looks like on its story: no task implements it, some do, or every one that does is done. */
export type CriterionState = 'none' | 'open' | 'met';

export function criterionState(story: LaneStory, key: string): CriterionState {
  const tasks = story.tasks.filter((t) => t.traces.includes(key));
  if (!tasks.length) return 'none';
  return tasks.every((t) => t.progress === 'done') ? 'met' : 'open';
}

export const tasksFor = (story: LaneStory, key: string): number => story.tasks.filter((t) => t.traces.includes(key)).length;

export interface AttentionCard {
  key: string;
  tone: 'danger' | 'warn';
  /** Mono line: identifier and the word that says why. */
  code: string;
  sentence: string;
  /** Where choosing the card goes: a story's page, or a task's preview. */
  target: { kind: 'feature' | 'task'; key: string };
}

/** Everything on the board that waits for a person, each item once, blocked work first. */
export function needsAttention(lanes: Lane[]): AttentionCard[] {
  const seen = new Set<string>();
  const stories = lanes.flatMap((l) => l.stories).filter((s) => !s.retired && s.feature && !seen.has(s.id) && seen.add(s.id));
  const blockedTasks: AttentionCard[] = [];
  const blockedStories: AttentionCard[] = [];
  const questions: AttentionCard[] = [];
  const lint: AttentionCard[] = [];
  const gaps: AttentionCard[] = [];
  for (const s of stories) {
    const f = s.feature!;
    const code = (word: string) => `${shortKey(s.id)} · ${word}`;
    const target = { kind: 'feature' as const, key: s.id };
    for (const t of s.tasks.filter((x) => x.progress === 'blocked')) {
      const untied = !t.traces.length && s.criteria.length > 0;
      blockedTasks.push({
        key: `task:${t.id}`,
        tone: 'danger',
        code: `${shortKey(t.id)} · Blocked`,
        sentence: untied ? `${t.title} is blocked and not tied to an acceptance criterion` : `${t.title} is blocked`,
        target: { kind: 'task', key: t.id },
      });
    }
    if (f.condition === 'blocked') blockedStories.push({ key: `blocked:${s.id}`, tone: 'danger', code: code(label(f.state)), sentence: `${s.title} is blocked`, target });
    if (f.openQuestions.length) questions.push({ key: `question:${s.id}`, tone: 'warn', code: code(label(f.state)), sentence: `${s.title} has ${plural(f.openQuestions.length, 'open question')}`, target });
    if (f.openChanges.length) questions.push({ key: `change:${s.id}`, tone: 'warn', code: code(label(f.state)), sentence: `${s.title} has ${plural(f.openChanges.length, 'open change request')}`, target });
    if (/fail/i.test(f.lint ?? '')) lint.push({ key: `lint:${s.id}`, tone: 'warn', code: code(label(f.state)), sentence: `${s.title} is failing lint`, target });
    if (s.tasks.length) {
      for (const c of s.criteria.filter((x) => !x.covered)) gaps.push({ key: `gap:${c.key}`, tone: 'warn', code: code('Coverage gap'), sentence: `No task covers \u201c${c.title}\u201d`, target });
    }
  }
  return [...blockedTasks, ...blockedStories, ...questions, ...lint, ...gaps];
}

/** Collapsed lanes live in the address as a comma-separated list of lane keys. */
export const parseClosed = (value: string | null): Set<string> => new Set((value ?? '').split(',').filter(Boolean));
export const closedQuery = (closed: Set<string>): string | null => (closed.size ? [...closed].sort(compareKeys).join(',') : null);

export const ATTENTION_WORDS: Record<Attention, string> = {
  blocked: 'Blocked',
  lint: 'Lint failing',
  question: 'Open question',
  change: 'Change request open',
  task: 'A task is blocked',
};
