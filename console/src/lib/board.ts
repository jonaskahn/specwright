// The board: features as cards, one column per station. Pure functions, so the rules (which
// column a feature is in, what is stale, how cards are grouped and ordered) are tested without a page.

import type { FeaturesRow, TasksRow } from '../../contract/types';
import type { Loaded } from './data/loader';
import { daysSince } from './format';

export type ColumnId = 'shape' | 'spec' | 'review' | 'plan' | 'dev' | 'publish' | 'inactive' | 'other';

export interface Column {
  id: ColumnId;
  title: string;
  /** The skill that moves a feature out of this column, or null when the kit has nothing further to do. */
  skill: string | null;
  hint: string;
}

export const COLUMNS: Column[] = [
  { id: 'shape', title: 'Shape', skill: 'sw-spec', hint: 'Reserved; sw-spec writes the story' },
  { id: 'spec', title: 'Spec', skill: 'sw-review', hint: 'Being written; then sw-review' },
  { id: 'review', title: 'Review', skill: 'sw-review', hint: 'Waiting for accept or sign-off' },
  { id: 'plan', title: 'Plan', skill: 'sw-plan', hint: 'Accepted; sw-plan breaks it into tasks' },
  { id: 'dev', title: 'Ready for dev', skill: null, hint: 'Planned; the team can build' },
  { id: 'publish', title: 'Publish', skill: 'sw-publish', hint: 'Publication requested' },
  { id: 'inactive', title: 'Inactive', skill: null, hint: 'Withdrawn or superseded' },
  { id: 'other', title: 'Not placed', skill: null, hint: 'No station in the data' },
];

export const STALE_DAYS = 14;
export const DANGER_DAYS = 30;

export const LAYER_SHORT: Record<string, string> = { backend: 'BE', frontend: 'FE', mobile: 'MO', devops: 'OPS', data: 'DATA', qa: 'QA', design: 'DS', docs: 'DOC' };

export type Feature = FeaturesRow;
export type Condition = 'blocked' | 'in-progress' | 'complete' | 'other';

export function columnOf(f: Pick<Feature, 'station' | 'condition'>): ColumnId {
  if (f.station === 'plan' && f.condition === 'complete') return 'dev';
  const known = COLUMNS.find((c) => c.id === f.station);
  return known ? known.id : 'other';
}

export function conditionOf(f: Pick<Feature, 'condition'>): Condition {
  return f.condition === 'blocked' || f.condition === 'in-progress' || f.condition === 'complete' ? f.condition : 'other';
}

export interface Card {
  feature: Feature;
  column: ColumnId;
  condition: Condition;
  /** Days since the feature last changed; null when its date is unknown. */
  idle: number | null;
  epics: { key: string; title: string }[];
  layers: [string, number][];
  /** What to type to move it on, e.g. `/sw-review ORD:FEAT-001`; null when nothing is left to run. */
  command: string | null;
}

export function buildCards(d: Loaded, today: Date, qualified: boolean): Card[] {
  const features = d.data.features?.rows ?? [];
  const nodes = new Map((d.data.graph?.nodes ?? []).map((n) => [n.key, n]));
  const epicsOf = new Map<string, { key: string; title: string }[]>();
  for (const e of d.data.graph?.edges ?? []) {
    if (e.rel !== 'member_of' || nodes.get(e.to)?.kind !== 'epic') continue;
    epicsOf.set(e.from, [...(epicsOf.get(e.from) ?? []), { key: e.to, title: nodes.get(e.to)!.title }]);
  }
  const layers = new Map<string, Map<string, number>>();
  for (const t of (d.data.tasks?.rows ?? []) as TasksRow[]) {
    if (t.status !== 'active') continue;
    const mine = layers.get(t.feature) ?? new Map<string, number>();
    mine.set(t.layer ?? 'other', (mine.get(t.layer ?? 'other') ?? 0) + 1);
    layers.set(t.feature, mine);
  }
  return features.map((feature) => {
    const column = columnOf(feature);
    const skill = COLUMNS.find((c) => c.id === column)?.skill ?? null;
    const id = qualified ? feature.id : feature.id.replace(/^[A-Z][A-Z0-9]*:/, '');
    return {
      feature,
      column,
      condition: conditionOf(feature),
      idle: daysSince(feature.updated, today),
      epics: epicsOf.get(feature.id) ?? [],
      layers: [...(layers.get(feature.id) ?? [])].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
      command: skill ? `/${skill} ${id}` : null,
    };
  });
}

