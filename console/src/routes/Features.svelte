<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import Rung from '../components/Rung.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince } from '../lib/format';
  import { href } from '../lib/router';
  import { lintLook, stateLook } from '../lib/status';

  let text = $state('');
  let stateFilter = $state('');
  let sort = $state<'id' | 'state' | 'updated'>('id');
  let desc = $state(false);

  const states = $derived([...new Set(app.features.map((f) => f.state))]);
  const shown = $derived.by(() => {
    const needle = text.trim().toLowerCase();
    const rows = app.features.filter((f) => (!stateFilter || f.state === stateFilter) && (!needle || `${f.id} ${f.title}`.toLowerCase().includes(needle)));
    const dir = desc ? -1 : 1;
    return [...rows].sort((a, b) => {
      if (sort === 'updated') return dir * ((a.updated ?? '') < (b.updated ?? '') ? -1 : 1);
      if (sort === 'state') return dir * a.state.localeCompare(b.state) || a.id.localeCompare(b.id);
      return dir * a.id.localeCompare(b.id);
    });
  });
  function by(column: typeof sort) {
    if (sort === column) desc = !desc;
    else { sort = column; desc = false; }
  }
</script>

<PageHead title="Features" lede="Every story in the workspace, with its place on the lifecycle." />
<div class="stack">
  <StaleBanner />
  <div class="row-flex wrap gap-2">
    <div class="search" style:flex="1" style:min-inline-size="14rem">
      <svg class="icon sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4" /></svg>
      <input class="input" type="search" placeholder="Filter by identifier or title" aria-label="Filter features" bind:value={text} />
    </div>
    <select class="select" style:inline-size="12rem" aria-label="State" bind:value={stateFilter}>
      <option value="">All states</option>
      {#each states as s (s)}<option value={s}>{stateLook(s).label}</option>{/each}
    </select>
  </div>
  {#if shown.length}
    <div class="ledger" style:--cols="minmax(0,2.2fr) 11rem 9rem 9rem 5rem 6rem">
      <div class="lhead">
        <button type="button" onclick={() => by('id')}>Feature</button><span>Rung</span>
        <button type="button" onclick={() => by('state')}>State</button><span>Lint</span><span>Open</span>
        <button type="button" onclick={() => by('updated')}>Updated</button>
      </div>
      {#each shown as f (f.id)}
        <a class="lrow" href={href('features', f.id)}>
          <span><span class="name">{f.id}</span><div class="sub">{f.title}</div></span>
          <span data-label="Rung"><Rung state={f.state} condition={f.condition} /></span>
          <span data-label="State"><Pill look={stateLook(f.state, f.condition)} /></span>
          <span data-label="Lint"><Pill look={lintLook(f.lint)} /></span>
          <span data-label="Open" class="num">{f.openQuestions.length + f.openChanges.length}</span>
          <span data-label="Updated" class="muted">{ago(daysSince(f.updated, app.today))}</span>
        </a>
      {/each}
    </div>
  {:else}
    <OwnerEmpty kind="features" what="feature" />
  {/if}
</div>
