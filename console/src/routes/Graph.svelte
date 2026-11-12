<script lang="ts">
  import CoverageStrip from '../components/CoverageStrip.svelte';
  import GraphCanvas from '../components/GraphCanvas.svelte';
  import NodePanel from '../components/NodePanel.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import TraceMap from '../components/TraceMap.svelte';
  import TreeItem from '../components/TreeItem.svelte';
  import { app } from '../lib/data/store.svelte';
  import { buildTree, scopedGraph } from '../lib/data/selectors';
  import { hue } from '../lib/graph/layout';
  import { buildTrace, focusModel, LEVEL_KINDS, traceCoverage } from '../lib/graph/trace';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
  import { kindWords } from '../lib/vocabulary';

  const LIMIT = 2500;
  const TRACE_LIMIT = 250;
  let view = $state<'trace' | 'network' | 'table'>('trace');
  let text = $state('');
  let hidden = $state(new Set<string>());
  let mentions = $state(false);
  let selected = $state<string | null>(null);
  let measure = $state<string | null>(null);
  let focusKey = $state<string | null>(null);

  $effect(() => { if (app.route.param) selected = app.route.param; });

  const scoped = $derived(scopedGraph(app.loaded, app.scope));
  const all = $derived(scoped.nodes);
  const known = $derived(new Set(all.map((n) => n.key)));
  const allEdges = $derived(scoped.edges);
  const kinds = $derived([...new Set(all.map((n) => n.kind))].sort());
  const needle = $derived(text.trim().toLowerCase());
  const nodes = $derived(all.filter((n) => !hidden.has(n.kind) && (!needle || `${n.key} ${n.title}`.toLowerCase().includes(needle))).slice(0, LIMIT));
  const keys = $derived(new Set(nodes.map((n) => n.key)));
  const edges = $derived(allEdges.filter((e) => keys.has(e.from) && keys.has(e.to) && (mentions || e.class !== 'mentioned')));

  const chainCount = $derived(all.filter((n) => n.kind in LEVEL_KINDS).length);
  const big = $derived(chainCount > TRACE_LIMIT);
  const picks = $derived(all.filter((n) => n.kind === 'epic' || n.kind === 'feat'));
  const start = $derived(focusKey ?? (selected && known.has(selected) ? selected : (picks[0]?.key ?? null)));
  const model = $derived(big && start ? focusModel(all, allEdges, start) : buildTrace(all, allEdges));
  const coverage = $derived(traceCoverage(all, allEdges));

  const emphasis = $derived.by(() => {
    const out = new Set<string>();
    if (needle) {
      for (const n of model.nodes) if (n.key && `${n.key} ${n.title}`.toLowerCase().includes(needle)) out.add(n.id);
      return out;
    }
    const gaps = new Set(coverage.find((c) => c.id === measure)?.gaps ?? []);
    for (const n of model.nodes) {
      const owner = n.gap ? n.id.split(':').slice(2).join(':') : n.key;
      if (owner && gaps.has(owner)) out.add(n.id);
    }
    return out;
  });
  const ghost = $derived(selected ? model.nodes.find((n) => n.id === selected && n.gap) : undefined);
  const real = $derived(selected && !ghost ? selected : null);
  const outline = $derived(buildTree(app.loaded, app.scope));

  function toggle(kind: string) {
    const next = new Set(hidden);
    if (next.has(kind)) next.delete(kind); else next.add(kind);
    hidden = next;
  }
</script>

