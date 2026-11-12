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

/** Program → project → epic → feature → AC and task, built from the graph's own links. */
export function buildTree(d: Loaded, scope: string): TreeNode[] {
  const nodes = d.data.graph?.nodes ?? [];
  const edges = d.data.graph?.edges ?? [];
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  const kids = new Map<string, string[]>();
  const hasParent = new Set<string>();
  const link = (parent: string, child: string) => {
    if (!byKey.has(parent) || !byKey.has(child)) return;
    kids.set(parent, [...(kids.get(parent) ?? []), child]);
    hasParent.add(child);
  };
  for (const e of edges) {
    if (e.rel === 'has_ac' || e.rel === 'has_task') link(e.from, e.to);
    else if (e.rel === 'member_of' && e.resolution === 'resolved') link(e.to, e.from);
  }
  const make = (key: string, seen: Set<string>): TreeNode => {
    const n = byKey.get(key)!;
    const next = new Set(seen).add(key);
    const children = (kids.get(key) ?? [])
      .filter((k) => !next.has(k))
      .sort()
      .map((k) => make(k, next));
    return { key, kind: n.kind, title: n.title, status: n.status, children };
  };
  const roots = nodes
    .filter((n) => !hasParent.has(n.key) && ['epic', 'feat'].includes(n.kind) && (scope === '*' || n.scope === scope))
    .map((n) => n.key)
    .sort();
  const projects = scope === '*' ? rows.scopes(d).map((s) => s.scope) : [scope];
  return projects.map((p) => ({
    key: p,
    kind: 'project',
    title: rows.scopes(d).find((s) => s.scope === p)?.name ?? p,
    status: null,
    children: roots.filter((k) => byKey.get(k)?.scope === p).map((k) => make(k, new Set())),
  }));
}
