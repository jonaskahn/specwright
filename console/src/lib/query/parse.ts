import { GraphIndex, QueryError, type EdgeRow, type Hop, type Impact, type LevelRow } from './engine';
import type { GraphNode } from '../../../contract/types';

export type QueryResult =
  | { type: 'nodes'; title: string; nodes: GraphNode[] }
  | { type: 'edges'; title: string; rows: EdgeRow[] }
  | { type: 'levels'; title: string; rows: LevelRow[] }
  | { type: 'path'; title: string; found: boolean; hops: Hop[] }
  | { type: 'impact'; title: string; impact: Impact }
  | { type: 'error'; title: string; message: string; options: string[] };

export const COMMANDS = ['find', 'show', 'neighbors', 'up', 'down', 'path', 'impact'] as const;
export const HELP = [
  'find <text> [kind:feat] [status:open] [jira:KEY] [epic:EPIC-1]: items by name, kind, status, Jira issue or epic',
  'show <identifier or name>: one item',
  'neighbors <identifier> [in|out|both] [rel:has_ac] [declared]: what it links to and what links to it',
  'up <identifier>    down <identifier> [depth:3]: the chain above or below an item',
  'path <identifier> <identifier>: how two items connect',
  'impact <identifier>: features, acceptance criteria, tasks and Jira issues it reaches',
  'kind: feat (feature), ac (acceptance criterion), task, epic, bo (business objective), q (question), dec (decision), cr (change request), src (source)',
];

function split(text: string): { words: string[]; flags: Record<string, string> } {
  const words: string[] = [];
  const flags: Record<string, string> = {};
  for (const token of text.trim().split(/\s+/).filter(Boolean)) {
    const found = /^(kind|status|jira|epic|rel|depth):(.+)$/.exec(token);
    if (found) flags[found[1]] = found[2];
    else words.push(token);
  }
  return { words, flags };
}

/** Keys a result touches, for highlighting on the graph. */
export function keysOf(result: QueryResult): string[] {
  switch (result.type) {
    case 'nodes':
      return result.nodes.map((n) => n.key);
    case 'edges':
      return result.rows.map((r) => r.other);
    case 'levels':
      return result.rows.map((r) => r.key);
    case 'path':
      return result.hops.flatMap((h) => [h.from, h.to]);
    case 'impact':
      return [...result.impact.features, ...result.impact.criteria, ...result.impact.tasks];
    default:
      return [];
  }
}

export function runQuery(graph: GraphIndex, input: string): QueryResult {
  const text = input.trim();
  if (!text) return { type: 'error', title: 'Query', message: 'Type a query.', options: HELP };
  const [head, ...rest] = text.split(/\s+/);
  const command = (COMMANDS as readonly string[]).includes(head.toLowerCase()) ? head.toLowerCase() : 'find';
  const { words, flags } = split(command === 'find' && head.toLowerCase() !== 'find' ? text : rest.join(' '));
  try {
    switch (command) {
      case 'find': {
        const nodes = graph.find({ text: words.join(' '), kind: flags.kind, status: flags.status, jira: flags.jira, epic: flags.epic });
        return { type: 'nodes', title: `find ${text.replace(/^find\s+/i, '')}`.trim(), nodes };
      }
      case 'show': {
        const key = graph.resolve(words.join(' '), true);
        const node = graph.node(key);
        return { type: 'nodes', title: `show ${key}`, nodes: node ? [node] : [] };
      }
      case 'neighbors': {
        const key = graph.resolve(words[0] ?? '');
        const dir = (['in', 'out', 'both'] as const).find((d) => words.includes(d)) ?? 'both';
        return { type: 'edges', title: `neighbors ${key}`, rows: graph.neighbors(key, dir, flags.rel, words.includes('declared')) };
      }
      case 'up':
      case 'down': {
        const key = graph.resolve(words[0] ?? '');
        const rows = command === 'up' ? graph.up(key) : graph.down(key, Number(flags.depth ?? 2));
        return { type: 'levels', title: `${command} ${key}`, rows };
      }
      case 'path': {
        const a = graph.resolve(words[0] ?? '');
        const b = graph.resolve(words[1] ?? '');
        return { type: 'path', title: `path ${a} to ${b}`, ...graph.path(a, b) };
      }
      default: {
        const key = graph.resolve(words[0] ?? '');
        return { type: 'impact', title: `impact ${key}`, impact: graph.impact(key) };
      }
    }
  } catch (error) {
    if (error instanceof QueryError) return { type: 'error', title: text, message: error.message, options: error.options };
    throw error;
  }
}
