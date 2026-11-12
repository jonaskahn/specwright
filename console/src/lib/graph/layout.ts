import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceY, type Simulation, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';
import type { GraphEdge, GraphNode } from '../../../contract/types';

export interface Vertex extends SimulationNodeDatum {
  key: string;
  kind: string;
  title: string;
  r: number;
  /** Row of the work chain (goal at the top, code at the bottom), or null for items off the chain. */
  rank: number | null;
}
export interface Link extends SimulationLinkDatum<Vertex> {
  rel: string;
  cls: string;
}

const RANK: Record<string, number> = { bo: 0, epic: 1, feat: 2, ac: 3, task: 4, code: 5 };
/** How hard a link pulls its ends together: written-down structure beats a passing mention. */
const PULL: Record<string, number> = { structural: 1, declared: 0.7, registry: 0.5, mentioned: 0.08 };

export const KIND_HUE: Record<string, number> = {
  feat: 25, ac: 55, task: 150, epic: 262, bo: 192, idea: 225, q: 78, dec: 8, cr: 40, amendment: 330,
  src: 110, snapshot: 110, risk: 20, br: 280, nfr: 300, fr: 300, stk: 170, plan: 205, jira: 240,
};

export function hue(kind: string): number {
  return KIND_HUE[kind] ?? 250;
}

export function radius(kind: string, links = 0): number {
  const base = kind === 'feat' ? 8 : kind === 'epic' || kind === 'bo' ? 7.5 : 5;
  return base + Math.min(4, Math.sqrt(links) * 0.9);
}

export function build(nodes: GraphNode[], edges: GraphEdge[], previous?: Map<string, Vertex>): { vertices: Vertex[]; links: Link[] } {
  const degree = new Map<string, number>();
  for (const e of edges) {
    degree.set(e.from, (degree.get(e.from) ?? 0) + 1);
    degree.set(e.to, (degree.get(e.to) ?? 0) + 1);
  }
  const vertices: Vertex[] = nodes.map((n) => {
    const old = previous?.get(n.key);
    return { key: n.key, kind: n.kind, title: n.title, r: radius(n.kind, degree.get(n.key) ?? 0), rank: RANK[n.kind] ?? null, x: old?.x, y: old?.y };
  });
  const byKey = new Map(vertices.map((v) => [v.key, v]));
  const links: Link[] = [];
  for (const e of edges) {
    const source = byKey.get(e.from);
    const target = byKey.get(e.to);
    if (source && target) links.push({ source, target, rel: e.rel, cls: e.class });
  }
  return { vertices, links };
}

export function simulate(vertices: Vertex[], links: Link[], onTick: () => void): Simulation<Vertex, Link> {
  const big = vertices.length > 600;
  const sim = forceSimulation(vertices)
    .force('link', forceLink<Vertex, Link>(links).id((v) => v.key).distance(big ? 28 : 52).strength((l) => 0.5 * (PULL[l.cls] ?? 0.4)))
    .force('rank', forceY<Vertex>((v) => ((v.rank ?? 2.5) - 2.5) * 70).strength((v) => (v.rank === null ? 0.01 : 0.07)))
    .force('charge', forceManyBody().strength(big ? -22 : -90).distanceMax(260))
    .force('collide', forceCollide<Vertex>((v) => v.r + 3))
    .force('center', forceCenter(0, 0))
    .alphaDecay(big ? 0.06 : 0.03)
    .on('tick', onTick);
  return sim;
}