<PageHead title="Graph" lede="How goals, epics, features, acceptance criteria, tasks and code connect. Choose an item to see its whole chain.">
  {#snippet actions()}
    <div class="seg" role="group" aria-label="View">
      <button type="button" aria-pressed={view === 'trace'} onclick={() => (view = 'trace')}>Trace</button>
      <button type="button" aria-pressed={view === 'network'} onclick={() => (view = 'network')}>Network</button>
      <button type="button" aria-pressed={view === 'table'} onclick={() => (view = 'table')}>Table</button>
    </div>
  {/snippet}
</PageHead>
{#if all.length}
  <div class="stack-sm">
    {#if view === 'trace'}<CoverageStrip measures={coverage} active={measure} onpick={(id) => (measure = id)} />{/if}
    <div class="row-flex wrap gap-2">
      <input class="input" style:max-inline-size="18rem" type="search" placeholder="Find an item" aria-label="Find an item" bind:value={text} />
      {#if view === 'trace' && big}
        <select class="select" style:max-inline-size="20rem" aria-label="Show the chain around" value={start} onchange={(e) => { focusKey = e.currentTarget.value; selected = null; }}>
          {#each picks as p (p.key)}<option value={p.key}>{kindWords(p.kind)}: {p.title}</option>{/each}
        </select>
      {/if}
      {#if view !== 'trace'}
        {#each kinds as kind (kind)}
          <button class="pill" type="button" aria-pressed={!hidden.has(kind)} style:opacity={hidden.has(kind) ? 0.45 : 1} onclick={() => toggle(kind)}>
            <svg class="mk" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill={`oklch(58% 0.15 ${hue(kind)})`} /></svg>{kindWords(kind, true)}
          </button>
        {/each}
      {/if}
      {#if view === 'network'}
        <label class="row-flex"><input type="checkbox" bind:checked={mentions} /> Links that only mention an item</label>
      {/if}
    </div>
    {#if view === 'trace' && big}
      <div class="banner warn"><div><p>This workspace has {chainCount} items in the chain, too many to read at once. Showing the chain around the item chosen above.</p></div></div>
    {/if}
    {#if view !== 'trace' && all.length > LIMIT}<div class="banner warn">Showing the first {LIMIT} of {all.length} items. Narrow it with a filter.</div>{/if}
    <div class="grid">
      <div class={selected ? 'span-8' : 'span-12'}>
        {#if view === 'trace'}
          {#each model.notes as note (note)}<p class="sub">{note}</p>{/each}
          <TraceMap {model} {selected} {emphasis} onselect={(id) => (selected = id)} />
          <div class="trace-outline card pad tree">
            {#each outline as root (root.key)}<TreeItem node={root} />{/each}
          </div>
          {#if model.broken.length}
            <section class="broken card pad">
              <div class="sec-h"><h2>Broken references</h2><span class="sub">{model.broken.length}</span></div>
              {#each model.broken as b (b.from + b.target)}
                <p><button class="btn ghost" type="button" onclick={() => (selected = b.from)}>{b.sentence}</button></p>
              {/each}
            </section>
          {/if}
        {:else if view === 'network'}
          <div class="graph-wrap"><GraphCanvas {nodes} {edges} {selected} onselect={(k) => (selected = k)} /></div>
        {:else}
          <div class="ledger" style:--cols="minmax(0,1.4fr) 10rem 8rem minmax(0,2fr)">
            <div class="lhead"><span>Identifier</span><span>Kind</span><span>Status</span><span>Title</span></div>
            {#each nodes.slice(0, 300) as n (n.key)}
              <button class="lrow" type="button" onclick={() => (selected = n.key)}>
                <span class="name mono">{n.key}</span><span data-label="Kind" class="chip">{kindWords(n.kind)}</span>
                <span data-label="Status"><Pill look={wordLook(n.status)} /></span><span data-label="Title">{n.title}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>
      {#if selected}
        <div class="span-4">
          {#if ghost}
            <div class="card panel">
              <h3>{ghost.title}</h3>
              <p class="sub">The data holds no link here. Ask <strong>{ghost.next}</strong> to add it; the console only reads.</p>
              <button class="btn" type="button" onclick={() => (selected = null)}>Close</button>
            </div>
          {:else if real}
            <NodePanel nodeKey={real} onpick={(k) => (selected = k)} />
          {/if}
        </div>
      {/if}
    </div>
    <p class="sub">Ask the graph a question in <a href={href('query')}><u>Query</u></a>.</p>
  </div>
{:else}
  <OwnerEmpty kind="graph" what="graph" />
{/if}
