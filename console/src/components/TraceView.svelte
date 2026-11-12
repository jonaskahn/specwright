<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { buildTrace, focusModel, LEVEL_KINDS, traceCoverage } from '../lib/graph/trace';
  import type { GraphEdge, GraphNode } from '../../contract/types';
  import { kindWords } from '../lib/vocabulary';
  import CoverageStrip from './CoverageStrip.svelte';
  import TraceMap from './TraceMap.svelte';

  let {
    nodes,
    edges,
    foreign = new Set<string>(),
    selected,
    onselect,
    onview,
    needle = '',
    code = false,
    coverage = true,
    gaps = true,
  }: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    foreign?: Set<string>;
    selected: string | null;
    onselect: (id: string | null) => void;
    onview?: (key: string) => void;
    needle?: string;
    code?: boolean;
    coverage?: boolean;
    /** Placeholders for missing links; off for the map of links between projects, which is partial by design. */
    gaps?: boolean;
  } = $props();

  const TRACE_LIMIT = 250;
  let measure = $state<string | null>(null);
  let focusKey = $state<string | null>(null);

  const chainCount = $derived(nodes.filter((n) => n.kind in LEVEL_KINDS).length);
  const big = $derived(chainCount > TRACE_LIMIT);
  const picks = $derived(nodes.filter((n) => (n.kind === 'epic' || n.kind === 'feat') && !foreign.has(n.key)));
  const known = $derived(new Set(nodes.map((n) => n.key)));
  const start = $derived(focusKey ?? (selected && known.has(selected) ? selected : (picks[0]?.key ?? null)));
  const jira = $derived(new Map(app.registry.filter((r) => r.jiraKey).map((r) => [r.id, r.jiraKey as string])));
  const options = $derived({ code, jira, foreign, gaps });
  const model = $derived(big && start ? focusModel(nodes, edges, start, options) : buildTrace(nodes, edges, options));
  const measures = $derived(traceCoverage(nodes, edges, foreign));

  const emphasis = $derived.by(() => {
    const out = new Set<string>();
    const find = needle.trim().toLowerCase();
    if (find) {
      for (const n of model.nodes) if (n.key && `${n.key} ${n.title}`.toLowerCase().includes(find)) out.add(n.id);
      return out;
    }
    const gaps = new Set(measures.find((c) => c.id === measure)?.gaps ?? []);
    for (const n of model.nodes) {
      const owner = n.gap ? n.id.split(':').slice(2).join(':') : n.key;
      if (owner && gaps.has(owner)) out.add(n.id);
    }
    return out;
  });
</script>

<div class="stack-sm">
  {#if coverage}<CoverageStrip {measures} active={measure} onpick={(id) => (measure = id)} />{/if}
  {#if big}
    <div class="banner warn"><div><p>This project has {chainCount} items in the chain, too many to read at once. Showing the chain around the item chosen here.</p></div></div>
    <select class="select table-pick" aria-label="Show the chain around" value={start} onchange={(e) => { focusKey = e.currentTarget.value; onselect(null); }}>
      {#each picks as p (p.key)}<option value={p.key}>{kindWords(p.kind)}: {p.title}</option>{/each}
    </select>
  {/if}
  {#each model.notes as note (note)}<p class="sub">{note}</p>{/each}
  <TraceMap {model} {selected} {emphasis} {onselect} {onview} />
  {#if model.broken.length}
    <section class="broken card pad">
      <div class="sec-h"><h2>Broken references</h2><span class="sub">{model.broken.length}</span></div>
      {#each model.broken as b (b.from + b.target)}
        <p><button class="btn ghost" type="button" onclick={() => onselect(b.from)}>{b.sentence}</button></p>
      {/each}
    </section>
  {/if}
</div>
