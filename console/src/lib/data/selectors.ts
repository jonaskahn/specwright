import type { FeaturesRow, GraphEdge, GraphNode, RecordsRow, ScopesRow, TasksRow } from '../../../contract/types';
import { CHAIN_RELS } from '../graph/trace';
import { GraphIndex } from '../query/engine';
import type { Loaded } from './loader';

export interface TreeNode {
  key: string;
  kind: string;
  title: string;
  status: string | null;
  children: TreeNode[];
  /** The project of an item that belongs to another project than the one the tree is about. */
  foreign?: string;
  /** For a feature: how many criteria and tasks it holds, so a reader sees its size at a glance. */
  counts?: { ac: number; task: number };
}

export const rows = {
  scopes: (d: Loaded): ScopesRow[] => d.data.scopes?.rows ?? [],
  features: (d: Loaded): FeaturesRow[] => d.data.features?.rows ?? [],
  tasks: (d: Loaded): TasksRow[] => d.data.tasks?.rows ?? [],
  records: (d: Loaded): RecordsRow[] => d.data.records?.rows ?? [],
  sources: (d: Loaded) => d.data.sources?.rows ?? [],
  registry: (d: Loaded) => d.data.registry?.rows ?? [],
  rtm: (d: Loaded) => d.data.rtm?.rows ?? [],
  results: (d: Loaded) => d.data.quality?.results ?? [],
  findings: (d: Loaded) => d.data.quality?.findings ?? [],
  nodes: (d: Loaded): GraphNode[] => d.data.graph?.nodes ?? [],
};

/** The graph's items and links for one project, or all of them. Links must start inside the scope. */
export function scopedGraph(d: Loaded, scope: string): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes = (d.data.graph?.nodes ?? []).filter((n) => scope === '*' || n.scope === scope || n.scope === null);
  const known = new Set(nodes.map((n) => n.key));
  return { nodes, edges: (d.data.graph?.edges ?? []).filter((e) => known.has(e.from)) };
}

export interface ProjectGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** Keys of the items that belong to another project but are linked to this one. */
  foreign: Set<string>;
}

const OUTLINE_KINDS = new Set(['bo', 'epic', 'feat']);

/**
 * One project's graph: its own items, plus the epics and objectives of other projects that its
 * features are linked to, so a link across projects is drawn instead of reported as missing.
 */
export function projectGraph(d: Loaded, scope: string): ProjectGraph {
  const all = d.data.graph?.nodes ?? [];
  const edges = d.data.graph?.edges ?? [];
  const byKey = new Map(all.map((n) => [n.key, n]));
  const home = new Set(all.filter((n) => n.scope === scope || n.scope === null).map((n) => n.key));
  const foreign = new Set<string>();
  for (const e of edges) {
    if (!CHAIN_RELS.has(e.rel)) continue;
    const other = home.has(e.from) ? e.to : home.has(e.to) ? e.from : null;
    if (other && !home.has(other) && OUTLINE_KINDS.has(byKey.get(other)?.kind ?? '')) foreign.add(other);
  }
  const inside = (key: string) => home.has(key) || foreign.has(key);
  return {
    nodes: all.filter((n) => inside(n.key)),
    // A link to something nobody defined stays, so it can be reported as broken.
    edges: edges.filter((e) => inside(e.from) && (inside(e.to) || !byKey.has(e.to))),
    foreign,
  };
}

/** Every link between two projects, with the objectives, epics and features it joins. */
export function acrossProjects(d: Loaded): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const all = d.data.graph?.nodes ?? [];
  const byKey = new Map(all.map((n) => [n.key, n]));
  const chain = (d.data.graph?.edges ?? []).filter((e) => CHAIN_RELS.has(e.rel) && byKey.has(e.from) && byKey.has(e.to));
  const apart = (e: GraphEdge) => {
    const a = byKey.get(e.from)?.scope;
    const b = byKey.get(e.to)?.scope;
    return !!a && !!b && a !== b;
  };
  const keep = new Set<string>();
  for (const e of chain.filter(apart)) {
    keep.add(e.from);
    keep.add(e.to);
  }
  // Add what each end belongs to, upwards, so a feature is shown under its epic and objective.
  for (let grew = true; grew; ) {
    grew = false;
    for (const e of chain) {
      const up = byKey.get(e.to)?.kind;
      if (keep.has(e.from) && !keep.has(e.to) && (up === 'epic' || up === 'bo')) {
        keep.add(e.to);
        grew = true;
      }
    }
  }
  return { nodes: all.filter((n) => keep.has(n.key)), edges: chain.filter((e) => keep.has(e.from) && keep.has(e.to)) };
}

export const crossLinks = (d: Loaded): number => {
  const byKey = new Map((d.data.graph?.nodes ?? []).map((n) => [n.key, n]));
  return (d.data.graph?.edges ?? []).filter((e) => CHAIN_RELS.has(e.rel) && !!byKey.get(e.from)?.scope && !!byKey.get(e.to)?.scope && byKey.get(e.from)!.scope !== byKey.get(e.to)!.scope).length;
};

