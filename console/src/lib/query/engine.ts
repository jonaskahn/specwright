// Port of the traversal semantics in kitlib/graph_query.py, over the exported graph.json.
// Results are structured; the golden files in workshop/fixtures/console-golden prove parity.

import type { GraphEdge, GraphNode } from '../../../contract/types';

export class QueryError extends Error {
  constructor(
    message: string,
    public options: string[] = [],
  ) {
    super(message);
  }
}

type Side = 'out' | 'in';
const UP = new Set(['has_ac:in', 'has_task:in', 'member_of:out', 'realizes:out']);
const DOWN = new Set(['has_ac:out', 'has_task:out', 'member_of:in']);

export interface EdgeRow {
  side: Side;
  rel: string;
  other: string;
  cls: string;
  res: string | null;
  file: string | null;
  line: number;
}
export interface LevelRow {
  level: number;
  key: string;
  rel: string;
}
export interface Hop extends EdgeRow {
  from: string;
  to: string;
}
export interface Impact {
  features: string[];
  criteria: string[];
  tasks: string[];
  jira: string[];
}

const byKey = (a: GraphNode, b: GraphNode) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);

export class GraphIndex {
  nodes = new Map<string, GraphNode>();
  /** Edges in file order: out sorted by source, in sorted by target (as edges-in.tsv is). */
  outFile: GraphEdge[];
  inFile: GraphEdge[];

  constructor(nodes: GraphNode[], edges: GraphEdge[]) {
    for (const n of nodes) this.nodes.set(n.key, n);
    this.outFile = edges;
    const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
    this.inFile = [...edges].sort(
      (a, b) => cmp(a.to, b.to) || cmp(a.rel, b.rel) || cmp(a.from, b.from) || cmp(a.class, b.class) || a.line - b.line,
    );
  }

  edgesFor(keys: Set<string>, side: Side): GraphEdge[] {
    const file = side === 'out' ? this.outFile : this.inFile;
    return file.filter((e) => keys.has(side === 'out' ? e.from : e.to));
  }

  node(key: string): GraphNode | undefined {
    return this.nodes.get(key);
  }

  private lookup(text: string, fuzzy: boolean): GraphNode[] {
    const needle = text.trim();
    const low = needle.toLowerCase();
    const all = [...this.nodes.values()];
    const keyed = all.filter((n) => n.key === needle || n.key.endsWith(':' + needle));
    if (keyed.length) return keyed;
    const aliased = (n: GraphNode) => n.aliases.map((a) => a.toLowerCase());
    const named = all.filter((n) => aliased(n).includes(low));
    if (named.length || !fuzzy || !low) return named;
    return all.filter((n) => n.title.toLowerCase().includes(low) || aliased(n).some((a) => a.includes(low)));
  }

  resolve(text: string, fuzzy = false): string {
    let t = text.trim().replace(/^STORY-(\d+)/i, 'FEAT-$1');
    if (t.startsWith('jira:') || t.startsWith('code:')) return t;
    const qualified = /^[A-Z][A-Z0-9]*:[A-Za-z0-9-]+$/.test(t);
    if (qualified) return t;
    const hits = this.lookup(t, fuzzy);
    if (t.includes('/') && !hits.length) return t;
    if (hits.length === 1) return hits[0].key;
    if (hits.length) {
      const options = [...hits].sort(byKey).map((n) => `${n.key}  ${n.title}`.trimEnd());
      throw new QueryError(`${t} names several items; pick one`, options);
    }
    t = t.trim();
    throw new QueryError(/^[A-Z]+-\d+/.test(t) ? `unknown ID: ${t}` : `no item is known as: ${t}`);
  }

  private known(key: string): void {
    if (!this.nodes.has(key)) throw new QueryError(`unknown ID: ${key}`);
  }

  find(opts: { text?: string; kind?: string; status?: string; jira?: string; epic?: string }): GraphNode[] {
    let allowed: Set<string> | null = null;
    if (opts.jira) {
      allowed = new Set(this.edgesFor(new Set([`jira:${opts.jira}`]), 'in').filter((e) => e.rel === 'published_as').map((e) => e.from));
    }
    if (opts.epic) {
      const epic = this.resolve(opts.epic);
      const members = new Set(this.edgesFor(new Set([epic]), 'in').filter((e) => e.rel === 'member_of').map((e) => e.from));
      allowed = allowed ? new Set([...allowed].filter((k) => members.has(k))) : members;
    }
    const needle = (opts.text ?? '').toLowerCase();
    return [...this.nodes.values()]
      .filter((n) => !opts.kind || n.kind === opts.kind)
      .filter((n) => !opts.status || n.status === opts.status)
      .filter((n) => !allowed || allowed.has(n.key))
      .filter((n) => !needle || [n.key, n.title, n.aliases.join('|')].join(' ').toLowerCase().includes(needle))
      .sort(byKey);
  }

