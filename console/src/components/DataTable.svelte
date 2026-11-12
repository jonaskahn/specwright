<script lang="ts" generics="R">
  import type { Snippet } from 'svelte';
  import { app } from '../lib/data/store.svelte';
  import Icon from './Icon.svelte';
  import { facetValues, filterRows, isFiltered, paginate, readState, SIZES, sortRows, writeState, type Col, type TableState } from '../lib/table';

  let {
    id,
    rows,
    cols,
    template,
    rowKey,
    title,
    sub,
    cells,
    onrow,
    canOpen,
    wide = false,
    keep = false,
    size = SIZES[0],
    search,
    empty = 'Nothing matches the filter.',
  }: {
    /** Names the table in the address, so two tables on a page keep their own state. */
    id: string;
    rows: R[];
    /** The first column is drawn by the table (a title and an optional second line); the rest by `cells`. */
    cols: Col<R>[];
    template: string;
    rowKey: (row: R) => string;
    title: (row: R) => string;
    sub?: (row: R) => string | null | undefined;
    cells?: Snippet<[R]>;
    /** Opens a row in the preview. Only the View button calls it; the row itself does nothing. */
    onrow?: (row: R) => void;
    canOpen?: (row: R) => boolean;
    wide?: boolean;
    keep?: boolean;
    size?: number;
    /** Extra text a row can be found by, beyond its columns. */
    search?: (row: R) => string;
    empty?: string;
  } = $props();

  const state = $derived(readState(app.route.query, id, size));
  const shown = $derived(cols.filter((c) => !c.hidden));
  const facets = $derived(cols.filter((c) => c.facet));
  const filtered = $derived(filterRows(rows, cols, state, search));
  const ordered = $derived(sortRows(filtered, cols, state.sort, state.dir));
  const page = $derived(paginate(ordered, state.page, state.size));
  const options = $derived(facets.map((c) => ({ col: c, values: facetValues(rows, c) })).filter((f) => f.values.length > 1 || state.facets[f.col.id]));
  const searchable = $derived(rows.length > 8 || isFiltered(state));

  function change(next: Partial<TableState>, resetPage = true) {
    const merged = { ...state, ...next, page: resetPage ? 1 : (next.page ?? state.page) };
    app.setQuery(writeState(id, merged, size, facets.map((c) => c.id)));
  }
  const sortBy = (col: Col<R>) => change(state.sort === col.id ? { dir: state.dir === 'asc' ? 'desc' : 'asc' } : { sort: col.id, dir: 'asc' }, false);
  const go = (n: number) => change({ page: Math.min(page.pages, Math.max(1, n)) }, false);
  const clear = () => change({ q: '', facets: {} });
  /** A table that can open its rows gets one more column, with a View button. */
  const columns = $derived(onrow ? `${template} 5.5rem` : template);
</script>

<div class="stack-sm">
  {#if searchable || options.length}
    <div class="row-flex wrap gap-2 table-tools">
      {#if searchable}
        <input class="input" type="search" placeholder="Filter" aria-label={`Filter ${id}`} value={state.q} oninput={(e) => change({ q: e.currentTarget.value })} />
      {/if}
      {#each options as f (f.col.id)}
        <select class="select" aria-label={f.col.label} value={state.facets[f.col.id] ?? ''} onchange={(e) => change({ facets: { ...state.facets, [f.col.id]: e.currentTarget.value } })}>
          <option value="">{f.col.label}: all</option>
          {#each f.values as [value, count] (value)}<option {value}>{f.col.label}: {f.col.facetLabel ? f.col.facetLabel(value) : value} ({count})</option>{/each}
        </select>
      {/each}
      {#if isFiltered(state)}<button class="btn ghost" type="button" onclick={clear}>Clear filters</button>{/if}
      <span class="sub num" aria-live="polite">{filtered.length === rows.length ? `${rows.length} rows` : `${filtered.length} of ${rows.length}`}</span>
    </div>
  {/if}
  {#if page.total}
    <div class="ledger" class:wide class:keep style:--cols={columns}>
      <div class="lhead">
        {#each shown as col (col.id)}
          {#if col.sortable}
            <span><button type="button" aria-label={`Sort by ${col.label}`} onclick={() => sortBy(col)}>{col.label}{state.sort === col.id ? (state.dir === 'asc' ? ' ↑' : ' ↓') : ''}</button></span>
          {:else}<span>{col.label}</span>{/if}
        {/each}
        {#if onrow}<span class="view-col">View</span>{/if}
      </div>
      {#each page.rows as row (rowKey(row))}
        <div class="lrow">
          <span><span class="name">{title(row)}</span>{#if sub?.(row)}<div class="sub">{sub(row)}</div>{/if}</span>
          {@render cells?.(row)}
          {#if onrow}
            <span class="view-col">
              {#if canOpen?.(row) ?? true}<button class="btn view-btn" type="button" aria-label={`View ${title(row)}`} onclick={() => onrow?.(row)}><Icon name="eye" size="sm" />View</button>{/if}
            </span>
          {/if}
        </div>
      {/each}
    </div>
    {#if page.pages > 1 || state.size !== SIZES[0] || rows.length > SIZES[0]}
      <nav class="pager row-flex wrap" aria-label="Pages">
        <span class="sub num">{page.from}–{page.to} of {page.total}</span>
        <span class="spacer"></span>
        <label class="sub row-flex">Rows <select class="select" value={state.size} onchange={(e) => change({ size: Number(e.currentTarget.value) })}>{#each SIZES as n (n)}<option value={n}>{n}</option>{/each}</select></label>
        <button class="btn" type="button" disabled={page.page <= 1} onclick={() => go(1)} aria-label="First page">«</button>
        <button class="btn" type="button" disabled={page.page <= 1} onclick={() => go(page.page - 1)}>Previous</button>
        <span class="num" aria-current="page">{page.page} / {page.pages}</span>
        <button class="btn" type="button" disabled={page.page >= page.pages} onclick={() => go(page.page + 1)}>Next</button>
        <button class="btn" type="button" disabled={page.page >= page.pages} onclick={() => go(page.pages)} aria-label="Last page">»</button>
      </nav>
    {/if}
  {:else}
    <div class="empty"><h3>{empty}</h3>{#if isFiltered(state)}<button class="btn" type="button" onclick={clear}>Clear filters</button>{/if}</div>
  {/if}
</div>
