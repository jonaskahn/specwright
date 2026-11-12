// The trace map: the work chain laid out left to right, from why to how.
//
//   Business objective > Epic > Feature > Acceptance criterion > Task > Code file
//
// Only links the data already holds are drawn. Where a link is missing, a hollow placeholder says
// so and names the skill that fills it. Everything here is pure and deterministic.

import type { GraphEdge, GraphNode } from '../../../contract/types';
import { relationWords } from '../vocabulary';

export const LEVEL_KINDS: Record<string, number> = { bo: 0, epic: 1, feat: 2, ac: 3, task: 4, code: 5 };
export const LEVEL_NAMES = ['bo', 'epic', 'feat', 'ac', 'task', 'code'];
/** Links that make up the chain. Each is drawn from the lower level to the higher one. */
export const CHAIN_RELS = new Set(['realizes', 'member_of', 'has_ac', 'implements', 'touches']);
const RETIRED = new Set(['withdrawn', 'superseded']);

export type GapKind = 'epic' | 'bo' | 'epic-bo' | 'ac' | 'task' | 'task-criterion';

const GAP_WORDS: Record<GapKind, { title: string; next: string; level: number; kind: string }> = {
  epic: { title: 'No epic yet', next: 'sw-shape', level: 1, kind: 'epic' },
  bo: { title: 'No business objective', next: 'sw-shape', level: 0, kind: 'bo' },
  'epic-bo': { title: 'No business objective', next: 'sw-shape', level: 0, kind: 'bo' },
  ac: { title: 'No acceptance criterion', next: 'sw-spec', level: 3, kind: 'ac' },
  task: { title: 'No task covers this criterion', next: 'sw-plan', level: 4, kind: 'task' },
  'task-criterion': { title: 'Not tied to an acceptance criterion', next: 'sw-plan', level: 3, kind: 'ac' },
};

export interface TraceNode {
  id: string;
  /** The graph key, or null for a placeholder. */
  key: string | null;
  gap: GapKind | null;
  kind: string;
  title: string;
  status: string | null;
  /** A published Jira issue key shown on the card (from the registry), never as a node of its own. */
  jira: string | null;
  /** The project the item belongs to, shown on a card when a map holds more than one. */
  scope: string | null;
  /** Set when the item belongs to another project than the one the map is about. */
  foreign: boolean;
  next: string | null;
  level: number;
  x: number;
  y: number;
  /** The feature an acceptance criterion, task or placeholder below a feature belongs to. */
  owner: string | null;
  /** On a feature: what it holds below it, whether drawn or folded away. */
  below: Below | null;
  /** On a feature: its criteria and tasks are drawn. */
  open: boolean;
}

/** What sits under one feature, counted from the whole chain so a folded card still tells the truth. */
export interface Below {
  ac: number;
  task: number;
  /** Criteria no task covers, tasks no criterion owns, and a feature with no criterion at all. */
  open: number;
}

export interface TraceLink {
  id: string;
  left: string;
  right: string;
  rel: string;
  cls: string;
  gap: boolean;
  /** True when the stored link points from the right-hand item to the left-hand one. */
  reversed: boolean;
  /** A feature's own link to an objective that its epic already serves: kept for the chain, not drawn. */
  implied: boolean;
  sentence: string;
}

export interface BrokenReference {
  from: string;
  target: string;
  rel: string;
  sentence: string;
}

export interface TraceModel {
  nodes: TraceNode[];
  links: TraceLink[];
  broken: BrokenReference[];
  /** The levels that hold at least one item, in order. */
  levels: number[];
  width: number;
  height: number;
  notes: string[];
  /** Criteria and tasks left out because their feature is folded. */
  hidden: number;
  /** Criteria and tasks are drawn beside their own feature, not packed from the top of the column. */
  anchored: boolean;
}

export const BOX = { w: 200, h: 64, gapX: 78, gapY: 14, top: 34, pad: 16 };

const byId = (a: { id: string }, b: { id: string }) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
const retired = (n: GraphNode | undefined) => !!n && RETIRED.has(n.status ?? '');

interface Parts {
  chain: Map<string, GraphNode>;
  edges: GraphEdge[];
}

export interface TraceOptions {
  /** Placeholders for missing links. On unless false. */
  gaps?: boolean;
  /** Add the column of code files that tasks say they change. Off by default: most projects name none. */
  code?: boolean;
  /** Published Jira issue keys by item key, read from the identifier registry (the only place they live). */
  jira?: Map<string, string>;
  /** Items that belong to other projects than the one drawn; they are shown but never asked for missing links. */
  foreign?: Set<string>;
  /**
   * Which features show their criteria and tasks. A set of feature keys folds every other feature to
   * one card with counts, which keeps a map of thousands of criteria readable; the default, 'all',
   * draws everything.
   */
  expand?: Set<string> | 'all';
}

