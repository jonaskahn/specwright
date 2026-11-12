<script lang="ts">
  import KanbanCard from '../components/KanbanCard.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import { app } from '../lib/data/store.svelte';
  import { applyFilters, buildCards, COLUMNS, lanes, NO_FILTERS, sortCards, statsOf, summary, type Card, type ColumnId, type ConditionFilter, type Filters, type Lane, type Order } from '../lib/board';
  import { preview } from '../lib/preview.svelte';
  import { shortKey } from '../lib/format';

  const query = $derived(app.route.query);
  const several = $derived(app.scope === '*' && app.scopes.length > 1);
  const filters = $derived<Filters>({
    text: query.get('q') ?? '',
    epic: query.get('epic') ?? '',
    condition: (['blocked', 'in-progress', 'complete'].includes(query.get('cond') ?? '') ? query.get('cond') : 'all') as ConditionFilter,
    turn: query.get('turn') ?? '',
    stale: query.get('stale') === '1',
    scope: query.get('project') ?? '',
  });
  const lane = $derived<Lane>((['project', 'epic', 'turn'].includes(query.get('lane') ?? '') ? query.get('lane') : 'none') as Lane);
  const order = $derived<Order>((['id', 'updated'].includes(query.get('sort') ?? '') ? query.get('sort') : 'rank') as Order);
  const dense = $derived(query.get('dense') === '1');
  const withInactive = $derived(query.get('inactive') === '1');

  let tab = $state<ColumnId>('review');
  let closed = $state(new Set<string>());
  let shown = $state<string | null>(null);

  const cards = $derived(buildCards(app.loaded, app.today, several || app.scopes.length > 1).filter((c) => app.scope === '*' || c.feature.scope === app.scope));
  const everyEpic = $derived([...new Map(cards.flatMap((c) => c.epics).map((e) => [e.key, e.title])).entries()].sort((a, b) => a[1].localeCompare(b[1])));
  const everyTurn = $derived([...new Set(cards.map((c) => c.feature.turn).filter((t): t is string => !!t))].sort());
  const total = $derived(summary(cards));
  const visible = $derived(sortCards(applyFilters(cards, filters), order));
  const columns = $derived(
    COLUMNS.filter((c) => (c.id !== 'inactive' || withInactive) && (c.id !== 'other' || visible.some((v) => v.column === 'other'))).map((c) => ({ ...c, cards: visible.filter((v) => v.column === c.id) })),
  );
  const swimlanes = $derived(lanes(visible, lane, (s) => app.scopes.find((x) => x.scope === s)?.name ?? s));
  const filtering = $derived(filters.text || filters.epic || filters.condition !== 'all' || filters.turn || filters.stale || filters.scope);

  $effect(() => {
    if (!columns.some((c) => c.id === tab)) tab = columns.find((c) => c.cards.length)?.id ?? columns[0]?.id ?? 'review';
  });

  const set = (changes: Record<string, string | null>) => app.setQuery(changes);
  const clear = () => set({ q: null, epic: null, cond: null, turn: null, stale: null, project: null });

  async function copy(command: string) {
    try {
      await navigator.clipboard.writeText(command);
      shown = null;
    } catch {
      shown = command;
    }
  }

  /** Arrow keys move between cards: up and down within a column, left and right to the neighbour column. */
  function arrows(e: KeyboardEvent) {
    const move: Record<string, [number, number]> = { ArrowDown: [0, 1], ArrowUp: [0, -1], ArrowRight: [1, 0], ArrowLeft: [-1, 0] };
    const step = move[e.key];
    const here = (e.target as HTMLElement).closest<HTMLElement>('[data-col]');
    if (!step || !here || !(e.target as HTMLElement).matches('[data-card]')) return;
    const ids = columns.map((c) => c.id as string);
    const col = ids.indexOf(here.dataset.col ?? '') + step[0];
    const row = Number(here.dataset.idx) + step[1];
    const next = ids[col] ? [...document.querySelectorAll<HTMLElement>(`[data-col="${ids[col]}"]`)] : [];
    const target = step[0] ? next[Math.min(row, next.length - 1)] : next.find((n) => Number(n.dataset.idx) === row);
    if (target) {
      e.preventDefault();
      target.querySelector<HTMLElement>('[data-card]')?.focus();
    }
  }
</script>

