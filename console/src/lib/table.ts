// Filtering, sorting and paging for every table, as plain functions. The state lives in the
// address (`t.<table>.q=…`), so a filtered page survives a reload and the Back button.

export interface Col<R> {
  id: string;
  label: string;
  /** The text shown or sorted for this column; also searched. null sorts last and is not offered as a filter. */
  value: (row: R) => string | number | null;
  sortable?: boolean;
  /** Offer a select with this column's values. */
  facet?: boolean;
  facetLabel?: (value: string) => string;
  /** Used for searching and filtering only: no column is drawn. */
  hidden?: boolean;
}

export interface TableState {
  q: string;
  facets: Record<string, string>;
  sort: string | null;
  dir: 'asc' | 'desc';
  page: number;
  size: number;
}

export const SIZES = [25, 50, 100] as const;
export const defaultState = (size: number = SIZES[0]): TableState => ({ q: '', facets: {}, sort: null, dir: 'asc', page: 1, size });

const text = (v: string | number | null): string => (v === null ? '' : String(v));

export function filterRows<R>(rows: R[], cols: Col<R>[], state: Pick<TableState, 'q' | 'facets'>, extra?: (row: R) => string): R[] {
  const needle = state.q.trim().toLowerCase();
  const picks = Object.entries(state.facets).filter(([, v]) => v);
  return rows.filter((row) => {
    for (const [id, want] of picks) {
      const col = cols.find((c) => c.id === id);
      if (col && text(col.value(row)) !== want) return false;
    }
    if (!needle) return true;
    const hay = [...cols.map((c) => text(c.value(row))), extra?.(row) ?? ''].join(' ').toLowerCase();
    return hay.includes(needle);
  });
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

/** Stable: rows that compare equal keep their order. Empty values go last in either direction. */
export function sortRows<R>(rows: R[], cols: Col<R>[], sort: string | null, dir: 'asc' | 'desc'): R[] {
  const col = cols.find((c) => c.id === sort);
  if (!col) return rows;
  const sign = dir === 'desc' ? -1 : 1;
  return rows
    .map((row, at) => ({ row, at, v: col.value(row) }))
    .sort((a, b) => {
      if (a.v === null || a.v === '') return b.v === null || b.v === '' ? a.at - b.at : 1;
      if (b.v === null || b.v === '') return -1;
      const order = typeof a.v === 'number' && typeof b.v === 'number' ? a.v - b.v : collator.compare(String(a.v), String(b.v));
      return sign * order || a.at - b.at;
    })
    .map((x) => x.row);
}

export interface Page<R> {
  rows: R[];
  page: number;
  pages: number;
  /** 1-based position of the first and last row on the page; 0 when there are none. */
  from: number;
  to: number;
  total: number;
}

export function paginate<R>(rows: R[], page: number, size: number): Page<R> {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const at = Math.min(pages, Math.max(1, Math.floor(page) || 1));
  const start = (at - 1) * size;
  const slice = rows.slice(start, start + size);
  return { rows: slice, page: at, pages, from: slice.length ? start + 1 : 0, to: start + slice.length, total: rows.length };
}

/** The values a column holds, each with how many rows have it, most common first. */
export function facetValues<R>(rows: R[], col: Col<R>): [string, number][] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const v = col.value(row);
    if (v !== null && v !== '') counts.set(String(v), (counts.get(String(v)) ?? 0) + 1);
  }
  return [...counts].sort((a, b) => b[1] - a[1] || collator.compare(a[0], b[0]));
}

const key = (id: string, part: string) => `t.${id}.${part}`;

export function readState(query: URLSearchParams, id: string, size: number = SIZES[0]): TableState {
  const state = defaultState(size);
  state.q = query.get(key(id, 'q')) ?? '';
  for (const [name, value] of query) {
    const prefix = key(id, 'f.');
    if (name.startsWith(prefix) && value) state.facets[name.slice(prefix.length)] = value;
  }
  state.sort = query.get(key(id, 's'));
  state.dir = query.get(key(id, 'd')) === 'desc' ? 'desc' : 'asc';
  const page = Number(query.get(key(id, 'p')));
  state.page = Number.isInteger(page) && page > 0 ? page : 1;
  const n = Number(query.get(key(id, 'n')));
  state.size = (SIZES as readonly number[]).includes(n) ? n : size;
  return state;
}

/** The address changes that make the state: a default value removes its key. */
export function writeState(id: string, state: TableState, size: number = SIZES[0], known: string[] = []): Record<string, string | null> {
  const out: Record<string, string | null> = {
    [key(id, 'q')]: state.q || null,
    [key(id, 's')]: state.sort,
    [key(id, 'd')]: state.sort && state.dir === 'desc' ? 'desc' : null,
    [key(id, 'p')]: state.page > 1 ? String(state.page) : null,
    [key(id, 'n')]: state.size !== size ? String(state.size) : null,
  };
  for (const name of known) out[key(id, `f.${name}`)] = state.facets[name] || null;
  for (const [name, value] of Object.entries(state.facets)) out[key(id, `f.${name}`)] = value || null;
  return out;
}

export const isFiltered = (state: Pick<TableState, 'q' | 'facets'>): boolean => !!state.q.trim() || Object.values(state.facets).some(Boolean);