function parts(nodes: GraphNode[], edges: GraphEdge[], code = false): Parts {
  const chain = new Map<string, GraphNode>();
  for (const n of nodes) if (n.kind in LEVEL_KINDS && (code || n.kind !== 'code')) chain.set(n.key, n);
  const kept = edges.filter((e) => CHAIN_RELS.has(e.rel) && chain.has(e.from) && chain.has(e.to));
  return { chain, edges: kept };
}

function level(kind: string): number {
  return LEVEL_KINDS[kind] ?? 0;
}

function node(n: GraphNode, jira: string | null, foreign: boolean): TraceNode {
  return { id: n.key, key: n.key, gap: null, kind: n.kind, title: n.title || n.key, status: n.status, jira, scope: n.scope, foreign, next: null, level: level(n.kind), x: 0, y: 0, owner: null, below: null, open: false };
}

function gapNode(kind: GapKind, owner: string): TraceNode {
  const words = GAP_WORDS[kind];
  return { id: `gap:${kind}:${owner}`, key: null, gap: kind, kind: words.kind, title: words.title, status: null, jira: null, scope: null, foreign: false, next: words.next, level: words.level, x: 0, y: 0, owner: null, below: null, open: false };
}

/** The feature each criterion and task belongs to, and each feature to itself. */
export function featureOwners(nodes: GraphNode[], edges: GraphEdge[]): Map<string, string> {
  const kind = new Map(nodes.map((n) => [n.key, n.kind]));
  const owner = new Map<string, string>();
  for (const n of nodes) if (n.kind === 'feat') owner.set(n.key, n.key);
  for (const e of edges) if (e.rel === 'has_ac' && kind.get(e.from) === 'feat') owner.set(e.to, e.from);
  for (const e of edges) if (e.rel === 'has_task' && kind.get(e.from) === 'feat') owner.set(e.to, e.from);
  for (const e of edges) if (e.rel === 'implements' && !owner.has(e.from) && owner.has(e.to)) owner.set(e.from, owner.get(e.to)!);
  for (const e of edges) if (e.rel === 'touches' && !owner.has(e.to) && owner.has(e.from)) owner.set(e.to, owner.get(e.from)!);
  return owner;
}

export interface Coverage {
  id: string;
  label: string;
  have: number;
  total: number;
  /** Keys of the items that miss the link, so a click can point at them. */
  gaps: string[];
}

/** How completely the chain is linked. A measure is omitted when the level it needs does not exist yet. */
export function traceCoverage(nodes: GraphNode[], edges: GraphEdge[], foreign: Set<string> = new Set()): Coverage[] {
  const { chain, edges: links } = parts(nodes, edges);
  const live = (kind: string) => [...chain.values()].filter((n) => n.kind === kind && !retired(n) && !foreign.has(n.key));
  const features = live('feat');
  const criteria = live('ac');
  const tasks = live('task');
  const out = (rel: string, side: 'from' | 'to') => new Set(links.filter((e) => e.rel === rel).map((e) => (side === 'from' ? e.from : e.to)));
  const measures: Coverage[] = [];
  const add = (id: string, label: string, items: GraphNode[], linked: Set<string>) => {
    const gaps = items.filter((n) => !linked.has(n.key)).map((n) => n.key);
    measures.push({ id, label, have: items.length - gaps.length, total: items.length, gaps });
  };
  const some = (kind: string) => [...chain.values()].some((n) => n.kind === kind && !retired(n));
  if (some('epic') && features.length) add('epic', 'Features in an epic', features, out('member_of', 'from'));
  const served = out('realizes', 'from');
  const viaEpic = new Set(links.filter((e) => e.rel === 'member_of' && served.has(e.to)).map((e) => e.from));
  const serving = new Set([...served, ...viaEpic]);
  if (some('bo') && features.length) add('bo', 'Features serving a business objective', features, serving);
  if (some('bo') && live('epic').length) add('epic-bo', 'Epics serving a business objective', live('epic'), served);
  if (features.length) add('ac', 'Features with an acceptance criterion', features, out('has_ac', 'from'));
  if (tasks.length && criteria.length) add('covered', 'Acceptance criteria covered by a task', criteria, out('implements', 'to'));
  if (tasks.length) add('tied', 'Tasks tied to an acceptance criterion', tasks, out('implements', 'from'));
  return measures;
}

