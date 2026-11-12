import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type Simulation, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';
import type { GraphEdge, GraphNode } from '../../../contract/types';

export interface Vertex extends SimulationNodeDatum {
  key: string;
  kind: string;
  title: string;
  r: number;
}
export interface Link extends SimulationLinkDatum<Vertex> {
  rel: string;
  cls: string;
}

export const KIND_HUE: Record<string, number> = {
  feat: 25, ac: 55, task: 150, epic: 262, bo: 192, idea: 225, q: 78, dec: 8, cr: 40, amendment: 330,
  src: 110, snapshot: 110, risk: 20, br: 280, nfr: 300, fr: 300, stk: 170, plan: 205, jira: 240,
};

export function hue(kind: string): number {
  return KIND_HUE[kind] ?? 250;
}

export function radius(kind: string): number {
  return kind === 'feat' ? 9 : kind === 'epic' || kind === 'bo' ? 8 : 5.5;
}

export function build(nodes: GraphNode[], edges: GraphEdge[], previous?: Map<string, Vertex>): { vertices: Vertex[]; links: Link[] } {
  const vertices: Vertex[] = nodes.map((n) => {
    const old = previous?.get(n.key);
    return { key: n.key, kind: n.kind, title: n.title, r: radius(n.kind), x: old?.x, y: old?.y };
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
    .force('link', forceLink<Vertex, Link>(links).id((v) => v.key).distance(big ? 28 : 52).strength(0.5))
    .force('charge', forceManyBody().strength(big ? -22 : -90).distanceMax(260))
    .force('collide', forceCollide<Vertex>((v) => v.r + 3))
    .force('center', forceCenter(0, 0))
    .alphaDecay(big ? 0.06 : 0.03)
    .on('tick', onTick);
  return sim;
}
