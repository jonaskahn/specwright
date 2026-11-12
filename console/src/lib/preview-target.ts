// What the preview panel shows, and how a choice is kept in the address so a reload or a shared
// link comes back to the same place. A choice is either an item (`pk=REF:AC-001-2`) or a file
// (`p=REF/records/CR-001.md:12`).

import type { Loaded } from './data/loader';
import { previewable } from './markdown/links';

export interface PreviewTarget {
  key: string | null;
  kind: string | null;
  scope: string | null;
  path: string | null;
  line: number;
  title: string;
}

const base = (path: string) => path.slice(path.lastIndexOf('/') + 1);

export function forFile(scope: string, path: string, line = 1, title = base(path)): PreviewTarget {
  return { key: null, kind: null, scope, path, line, title };
}

/** The item a key names, from the graph first and then from the rows that carry a file. */
export function forKey(d: Loaded, key: string): PreviewTarget | null {
  const nodes = d.data.graph?.nodes ?? [];
  let node = nodes.find((n) => n.key === key);
  if (!node && !key.includes(':')) {
    const hits = nodes.filter((n) => n.key.endsWith(`:${key}`));
    if (hits.length === 1) node = hits[0];
  }
  if (node) return { key: node.key, kind: node.kind, scope: node.scope, path: node.path, line: node.line || 1, title: node.title || node.key };
  const rows: { id: string; kind: string | null; scope: string; title: string; path: string | null; line?: number }[] = [
    ...(d.data.features?.rows ?? []).map((r) => ({ ...r, kind: 'feat' })),
    ...(d.data.tasks?.rows ?? []).map((r) => ({ ...r, kind: 'task' })),
    ...(d.data.records?.rows ?? []),
    ...(d.data.sources?.rows ?? []),
  ];
  const row = rows.find((r) => r.id === key);
  return row ? { key: row.id, kind: row.kind, scope: row.scope, path: row.path ?? null, line: row.line || 1, title: row.title || row.id } : null;
}

export function encode(t: PreviewTarget | null): Record<string, string | null> {
  if (!t) return { pk: null, p: null };
  if (t.key) return { pk: t.key, p: null };
  return { pk: null, p: t.scope && t.path ? `${t.scope}/${t.path}${t.line > 1 ? `:${t.line}` : ''}` : null };
}

export function decode(query: URLSearchParams, d: Loaded): PreviewTarget | null {
  const key = query.get('pk');
  if (key) return forKey(d, key);
  const file = /^([A-Z][A-Z0-9]*)\/(.+?)(?::(\d+))?$/.exec(query.get('p') ?? '');
  if (!file || !previewable(file[2]) || file[2].split('/').includes('..')) return null;
  return forFile(file[1], file[2], file[3] ? Number(file[3]) : 1);
}
