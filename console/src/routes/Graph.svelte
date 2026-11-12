<script lang="ts">
  import GraphCanvas from '../components/GraphCanvas.svelte';
  import NodePanel from '../components/NodePanel.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { hue } from '../lib/graph/layout';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';

  const LIMIT = 2500;
  let mode = $state<'graph' | 'table'>('graph');
  let text = $state('');
  let hidden = $state(new Set<string>());
  let mentions = $state(true);
  let selected = $state<string | null>(null);

  $effect(() => { if (app.route.param) selected = app.route.param; });

  const all = $derived(app.loaded.data.graph?.nodes.filter((n) => app.scope === '*' || n.scope === app.scope || n.scope === null) ?? []);
  const kinds = $derived([...new Set(all.map((n) => n.kind))].sort());
  const nodes = $derived.by(() => {
    const needle = text.trim().toLowerCase();
    return all.filter((n) => !hidden.has(n.kind) && (!needle || `${n.key} ${n.title}`.toLowerCase().includes(needle))).slice(0, LIMIT);
  });
  const keys = $derived(new Set(nodes.map((n) => n.key)));
  const edges = $derived(
    (app.loaded.data.graph?.edges ?? []).filter((e) => keys.has(e.from) && keys.has(e.to) && (mentions || e.class !== 'mentioned')),
  );
  function toggle(kind: string) {
    const next = new Set(hidden);
    if (next.has(kind)) next.delete(kind); else next.add(kind);
    hidden = next;
  }
</script>

<PageHead title="Graph" lede="Everything the knowledge graph links. Click an item to see what it touches.">
  {#snippet actions()}
    <div class="seg" role="group" aria-label="View">
      <button type="button" aria-pressed={mode === 'graph'} onclick={() => (mode = 'graph')}>Graph</button>
      <button type="button" aria-pressed={mode === 'table'} onclick={() => (mode = 'table')}>Table</button>
    </div>
  {/snippet}
</PageHead>
{#if all.length}
  <div class="stack-sm">
    <div class="row-flex wrap gap-2">
      <input class="input" style:max-inline-size="18rem" type="search" placeholder="Find an item" aria-label="Find an item" bind:value={text} />
      {#each kinds as kind (kind)}
        <button class="pill" type="button" aria-pressed={!hidden.has(kind)} style:opacity={hidden.has(kind) ? 0.45 : 1} onclick={() => toggle(kind)}>
          <svg class="mk" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill={`oklch(58% 0.15 ${hue(kind)})`} /></svg>{kind}
        </button>
      {/each}
      <label class="row-flex"><input type="checkbox" bind:checked={mentions} /> Mentions</label>
    </div>
    {#if all.length > LIMIT}<div class="banner warn">Showing the first {LIMIT} of {all.length} items. Narrow it with a filter.</div>{/if}
    <div class="grid">
      <div class={selected ? 'span-8' : 'span-12'}>
        {#if mode === 'graph'}
          <div class="graph-wrap"><GraphCanvas {nodes} {edges} {selected} onselect={(k) => (selected = k)} /></div>
        {:else}
          <div class="ledger" style:--cols="minmax(0,1.4fr) 6rem 8rem minmax(0,2fr)">
            <div class="lhead"><span>Key</span><span>Kind</span><span>Status</span><span>Title</span></div>
            {#each nodes.slice(0, 300) as n (n.key)}
              <button class="lrow" type="button" onclick={() => (selected = n.key)}>
                <span class="name mono">{n.key}</span><span data-label="Kind" class="chip">{n.kind}</span>
                <span data-label="Status"><Pill look={wordLook(n.status)} /></span><span data-label="Title">{n.title}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>
      {#if selected}
        <div class="span-4"><NodePanel nodeKey={selected} onpick={(k) => (selected = k)} /></div>
      {/if}
    </div>
    <p class="sub">Query this graph in <a href={href('query')}><u>Query</u></a>.</p>
  </div>
{:else}
  <OwnerEmpty kind="graph" what="graph" />
{/if}