export function graphIndex(d: Loaded): GraphIndex {
  return new GraphIndex(d.data.graph?.nodes ?? [], d.data.graph?.edges ?? []);
}

/** The scopes to show: every scope, or the one picked in the sidebar. */
export function inScope<T extends { scope?: string | null }>(items: T[], scope: string): T[] {
  return scope === '*' ? items : items.filter((i) => i.scope === scope);
}

/**
 * Project, epic, feature, acceptance criterion, task, built from the graph's own links. A task sits
 * under the criterion it implements; one that implements none sits under a "not tied" group, and a
 * feature in no epic sits under "No epic yet" (only when the project has epics at all).
 */
export function buildTree(d: Loaded, scope: string): TreeNode[] {
  const nodes = d.data.graph?.nodes ?? [];
  const edges = d.data.graph?.edges ?? [];
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  const live = (key: string) => byKey.has(key);
  const children = new Map<string, string[]>();
  const add = (parent: string, child: string) => {
    if (live(parent) && live(child) && !(children.get(parent) ?? []).includes(child)) children.set(parent, [...(children.get(parent) ?? []), child]);
  };
  const epicOf = new Set<string>();
  const tied = new Set<string>();
  const taskOwner = new Map<string, string>();
  for (const e of edges) {
    if (e.rel === 'has_ac') add(e.from, e.to);
    else if (e.rel === 'member_of' && e.resolution === 'resolved' && byKey.get(e.to)?.kind === 'epic') {
      add(e.to, e.from);
      epicOf.add(e.from);
    } else if (e.rel === 'implements' && byKey.get(e.to)?.kind === 'ac' && byKey.get(e.from)?.kind === 'task') {
      add(e.to, e.from);
      tied.add(e.from);
    } else if (e.rel === 'has_task') taskOwner.set(e.to, e.from);
  }
  const leaf = (key: string, kids: TreeNode[] = [], project?: string): TreeNode => {
    const n = byKey.get(key)!;
    const out: TreeNode = { key, kind: n.kind, title: n.title, status: n.status, children: kids };
    if (project && n.scope && n.scope !== project) out.foreign = n.scope;
    return out;
  };
  const group = (id: string, title: string, kids: TreeNode[]): TreeNode => ({ key: id, kind: 'gap', title, status: null, children: kids });
  const sorted = (keys: string[]) => [...keys].sort();
  const criterion = (key: string) => leaf(key, sorted(children.get(key) ?? []).map((t) => leaf(t)));
  const feature = (project: string) => (key: string): TreeNode => {
    const untied = [...taskOwner].filter(([task, owner]) => owner === key && !tied.has(task)).map(([task]) => task);
    const kids = sorted(children.get(key) ?? []).map(criterion);
    if (untied.length) kids.push(group(`gap:task:${key}`, 'Tasks not tied to an acceptance criterion', sorted(untied).map((t) => leaf(t))));
    const out = leaf(key, kids, project);
    out.counts = { ac: kids.filter((k) => k.kind === 'ac').length, task: [...taskOwner].filter(([, owner]) => owner === key).length };
    return out;
  };
  const inScope = (n: GraphNode, project: string) => n.scope === project;
  const projects = scope === '*' ? rows.scopes(d).map((s) => s.scope) : [scope];
  return projects.map((p) => {
    const features = sorted(nodes.filter((n) => n.kind === 'feat' && inScope(n, p)).map((n) => n.key));
    // The project's own epics, and an epic of another project that one of its features belongs to.
    const joined = new Set(nodes.filter((n) => n.kind === 'epic' && (children.get(n.key) ?? []).some((f) => features.includes(f))).map((n) => n.key));
    const epics = sorted([...new Set([...nodes.filter((n) => n.kind === 'epic' && inScope(n, p)).map((n) => n.key), ...joined])]);
    const loose = features.filter((k) => !epicOf.has(k));
    const kids = epics.map((e) => leaf(e, sorted(children.get(e) ?? []).map(feature(p)), p));
    if (epics.length && loose.length) kids.push(group(`gap:epic:${p}`, 'Features in no epic yet', loose.map(feature(p))));
    else if (!epics.length) kids.push(...loose.map(feature(p)));
    return { key: p, kind: 'project', title: rows.scopes(d).find((s) => s.scope === p)?.name ?? p, status: null, children: kids };
  });
}

/** Keep the items that match the text, with every parent above them; null when nothing matches. */
export function filterTree(node: TreeNode, text: string): TreeNode | null {
  const needle = text.trim().toLowerCase();
  if (!needle) return node;
  const kids = node.children.map((c) => filterTree(c, needle)).filter((c): c is TreeNode => !!c);
  const self = `${node.key} ${node.title}`.toLowerCase().includes(needle);
  return self || kids.length ? { ...node, children: self && !kids.length ? node.children : kids } : null;
}

/** Keys of the items above `key` in the tree, nearest last, so the path to it can be opened. */
export function pathTo(node: TreeNode, key: string, trail: string[] = []): string[] | null {
  if (node.key === key) return trail;
  for (const child of node.children) {
    const found = pathTo(child, key, [...trail, node.key]);
    if (found) return found;
  }
  return null;
}
