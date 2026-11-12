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
const CHAIN_RELS = new Set(['realizes', 'member_of', 'has_ac', 'implements', 'touches']);
const RETIRED = new Set(['withdrawn', 'superseded']);

export type GapKind = 'epic' | 'bo' | 'ac' | 'task' | 'task-criterion';

const GAP_WORDS: Record<GapKind, { title: string; next: string; level: number; kind: string }> = {
  epic: { title: 'No epic yet', next: 'sw-shape', level: 1, kind: 'epic' },
  bo: { title: 'No business objective', next: 'sw-shape', level: 0, kind: 'bo' },
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
  next: string | null;
  level: number;
  x: number;
  y: number;
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
}

export const BOX = { w: 200, h: 54, gapX: 78, gapY: 14, top: 34, pad: 16 };

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

function node(n: GraphNode, jira: string | null): TraceNode {
  return { id: n.key, key: n.key, gap: null, kind: n.kind, title: n.title || n.key, status: n.status, jira, next: null, level: level(n.kind), x: 0, y: 0 };
}

function gapNode(kind: GapKind, owner: string): TraceNode {
  const words = GAP_WORDS[kind];
  return { id: `gap:${kind}:${owner}`, key: null, gap: kind, kind: words.kind, title: words.title, status: null, jira: null, next: words.next, level: words.level, x: 0, y: 0 };
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
export function traceCoverage(nodes: GraphNode[], edges: GraphEdge[]): Coverage[] {
  const { chain, edges: links } = parts(nodes, edges);
  const live = (kind: string) => [...chain.values()].filter((n) => n.kind === kind && !retired(n));
  const features = live('feat');
  const criteria = live('ac');
  const tasks = live('task');
  const out = (rel: string, side: 'from' | 'to') => new Set(links.filter((e) => e.rel === rel).map((e) => (side === 'from' ? e.from : e.to)));
  const measures: Coverage[] = [];
  const add = (id: string, label: string, items: GraphNode[], linked: Set<string>) => {
    const gaps = items.filter((n) => !linked.has(n.key)).map((n) => n.key);
    measures.push({ id, label, have: items.length - gaps.length, total: items.length, gaps });
  };
  if (live('epic').length && features.length) add('epic', 'Features in an epic', features, out('member_of', 'from'));
  if (live('bo').length && features.length) add('bo', 'Features serving a business objective', features, out('realizes', 'from'));
  if (features.length) add('ac', 'Features with an acceptance criterion', features, out('has_ac', 'from'));
  if (tasks.length && criteria.length) add('covered', 'Acceptance criteria covered by a task', criteria, out('implements', 'to'));
  if (tasks.length) add('tied', 'Tasks tied to an acceptance criterion', tasks, out('implements', 'from'));
  return measures;
}

export function buildTrace(nodes: GraphNode[], edges: GraphEdge[], opts: TraceOptions = {}): TraceModel {
  const { chain, edges: chainEdges } = parts(nodes, edges, opts.code);
  const model: TraceModel = { nodes: [], links: [], broken: [], levels: [], width: 0, height: 0, notes: [] };
  const present = new Map<string, TraceNode>();
  for (const n of [...chain.values()].sort((a, b) => (a.key < b.key ? -1 : 1))) present.set(n.key, node(n, opts.jira?.get(n.key) ?? null));

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
      sentence: `${title(e.from)} ${relationWords(e.rel, 'out')} ${title(e.to)}`,
    });
  }

  if (opts.gaps !== false) {
    const hasEpics = [...chain.values()].some((n) => n.kind === 'epic');
    const hasObjectives = [...chain.values()].some((n) => n.kind === 'bo');
    const hasTasks = [...chain.values()].some((n) => n.kind === 'task');
    const origin = (l: TraceLink) => (l.reversed ? l.right : l.left);
    const target = (l: TraceLink) => (l.reversed ? l.left : l.right);
    const linked = (rel: string, side: 'from' | 'to') => new Set(model.links.filter((l) => l.rel === rel).map(side === 'from' ? origin : target));
    const inEpic = linked('member_of', 'from');
    const serving = linked('realizes', 'from');
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
        sentence: `${title(owner)}: ${g.title.toLowerCase()}`,
      });
      return g;
    };
    for (const n of chain.values()) {
      if (retired(n)) continue;
      if (n.kind === 'feat') {
        if (hasEpics && !inEpic.has(n.key)) add('epic', n.key, 'left', n.key, 'member_of');
        if (hasObjectives && !serving.has(n.key)) add('bo', n.key, 'left', n.key, 'realizes');
        if (!withCriterion.has(n.key)) add('ac', n.key, 'right', n.key, 'has_ac');
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

  model.nodes = [...present.values()].sort(byId);
  place(model);
  return model;
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
      .filter((l) => (towards === 'left' ? l.right === n.id : l.left === n.id))
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
  model.width = BOX.pad * 2 + Math.max(1, levels.length) * BOX.w + Math.max(0, levels.length - 1) * BOX.gapX;
  model.height = BOX.top + rows * (BOX.h + BOX.gapY) + BOX.pad;
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