export function buildTrace(nodes: GraphNode[], edges: GraphEdge[], opts: TraceOptions = {}): TraceModel {
  const { chain, edges: chainEdges } = parts(nodes, edges, opts.code);
  const model: TraceModel = { nodes: [], links: [], broken: [], levels: [], width: 0, height: 0, notes: [], hidden: 0, anchored: false };
  const present = new Map<string, TraceNode>();
  for (const n of [...chain.values()].sort((a, b) => (a.key < b.key ? -1 : 1))) present.set(n.key, node(n, opts.jira?.get(n.key) ?? null, opts.foreign?.has(n.key) ?? false));

  const title = (key: string) => present.get(key)?.title ?? key;
  for (const e of chainEdges) {
    const a = chain.get(e.from)!;
    const b = chain.get(e.to)!;
    if (level(a.kind) === level(b.kind)) continue;
    const reversed = level(a.kind) > level(b.kind);
    model.links.push({
      id: `${e.from}|${e.rel}|${e.to}`,
      left: reversed ? e.to : e.from,
      right: reversed ? e.from : e.to,
      rel: e.rel,
      cls: e.class,
      gap: false,
      reversed,
      implied: false,
      sentence: `${title(e.from)} ${relationWords(e.rel, 'out')} ${title(e.to)}`,
    });
  }
  markImplied(model.links);

  if (opts.gaps !== false) {
    const hasEpics = [...chain.values()].some((n) => n.kind === 'epic');
    const hasObjectives = [...chain.values()].some((n) => n.kind === 'bo');
    const hasTasks = [...chain.values()].some((n) => n.kind === 'task');
    const origin = (l: TraceLink) => (l.reversed ? l.right : l.left);
    const target = (l: TraceLink) => (l.reversed ? l.left : l.right);
    const linked = (rel: string, side: 'from' | 'to') => new Set(model.links.filter((l) => l.rel === rel).map(side === 'from' ? origin : target));
    const inEpic = linked('member_of', 'from');
    const serving = linked('realizes', 'from');
    const epicOf = new Map(model.links.filter((l) => l.rel === 'member_of').map((l) => [origin(l), target(l)]));
    const viaEpic = (key: string) => serving.has(epicOf.get(key) ?? '');
    const withCriterion = linked('has_ac', 'from');
    const covered = linked('implements', 'to');
    const tied = linked('implements', 'from');
    const add = (kind: GapKind, owner: string, side: 'left' | 'right', other: string, rel: string) => {
      const g = gapNode(kind, owner);
      if (!present.has(g.id)) present.set(g.id, g);
      model.links.push({
        id: `${g.id}|${other}`,
        left: side === 'left' ? g.id : other,
        right: side === 'left' ? other : g.id,
        rel,
        cls: 'gap',
        gap: true,
        reversed: false,
        implied: false,
        sentence: `${title(owner)}: ${g.title.toLowerCase()}`,
      });
      return g;
    };
    for (const n of chain.values()) {
      if (retired(n) || opts.foreign?.has(n.key)) continue;
      if (n.kind === 'feat') {
        if (hasEpics && !inEpic.has(n.key)) add('epic', n.key, 'left', n.key, 'member_of');
        if (hasObjectives && !serving.has(n.key) && !viaEpic(n.key)) add('bo', n.key, 'left', n.key, 'realizes');
        if (!withCriterion.has(n.key)) add('ac', n.key, 'right', n.key, 'has_ac');
      } else if (n.kind === 'epic') {
        if (hasObjectives && !serving.has(n.key)) add('epic-bo', n.key, 'left', n.key, 'realizes');
      } else if (n.kind === 'ac' && hasTasks && !covered.has(n.key)) {
        add('task', n.key, 'right', n.key, 'implements');
      } else if (n.kind === 'task' && !tied.has(n.key)) {
        const parent = edges.find((e) => e.rel === 'has_task' && e.to === n.key && chain.has(e.from))?.from;
        const g = add('task-criterion', n.key, 'left', n.key, 'implements');
        if (parent) {
          model.links.push({
            id: `${parent}|has_task|${n.key}|gap`,
            left: parent,
            right: g.id,
            rel: 'has_task',
            cls: 'gap',
            gap: true,
            reversed: false,
            implied: false,
            sentence: `${title(parent)} has task ${n.title}`,
          });
        }
      }
    }
    if (!hasEpics && [...chain.values()].some((n) => n.kind === 'feat')) model.notes.push('No epic is defined, so features are shown without one.');
    if (!hasTasks && [...chain.values()].some((n) => n.kind === 'ac')) model.notes.push('No task is planned yet, so criteria are shown without tasks.');
  }

  const idOf = new Set(nodes.map((n) => n.key));
  for (const e of edges) {
    if (e.resolution !== 'unresolved' || !idOf.has(e.from)) continue;
    const from = nodes.find((n) => n.key === e.from);
    const target = e.to.replace(/^[A-Z][A-Z0-9]*:/, '');
    model.broken.push({ from: e.from, target, rel: e.rel, sentence: `${from?.title ?? e.from} ${relationWords(e.rel, 'out')} ${target}, which is not defined anywhere` });
  }
  model.broken.sort((a, b) => (a.from + a.target < b.from + b.target ? -1 : 1));

  fold(model, present, chain, edges, opts.expand ?? 'all');
  model.nodes = [...present.values()].sort(byId);
  place(model);
  return model;
}