  neighbors(key: string, dir: Side | 'both' = 'both', rel?: string, declaredOnly = false): EdgeRow[] {
    if (!this.nodes.has(key) && !key.startsWith('jira:') && !key.startsWith('code:')) throw new QueryError(`unknown ID: ${key}`);
    const sides: Side[] = dir === 'both' ? ['out', 'in'] : [dir];
    const rows: EdgeRow[] = [];
    for (const side of sides) {
      for (const e of this.edgesFor(new Set([key]), side)) {
        if (rel && e.rel !== rel) continue;
        if (declaredOnly && e.class === 'mentioned') continue;
        rows.push({ side, rel: e.rel, other: side === 'out' ? e.to : e.from, cls: e.class, res: e.resolution, file: e.file, line: e.line });
      }
    }
    return rows;
  }

  private walk(key: string, allowed: Set<string>, depth: number): LevelRow[] {
    const seen = new Set([key]);
    let frontier = new Set([key]);
    const out: LevelRow[] = [];
    for (let level = 1; level <= depth; level++) {
      const found = new Map<string, string>();
      for (const side of ['out', 'in'] as const) {
        for (const e of this.edgesFor(frontier, side)) {
          if (!allowed.has(`${e.rel}:${side}`)) continue;
          const other = side === 'out' ? e.to : e.from;
          if (!seen.has(other) && !found.has(other)) found.set(other, e.rel);
        }
      }
      if (!found.size) return out;
      for (const other of [...found.keys()].sort()) {
        seen.add(other);
        out.push({ level, key: other, rel: found.get(other)! });
      }
      frontier = new Set(found.keys());
    }
    return out;
  }

  up(key: string): LevelRow[] {
    this.known(key);
    return this.walk(key, UP, 6);
  }

  down(key: string, depth = 2): LevelRow[] {
    this.known(key);
    return this.walk(key, DOWN, depth);
  }

  path(a: string, b: string, longest = 6): { found: boolean; hops: Hop[] } {
    this.known(a);
    this.known(b);
    const parent = new Map<string, { prev: string; edge: GraphEdge; side: Side }>();
    const seen = new Set([a]);
    let frontier = new Set([a]);
    for (let i = 0; i < longest; i++) {
      const step = new Map<string, { prev: string; edge: GraphEdge; side: Side }>();
      for (const side of ['out', 'in'] as const) {
        for (const e of this.edgesFor(frontier, side)) {
          const [here, other] = side === 'out' ? [e.from, e.to] : [e.to, e.from];
          if (!seen.has(other) && !step.has(other)) step.set(other, { prev: here, edge: e, side });
        }
      }
      for (const [other, value] of step) {
        parent.set(other, value);
        seen.add(other);
      }
      frontier = new Set(step.keys());
      if (seen.has(b) || !frontier.size) break;
    }
    if (!parent.has(b) && a !== b) return { found: false, hops: [] };
    const hops: Hop[] = [];
    let cur = b;
    while (cur !== a) {
      const { prev, edge, side } = parent.get(cur)!;
      hops.push({ side, rel: edge.rel, other: cur, cls: edge.class, res: edge.resolution, file: edge.file, line: edge.line, from: prev, to: cur });
      cur = prev;
    }
    return { found: true, hops: hops.reverse() };
  }

  impact(target: string, includeMentions = false): Impact {
    let seeds: Set<string>;
    if (target.startsWith('jira:')) {
      seeds = new Set(this.edgesFor(new Set([target]), 'in').filter((e) => e.rel === 'published_as').map((e) => e.from));
      if (!seeds.size) throw new QueryError(`unknown Jira key: ${target.slice(5)}`);
    } else {
      this.known(target);
      seeds = new Set([target]);
    }
    const reached = new Set(seeds);
    for (;;) {
      const added = new Set<string>();
      for (const e of this.edgesFor(reached, 'in')) {
        if (e.rel === 'mentions' && !includeMentions) continue;
        if (e.rel === 'published_as' || e.rel === 'last_snapshot') continue;
        added.add(e.from);
      }
      for (const e of this.edgesFor(reached, 'out')) if (e.rel === 'has_ac' || e.rel === 'has_task') added.add(e.to);
      for (const k of reached) added.delete(k);
      if (!added.size) break;
      for (const k of added) reached.add(k);
    }
    const pick = (marker: string) => [...reached].filter((k) => k.includes(marker)).sort();
    const jira = this.edgesFor(reached, 'out').filter((e) => e.rel === 'published_as').map((e) => e.to.slice(5)).sort();
    return { features: pick(':FEAT-'), criteria: pick(':AC-'), tasks: pick(':TASK-'), jira };
  }
}
