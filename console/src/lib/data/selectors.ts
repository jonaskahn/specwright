import type { FeaturesRow, GraphEdge, GraphNode, RecordsRow, ScopesRow, TasksRow } from '../../../contract/types';
import { GraphIndex } from '../query/engine';
import type { Loaded } from './loader';

export interface TreeNode {
  key: string;
  kind: string;
  title: string;
  status: string | null;
  children: TreeNode[];
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
  const leaf = (key: string, kids: TreeNode[] = []): TreeNode => {
    const n = byKey.get(key)!;
    return { key, kind: n.kind, title: n.title, status: n.status, children: kids };
  };
  const group = (id: string, title: string, kids: TreeNode[]): TreeNode => ({ key: id, kind: 'gap', title, status: null, children: kids });
  const sorted = (keys: string[]) => [...keys].sort();
  const criterion = (key: string) => leaf(key, sorted(children.get(key) ?? []).map((t) => leaf(t)));
  const feature = (key: string): TreeNode => {
    const untied = [...taskOwner].filter(([task, owner]) => owner === key && !tied.has(task)).map(([task]) => task);
    const kids = sorted(children.get(key) ?? []).map(criterion);
    if (untied.length) kids.push(group(`gap:task:${key}`, 'Tasks not tied to an acceptance criterion', sorted(untied).map((t) => leaf(t))));
    return leaf(key, kids);
  };
  const inScope = (n: GraphNode, project: string) => n.scope === project;
  const projects = scope === '*' ? rows.scopes(d).map((s) => s.scope) : [scope];
  return projects.map((p) => {
    const epics = sorted(nodes.filter((n) => n.kind === 'epic' && inScope(n, p)).map((n) => n.key));
    const features = sorted(nodes.filter((n) => n.kind === 'feat' && inScope(n, p)).map((n) => n.key));
    const loose = features.filter((k) => !epicOf.has(k));
    const kids = epics.map((e) => leaf(e, sorted(children.get(e) ?? []).map(feature)));
    if (epics.length && loose.length) kids.push(group(`gap:epic:${p}`, 'Features in no epic yet', loose.map(feature)));
    else if (!epics.length) kids.push(...loose.map(feature));
    return { key: p, kind: 'project', title: rows.scopes(d).find((s) => s.scope === p)?.name ?? p, status: null, children: kids };
  });
}