/**
 * Count what sits under each feature, then drop the criteria, tasks and placeholders of every
 * feature that is not open. Items that belong to no feature stay, so nothing becomes unreachable.
 */
function fold(model: TraceModel, present: Map<string, TraceNode>, chain: Map<string, GraphNode>, edges: GraphEdge[], expand: Set<string> | 'all'): void {
  const owners = featureOwners([...chain.values()], edges);
  const originOf = (l: TraceLink) => (l.reversed ? l.right : l.left);
  const targetOf = (l: TraceLink) => (l.reversed ? l.left : l.right);
  const covered = new Set(model.links.filter((l) => !l.gap && l.rel === 'implements').map(targetOf));
  const tied = new Set(model.links.filter((l) => !l.gap && l.rel === 'implements').map(originOf));
  const hasTasks = [...chain.values()].some((g) => g.kind === 'task');
  const below = new Map<string, Below>();
  const of = (feature: string) => below.get(feature) ?? below.set(feature, { ac: 0, task: 0, open: 0 }).get(feature)!;
  for (const g of chain.values()) {
    if (retired(g) || (g.kind !== 'ac' && g.kind !== 'task')) continue;
    const feature = owners.get(g.key);
    if (!feature) continue;
    const row = of(feature);
    if (g.kind === 'ac') {
      row.ac++;
      if (hasTasks && !covered.has(g.key)) row.open++;
    } else {
      row.task++;
      if (!tied.has(g.key)) row.open++;
    }
  }
  for (const n of present.values()) {
    if (n.gap) n.owner = owners.get(n.id.split(':').slice(2).join(':')) ?? null;
    else if (n.key && n.kind !== 'feat') n.owner = n.level >= 3 ? (owners.get(n.key) ?? null) : null;
    if (n.kind === 'feat' && n.key && !n.gap) {
      const row = of(n.key);
      if (!row.ac && !retired(chain.get(n.key))) row.open++;
      n.below = row;
      n.open = expand === 'all' || expand.has(n.key);
    }
  }
  if (expand === 'all') return;
  const folded = (n: TraceNode) => n.level >= 3 && n.owner !== null && !expand.has(n.owner);
  for (const n of [...present.values()]) {
    if (!folded(n)) continue;
    if (!n.gap) model.hidden++;
    present.delete(n.id);
  }
  model.links = model.links.filter((l) => present.has(l.left) && present.has(l.right));
  model.anchored = true;
}

/** A feature's direct link to an objective is implied when one of its epics already serves it. */
function markImplied(links: TraceLink[]): void {
  const origin = (l: TraceLink) => (l.reversed ? l.right : l.left);
  const target = (l: TraceLink) => (l.reversed ? l.left : l.right);
  const epicsOf = new Map<string, string[]>();
  for (const l of links) if (l.rel === 'member_of') epicsOf.set(origin(l), [...(epicsOf.get(origin(l)) ?? []), target(l)]);
  const serves = new Set(links.filter((l) => l.rel === 'realizes').map((l) => `${origin(l)}|${target(l)}`));
  for (const l of links) {
    if (l.rel !== 'realizes') continue;
    if ((epicsOf.get(origin(l)) ?? []).some((epic) => serves.has(`${epic}|${target(l)}`))) l.implied = true;
  }
}

