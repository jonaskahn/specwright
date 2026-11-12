import { describe, expect, it } from 'vitest';
import { defaultState, facetValues, filterRows, isFiltered, paginate, readState, sortRows, writeState, type Col } from '../src/lib/table';

interface Row {
  id: string;
  title: string;
  state: string | null;
  n: number;
}
const rows: Row[] = [
  { id: 'FEAT-010', title: 'Refund', state: 'draft', n: 3 },
  { id: 'FEAT-002', title: 'Cancel order', state: 'accepted', n: 1 },
  { id: 'FEAT-001', title: 'Invite a person', state: 'draft', n: 3 },
  { id: 'FEAT-003', title: 'Notify', state: null, n: 2 },
];
const cols: Col<Row>[] = [
  { id: 'id', label: 'ID', value: (r) => r.id, sortable: true },
  { id: 'state', label: 'State', value: (r) => r.state, sortable: true, facet: true },
  { id: 'n', label: 'N', value: (r) => r.n, sortable: true },
  { id: 'title', label: 'Title', value: (r) => r.title, hidden: true },
];

describe('table filtering', () => {
  it('finds rows by any column, including hidden ones, ignoring case', () => {
    expect(filterRows(rows, cols, { q: 'INVITE', facets: {} }).map((r) => r.id)).toEqual(['FEAT-001']);
    expect(filterRows(rows, cols, { q: 'feat-00', facets: {} })).toHaveLength(3);
  });

  it('also searches the extra text a page supplies', () => {
    expect(filterRows(rows, cols, { q: 'alias-x', facets: {} }, (r) => (r.id === 'FEAT-003' ? 'alias-x' : '')).map((r) => r.id)).toEqual(['FEAT-003']);
  });

  it('combines a facet with the text', () => {
    expect(filterRows(rows, cols, { q: '', facets: { state: 'draft' } })).toHaveLength(2);
    expect(filterRows(rows, cols, { q: 'refund', facets: { state: 'draft' } }).map((r) => r.id)).toEqual(['FEAT-010']);
    expect(filterRows(rows, cols, { q: 'refund', facets: { state: 'accepted' } })).toEqual([]);
  });

  it('counts facet values, most common first, leaving out empty ones', () => {
    expect(facetValues(rows, cols[1])).toEqual([
      ['draft', 2],
      ['accepted', 1],
    ]);
  });

  it('knows whether anything is filtered', () => {
    expect(isFiltered({ q: ' ', facets: { state: '' } })).toBe(false);
    expect(isFiltered({ q: 'a', facets: {} })).toBe(true);
    expect(isFiltered({ q: '', facets: { state: 'draft' } })).toBe(true);
  });
});

describe('table sorting', () => {
  it('orders identifiers by number, not by character', () => {
    expect(sortRows(rows, cols, 'id', 'asc').map((r) => r.id)).toEqual(['FEAT-001', 'FEAT-002', 'FEAT-003', 'FEAT-010']);
    expect(sortRows(rows, cols, 'id', 'desc').map((r) => r.id)).toEqual(['FEAT-010', 'FEAT-003', 'FEAT-002', 'FEAT-001']);
  });

  it('is stable: equal rows keep their order, in both directions', () => {
    expect(sortRows(rows, cols, 'n', 'asc').map((r) => r.id)).toEqual(['FEAT-002', 'FEAT-003', 'FEAT-010', 'FEAT-001']);
    expect(sortRows(rows, cols, 'n', 'desc').map((r) => r.id)).toEqual(['FEAT-010', 'FEAT-001', 'FEAT-003', 'FEAT-002']);
  });

  it('puts empty values last whichever way it sorts', () => {
    expect(sortRows(rows, cols, 'state', 'asc').at(-1)?.state).toBeNull();
    expect(sortRows(rows, cols, 'state', 'desc').at(-1)?.state).toBeNull();
  });

  it('leaves the order alone for an unknown column', () => {
    expect(sortRows(rows, cols, 'nope', 'asc')).toBe(rows);
  });
});

describe('table paging', () => {
  const many = Array.from({ length: 60 }, (_, i) => i);

  it('slices a page and reports where it is', () => {
    expect(paginate(many, 1, 25)).toMatchObject({ page: 1, pages: 3, from: 1, to: 25, total: 60 });
    expect(paginate(many, 3, 25)).toMatchObject({ page: 3, from: 51, to: 60 });
    expect(paginate(many, 3, 25).rows).toHaveLength(10);
  });

  it('keeps the page inside the range', () => {
    expect(paginate(many, 99, 25).page).toBe(3);
    expect(paginate(many, 0, 25).page).toBe(1);
    expect(paginate(many, Number.NaN, 25).page).toBe(1);
  });

  it('shows an empty list as one empty page', () => {
    expect(paginate([], 4, 25)).toEqual({ rows: [], page: 1, pages: 1, from: 0, to: 0, total: 0 });
  });
});

describe('table state in the address', () => {
  it('reads the defaults from an empty address', () => {
    expect(readState(new URLSearchParams(), 'features')).toEqual(defaultState());
  });

  it('writes only what differs from the defaults, and reads it back', () => {
    const state = { ...defaultState(), q: 'inv', facets: { state: 'draft' }, sort: 'n', dir: 'desc' as const, page: 2, size: 50 };
    const written = writeState('features', state, 25, ['state']);
    expect(written).toMatchObject({ 't.features.q': 'inv', 't.features.s': 'n', 't.features.d': 'desc', 't.features.p': '2', 't.features.n': '50', 't.features.f.state': 'draft' });
    const query = new URLSearchParams(Object.entries(written).filter((e): e is [string, string] => e[1] !== null));
    expect(readState(query, 'features')).toEqual(state);
    expect(Object.values(writeState('features', defaultState(), 25, ['state'])).every((v) => v === null)).toBe(true);
  });

  it('keeps two tables on one page apart and ignores nonsense', () => {
    const query = new URLSearchParams('t.a.q=x&t.b.q=y&t.a.p=zz&t.a.n=7&t.a.d=sideways');
    expect(readState(query, 'a')).toMatchObject({ q: 'x', page: 1, size: 25, dir: 'asc' });
    expect(readState(query, 'b').q).toBe('y');
  });

  it('writes a facet back to empty when it is cleared', () => {
    const out = writeState('t', { ...defaultState(), facets: { state: '' } }, 25, ['state']);
    expect(out['t.t.f.state']).toBeNull();
  });
});