export type ConditionFilter = 'all' | Condition;

export interface Filters {
  text: string;
  epic: string;
  condition: ConditionFilter;
  turn: string;
  stale: boolean;
  scope: string;
}

export const NO_FILTERS: Filters = { text: '', epic: '', condition: 'all', turn: '', stale: false, scope: '' };

export function applyFilters(cards: Card[], f: Filters): Card[] {
  const needle = f.text.trim().toLowerCase();
  return cards.filter((c) => {
    if (f.condition !== 'all' && c.condition !== f.condition) return false;
    if (f.turn && (c.feature.turn ?? '') !== f.turn) return false;
    if (f.scope && c.feature.scope !== f.scope) return false;
    if (f.epic && !c.epics.some((e) => e.key === f.epic)) return false;
    if (f.stale && !(c.idle !== null && c.idle > STALE_DAYS)) return false;
    if (!needle) return true;
    return `${c.feature.id} ${c.feature.title} ${c.epics.map((e) => e.title).join(' ')}`.toLowerCase().includes(needle);
  });
}

export type Order = 'rank' | 'id' | 'updated';

/** Blocked first, then the longest idle, then by identifier. */
export function sortCards(cards: Card[], by: Order): Card[] {
  const id = (a: Card, b: Card) => a.feature.id.localeCompare(b.feature.id, undefined, { numeric: true });
  const sorted = [...cards];
  if (by === 'id') return sorted.sort(id);
  if (by === 'updated') return sorted.sort((a, b) => (b.idle ?? -1) - (a.idle ?? -1) || id(a, b));
  return sorted.sort((a, b) => Number(b.condition === 'blocked') - Number(a.condition === 'blocked') || (b.idle ?? -1) - (a.idle ?? -1) || id(a, b));
}

export type Lane = 'none' | 'project' | 'epic' | 'turn';

export interface Swimlane {
  key: string;
  title: string;
  cards: Card[];
}

export function lanes(cards: Card[], by: Lane, names: (scope: string) => string = (s) => s): Swimlane[] {
  if (by === 'none') return [{ key: '', title: '', cards }];
  const groups = new Map<string, Swimlane>();
  for (const card of cards) {
    const [key, title] =
      by === 'project' ? [card.feature.scope, names(card.feature.scope)] : by === 'epic' ? [card.epics[0]?.key ?? '~', card.epics[0]?.title ?? 'No epic yet'] : [card.feature.turn ?? '~', card.feature.turn ?? 'No one yet'];
    if (!groups.has(key)) groups.set(key, { key, title, cards: [] });
    groups.get(key)!.cards.push(card);
  }
  // Named groups in name order, the "none yet" group last.
  return [...groups.values()].sort((a, b) => Number(a.key === '~') - Number(b.key === '~') || a.title.localeCompare(b.title));
}

export interface ColumnStats {
  total: number;
  blocked: number;
  inProgress: number;
  complete: number;
}

export function statsOf(cards: Card[]): ColumnStats {
  return {
    total: cards.length,
    blocked: cards.filter((c) => c.condition === 'blocked').length,
    inProgress: cards.filter((c) => c.condition === 'in-progress').length,
    complete: cards.filter((c) => c.condition === 'complete').length,
  };
}

export interface Summary {
  total: number;
  blocked: number;
  waiting: [turn: string, count: number][];
  stale: number;
}

export function summary(cards: Card[]): Summary {
  const live = cards.filter((c) => c.column !== 'inactive');
  const turns = new Map<string, number>();
  for (const c of live) if (c.feature.turn) turns.set(c.feature.turn, (turns.get(c.feature.turn) ?? 0) + 1);
  return {
    total: live.length,
    blocked: live.filter((c) => c.condition === 'blocked').length,
    waiting: [...turns].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
    stale: live.filter((c) => c.idle !== null && c.idle > STALE_DAYS).length,
  };
}

export const idleTone = (idle: number | null): 'ok' | 'warn' | 'danger' => (idle !== null && idle > DANGER_DAYS ? 'danger' : idle !== null && idle > STALE_DAYS ? 'warn' : 'ok');

export function layerSplit(layers: [string, number][]): string {
  return layers.map(([name, n]) => `${LAYER_SHORT[name] ?? name} ${n}`).join(' · ');
}
