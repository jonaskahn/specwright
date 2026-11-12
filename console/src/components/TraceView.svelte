<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { buildTrace, featureOwners, focusModel, traceCoverage } from '../lib/graph/trace';
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
  /** More criteria and tasks than this are not opened all at once; pick features instead. */
  const EXPAND_LIMIT = 150;
  let measure = $state<string | null>(null);
  let focusKey = $state<string | null>(null);
  /** Features kept open on purpose; the feature chosen on the map is open as well. */
  let pinned = $state<Set<string>>(new Set());

  const owners = $derived(featureOwners(nodes, edges));
  const below = $derived(nodes.filter((n) => (n.kind === 'ac' || n.kind === 'task') && !foreign.has(n.key)).length);
  const opened = $derived.by(() => {
    const out = new Set(pinned);
    const own = selected ? owners.get(selected) : undefined;
    if (own) out.add(own);
    return out;
  });
  const chainCount = $derived(nodes.filter((n) => n.kind === 'bo' || n.kind === 'epic' || n.kind === 'feat').length);
  const big = $derived(chainCount > TRACE_LIMIT);
  const picks = $derived(nodes.filter((n) => (n.kind === 'epic' || n.kind === 'feat') && !foreign.has(n.key)));
  const known = $derived(new Set(nodes.map((n) => n.key)));
  const start = $derived(focusKey ?? (selected && known.has(selected) ? selected : (picks[0]?.key ?? null)));
  const jira = $derived(new Map(app.registry.filter((r) => r.jiraKey).map((r) => [r.id, r.jiraKey as string])));
  const options = $derived({ code, jira, foreign, gaps, expand: opened });
  const model = $derived(big && start ? focusModel(nodes, edges, start, options) : buildTrace(nodes, edges, options));
  const measures = $derived(traceCoverage(nodes, edges, foreign));

  const shown = $derived(new Set(model.nodes.map((n) => n.id)));
  /** A folded criterion or task is marked on the feature that holds it. */
  const mark = (out: Set<string>, key: string) => {
    if (shown.has(key)) out.add(key);
    else {
      const feature = owners.get(key);
      if (feature && shown.has(feature)) out.add(feature);
    }
  };
  const emphasis = $derived.by(() => {
    const out = new Set<string>();
    const find = needle.trim().toLowerCase();
    if (find) {
      for (const n of nodes) if (n.key && `${n.key} ${n.title}`.toLowerCase().includes(find)) mark(out, n.key);
      return out;
    }
    const gaps = new Set(measures.find((c) => c.id === measure)?.gaps ?? []);
    for (const n of model.nodes) {
      const owner = n.gap ? n.id.split(':').slice(2).join(':') : n.key;
      if (owner && gaps.has(owner)) out.add(n.id);
    }
    for (const key of gaps) mark(out, key);
    return out;
  });

  function fold(key: string) {
    const next = new Set(pinned);
    if (opened.has(key)) {
      next.delete(key);
      if (selected && owners.get(selected) === key) onselect(null);
    } else next.add(key);
    pinned = next;
  }
  const all = () => (pinned = new Set(model.nodes.filter((n) => n.kind === 'feat' && !n.gap && n.below && n.below.ac + n.below.task > 0).map((n) => n.id)));
  const none = () => {
    pinned = new Set();
    if (selected && owners.has(selected)) onselect(null);
  };
</script>

<div class="stack-sm">
  {#if coverage}<CoverageStrip {measures} active={measure} onpick={(id) => (measure = id)} />{/if}
  {#if big}
    <div class="banner warn"><div><p>This project has {chainCount} objectives, epics and features, too many to read at once. Showing the chain around the item chosen here.</p></div></div>
    <select class="select table-pick" aria-label="Show the chain around" value={start} onchange={(e) => { focusKey = e.currentTarget.value; onselect(null); }}>
      {#each picks as p (p.key)}<option value={p.key}>{kindWords(p.kind)}: {p.title}</option>{/each}
    </select>
  {/if}
  {#each model.notes as note (note)}<p class="sub">{note}</p>{/each}
  {#if below > 0}
    <div class="trace-fold row-flex wrap">
      <p class="sub">
        {#if model.hidden}{model.hidden} {model.hidden === 1 ? 'criterion or task is' : 'criteria and tasks are'} folded. Choose a feature to open its own.{:else}Every feature is open.{/if}
      </p>
      <button class="btn" type="button" disabled={below > EXPAND_LIMIT || !model.hidden} title={below > EXPAND_LIMIT ? `More than ${EXPAND_LIMIT} criteria and tasks; open features one at a time.` : 'Open every feature'} onclick={all}>Open all</button>
      <button class="btn" type="button" disabled={!opened.size} onclick={none}>Fold all</button>
    </div>
  {/if}
  <TraceMap {model} {selected} {emphasis} {onselect} {onview} onfold={fold} />
  {#if model.broken.length}
    <section class="broken card pad">
      <div class="sec-h"><h2>Broken references</h2><span class="sub">{model.broken.length}</span></div>
      {#each model.broken as b (b.from + b.target)}
        <p><button class="btn ghost" type="button" onclick={() => onselect(b.from)}>{b.sentence}</button></p>
      {/each}
    </section>
  {/if}
</div>