<PageHead title="Board" lede="Features by station. A card shows what is built, what blocks it and what to run to move it on; the console only reads, so there is nothing to drag." />
{#if cards.length}
  <div class="stack-sm">
    <div class="board-sum" role="group" aria-label="Summary">
      <button type="button" class="sum" aria-pressed={!filtering} onclick={clear}><strong class="num">{total.total}</strong> features</button>
      <button type="button" class="sum bad" aria-pressed={filters.condition === 'blocked'} disabled={!total.blocked} onclick={() => set({ cond: filters.condition === 'blocked' ? null : 'blocked' })}><strong class="num">{total.blocked}</strong> blocked</button>
      {#each total.waiting as [who, n] (who)}
        <button type="button" class="sum" aria-pressed={filters.turn === who} onclick={() => set({ turn: filters.turn === who ? null : who })}><strong class="num">{n}</strong> waiting on {who}</button>
      {/each}
      <button type="button" class="sum warn" aria-pressed={filters.stale} disabled={!total.stale} onclick={() => set({ stale: filters.stale ? null : '1' })}><strong class="num">{total.stale}</strong> idle over 14 days</button>
    </div>
    <div class="row-flex wrap gap-2 board-tools">
      <input class="input" type="search" placeholder="Find a feature or epic" aria-label="Find a feature or epic" value={filters.text} oninput={(e) => set({ q: e.currentTarget.value })} />
      {#if app.scopes.length > 1 && app.scope === '*'}
        <select class="select" aria-label="Project" value={filters.scope} onchange={(e) => set({ project: e.currentTarget.value })}>
          <option value="">Project: all</option>
          {#each app.scopes as s (s.scope)}<option value={s.scope}>{s.name} ({s.scope})</option>{/each}
        </select>
      {/if}
      {#if everyEpic.length}
        <select class="select" aria-label="Epic" value={filters.epic} onchange={(e) => set({ epic: e.currentTarget.value })}>
          <option value="">Epic: all</option>
          {#each everyEpic as [key, title] (key)}<option value={key}>{title} ({shortKey(key)})</option>{/each}
        </select>
      {/if}
      <select class="select" aria-label="Condition" value={filters.condition} onchange={(e) => set({ cond: e.currentTarget.value === 'all' ? null : e.currentTarget.value })}>
        <option value="all">Condition: all</option>
        <option value="blocked">Blocked</option>
        <option value="in-progress">In progress</option>
        <option value="complete">Complete</option>
      </select>
      {#if everyTurn.length}
        <select class="select" aria-label="Turn" value={filters.turn} onchange={(e) => set({ turn: e.currentTarget.value })}>
          <option value="">Turn: all</option>
          {#each everyTurn as who (who)}<option value={who}>{who}</option>{/each}
        </select>
      {/if}
      <select class="select" aria-label="Swimlanes" value={lane} onchange={(e) => set({ lane: e.currentTarget.value === 'none' ? null : e.currentTarget.value })}>
        <option value="none">Lanes: none</option>
        <option value="project">By project</option>
        <option value="epic">By epic</option>
        <option value="turn">By turn</option>
      </select>
      <select class="select" aria-label="Order" value={order} onchange={(e) => set({ sort: e.currentTarget.value === 'rank' ? null : e.currentTarget.value })}>
        <option value="rank">Order: blocked first</option>
        <option value="updated">Order: longest idle</option>
        <option value="id">Order: identifier</option>
      </select>
      <label class="row-flex"><input type="checkbox" checked={dense} onchange={(e) => set({ dense: e.currentTarget.checked ? '1' : null })} /> Compact</label>
      <label class="row-flex"><input type="checkbox" checked={withInactive} onchange={(e) => set({ inactive: e.currentTarget.checked ? '1' : null })} /> Inactive</label>
      {#if filtering}<button class="btn ghost" type="button" onclick={clear}>Clear filters</button>{/if}
    </div>

    <div class="ktabs seg" role="group" aria-label="Station">
      {#each columns as c (c.id)}<button type="button" aria-pressed={tab === c.id} onclick={() => (tab = c.id)}>{c.title} {c.cards.length}</button>{/each}
    </div>

    {#each swimlanes as sl (sl.key)}
      {@const open = !closed.has(sl.key)}
      <section class="klane">
        {#if lane !== 'none'}
          <button class="klane-h" type="button" aria-expanded={open} onclick={() => { const next = new Set(closed); if (open) next.add(sl.key); else next.delete(sl.key); closed = next; }}>
            <span class="chev">{open ? '▾' : '▸'}</span><strong>{sl.title}</strong><span class="sub num">{sl.cards.length}</span>
          </button>
        {/if}
        {#if open}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="kanban" onkeydown={arrows}>
            {#each columns as c (c.id)}
              {@const here = sl.cards.filter((x: Card) => x.column === c.id)}
              {@const stats = statsOf(here)}
              <div class="kcol" class:on={tab === c.id}>
                <header class="kcol-head">
                  <div class="row-flex"><h3>{c.title}</h3><span class="spacer"></span>{#if stats.blocked}<span class="bad num" title="Blocked">▲ {stats.blocked}</span>{/if}<span class="num sub">{here.length}</span></div>
                  {#if here.length}
                    <div class="stackbar" role="img" aria-label={`${stats.complete} complete, ${stats.inProgress} in progress, ${stats.blocked} blocked`}>
                      {#if stats.complete}<span style:--w={stats.complete} style:--c="var(--color-ok)"></span>{/if}
                      {#if stats.inProgress}<span style:--w={stats.inProgress} style:--c="var(--color-warn)"></span>{/if}
                      {#if stats.blocked}<span style:--w={stats.blocked} style:--c="var(--color-danger)"></span>{/if}
                    </div>
                  {/if}
                  <p class="sub">{c.hint}</p>
                </header>
                <div class="kcol-body">
                  {#each here as card, i (card.feature.id)}
                    <KanbanCard {card} {dense} several={app.scopes.length > 1} column={c.id} index={i} {shown} open={(key) => preview.openKey(key)} {copy} />
                  {:else}
                    <p class="muted k-none">Nothing here</p>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    {/each}
  </div>
{:else}
  <OwnerEmpty kind="features" what="feature" />
{/if}