/** Rows are ordered by the average row of linked neighbours, two sweeps, so lines cross less. */
function place(model: TraceModel): void {
  const levels = [...new Set(model.nodes.map((n) => n.level))].sort((a, b) => a - b);
  model.levels = levels;
  const columns = new Map<number, TraceNode[]>(levels.map((l) => [l, model.nodes.filter((n) => n.level === l)]));
  const row = new Map<string, number>();
  const index = () => columns.forEach((list) => list.forEach((n, i) => row.set(n.id, i)));
  index();
  const neighbours = (n: TraceNode, towards: 'left' | 'right'): number[] =>
    model.links
      .filter((l) => !l.implied && (towards === 'left' ? l.right === n.id : l.left === n.id))
      .map((l) => row.get(towards === 'left' ? l.left : l.right) ?? 0);
  const sweep = (order: number[], towards: 'left' | 'right') => {
    for (const lv of order) {
      const list = columns.get(lv)!;
      const score = new Map(list.map((n) => {
        const near = neighbours(n, towards);
        return [n.id, near.length ? near.reduce((s, v) => s + v, 0) / near.length : row.get(n.id)!] as const;
      }));
      list.sort((a, b) => score.get(a.id)! - score.get(b.id)! || (a.id < b.id ? -1 : 1));
      list.forEach((n, i) => row.set(n.id, i));
    }
  };
  for (let pass = 0; pass < 2; pass++) {
    sweep(levels.slice(1), 'left');
    sweep([...levels].reverse().slice(1), 'right');
  }
  let rows = 0;
  levels.forEach((lv, col) => {
    const list = columns.get(lv)!;
    rows = Math.max(rows, list.length);
    list.forEach((n, i) => {
      n.x = BOX.pad + col * (BOX.w + BOX.gapX);
      n.y = BOX.top + i * (BOX.h + BOX.gapY);
    });
  });
  if (model.anchored) {
    rows = anchor(model, columns, levels);
    model.height = rows + BOX.pad;
  } else model.height = BOX.top + rows * (BOX.h + BOX.gapY) + BOX.pad;
  model.width = BOX.pad * 2 + Math.max(1, levels.length) * BOX.w + Math.max(0, levels.length - 1) * BOX.gapX;
}

/**
 * Put each open feature's criteria and tasks level with it, so a feature far down a long column
 * does not send its lines across the whole map. Groups keep the order of their features and
 * never overlap. Returns the bottom edge of the lowest card.
 */
function anchor(model: TraceModel, columns: Map<number, TraceNode[]>, levels: number[]): number {
  const pitch = BOX.h + BOX.gapY;
  const features = new Map(model.nodes.filter((n) => n.kind === 'feat' && !n.gap).map((n) => [n.id, n]));
  let bottom = BOX.top;
  for (const lv of levels) {
    const list = columns.get(lv)!;
    if (lv >= 3) {
      const groups = new Map<string, TraceNode[]>();
      const loose: TraceNode[] = [];
      for (const n of list) (n.owner && features.has(n.owner) ? (groups.get(n.owner) ?? groups.set(n.owner, []).get(n.owner)!) : loose).push(n);
      let cursor = BOX.top;
      for (const owner of [...groups.keys()].sort((a, b) => features.get(a)!.y - features.get(b)!.y)) {
        const group = groups.get(owner)!;
        const start = Math.max(cursor, features.get(owner)!.y - ((group.length - 1) * pitch) / 2);
        group.forEach((n, i) => (n.y = start + i * pitch));
        cursor = start + group.length * pitch;
      }
      for (const n of loose) {
        n.y = cursor;
        cursor += pitch;
      }
    }
    for (const n of list) bottom = Math.max(bottom, n.y + BOX.h);
  }
  return bottom;
}

/** Every item above and below `id` along the chain, including itself, and the links between them. */
export function chainOf(model: TraceModel, id: string): { nodes: Set<string>; links: Set<string> } {
  const nodes = new Set([id]);
  const links = new Set<string>();
  for (const direction of ['left', 'right'] as const) {
    const queue = [id];
    while (queue.length) {
      const at = queue.pop()!;
      for (const l of model.links) {
        const here = direction === 'left' ? l.right : l.left;
        const next = direction === 'left' ? l.left : l.right;
        if (here !== at) continue;
        links.add(l.id);
        if (!nodes.has(next)) {
          nodes.add(next);
          queue.push(next);
        }
      }
    }
  }
  return { nodes, links };
}

/** Keep only the chain around one item and everything below its features. For maps too large to read whole. */
export function focusModel(nodes: GraphNode[], edges: GraphEdge[], key: string, opts: TraceOptions = {}): TraceModel {
  const full = buildTrace(nodes, edges, opts);
  const keep = chainOf(full, key).nodes;
  for (const f of full.nodes.filter((n) => keep.has(n.id) && n.kind === 'feat')) {
    for (const id of chainOf(full, f.id).nodes) keep.add(id);
  }
  const slim: TraceModel = {
    ...full,
    nodes: full.nodes.filter((n) => keep.has(n.id)),
    links: full.links.filter((l) => keep.has(l.left) && keep.has(l.right)),
  };
  place(slim);
  return slim;
}
