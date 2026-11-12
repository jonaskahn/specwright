<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import GraphCanvas from '../components/GraphCanvas.svelte';
  import PageHead from '../components/PageHead.svelte';
  import { app } from '../lib/data/store.svelte';
  import { preview } from '../lib/preview.svelte';
  import { HELP, keysOf, runQuery, type QueryResult } from '../lib/query/parse';
  import { href } from '../lib/router';
  import type { Col } from '../lib/table';
  import { classWords, kindWords, relationWords, resolutionWords } from '../lib/vocabulary';

  let text = $state(app.route.query.get('q') ?? '');
  const result = $derived<QueryResult | null>(
    app.graph.nodes.size && app.route.query.get('q') ? runQuery(app.graph, app.route.query.get('q') ?? '') : null,
  );
  const lit = $derived(new Set(result ? keysOf(result) : []));
  $effect(() => { text = app.route.query.get('q') ?? ''; });

  function submit(e: Event) {
    e.preventDefault();
    location.hash = href('query', null, text.trim() ? { q: text.trim() } : {});
  }
  const IMPACT_NAMES: Record<string, string> = { features: 'Features', criteria: 'Acceptance criteria', tasks: 'Tasks', jira: 'Jira issues' };
  const go = (key: string) => (location.hash = href('graph', key));
  type NodeRow = Extract<QueryResult, { type: 'nodes' }>['nodes'][number];
  type EdgeRow = Extract<QueryResult, { type: 'edges' }>['rows'][number];
  type LevelRow = Extract<QueryResult, { type: 'levels' }>['rows'][number];
  const nodeCols: Col<NodeRow>[] = [
    { id: 'key', label: 'Key', value: (n) => n.key, sortable: true },
    { id: 'kind', label: 'Kind', value: (n) => n.kind, sortable: true, facet: true, facetLabel: (v) => kindWords(v) },
    { id: 'status', label: 'Status', value: (n) => n.status, sortable: true, facet: true },
    { id: 'title', label: 'Title', value: (n) => n.title, sortable: true },
  ];
  const edgeCols: Col<EdgeRow>[] = [
    { id: 'way', label: 'Way', value: (r) => r.side },
    { id: 'rel', label: 'Relation', value: (r) => r.rel, sortable: true, facet: true, facetLabel: (v) => relationWords(v, 'out') },
    { id: 'item', label: 'Item', value: (r) => r.other, sortable: true },
    { id: 'how', label: 'How it is known', value: (r) => r.cls, facet: true, facetLabel: classWords },
  ];
  const levelCols: Col<LevelRow>[] = [
    { id: 'item', label: 'Item', value: (r) => r.key, sortable: true },
    { id: 'kind', label: 'Kind', value: (r) => app.graph.node(r.key)?.kind ?? 'unknown', sortable: true, facet: true, facetLabel: (v) => kindWords(v) },
  ];
</script>

<PageHead title="Query" lede="Ask the knowledge graph: find, show, neighbors, up, down, path and impact. Each command is explained below." />
<div class="stack">
  <form class="queryline" onsubmit={submit}>
    <input class="input" aria-label="Query" placeholder="path REF:FEAT-001 REF:FEAT-002" bind:value={text} />
    <button class="btn primary" type="submit">Run</button>
  </form>
  {#if !app.graph.nodes.size}
    <div class="empty"><h3>No graph data</h3><p class="muted">graph.json is owned by sw-start. Run <code>graph.py build</code>, then reload.</p></div>
  {:else if result}
    <div class="grid">
      <section class="span-7">
        <div class="sec-h"><h2>{result.title}</h2></div>
        {#if result.type === 'error'}
          <div class="banner danger"><div><p>{result.message}</p>{#each result.options as o (o)}<p class="mono sub">{o}</p>{/each}</div></div>
        {:else if result.type === 'nodes'}
          <DataTable id="qnodes" rows={result.nodes} cols={nodeCols} rowKey={(n) => n.key} title={(n) => n.key} template="minmax(0,1.3fr) 6rem 7rem minmax(0,2fr)" empty="Nothing found." onrow={(n) => preview.openKey(n.key)}>
            {#snippet cells(n)}<span class="chip" data-label="Kind">{kindWords(n.kind)}</span><span data-label="Status">{n.status ?? 'none'}</span><span data-label="Title">{n.title}</span>{/snippet}
          </DataTable>
        {:else if result.type === 'edges'}
          <DataTable id="qedges" rows={result.rows} cols={edgeCols} rowKey={(r) => `${r.side}|${r.rel}|${r.other}`} title={(r) => (r.side === 'out' ? '→' : '←')} template="3rem minmax(0,1fr) minmax(0,1.2fr) 9rem" empty="No links." search={(r) => app.graph.node(r.other)?.title ?? ''} onrow={(r) => preview.openKey(r.other)}>
            {#snippet cells(r)}
              <span class="chip" data-label="Relation">{relationWords(r.rel, r.side)}</span>
              <span data-label="Item"><span class="name">{app.graph.node(r.other)?.title ?? r.other}</span> <span class="mono sub">{r.other}</span></span>
              <span class="sub" data-label="How it is known">{classWords(r.cls)}. {resolutionWords(r.res)}.</span>
            {/snippet}
          </DataTable>
        {:else if result.type === 'levels'}
          <DataTable id="qlevels" rows={result.rows} cols={levelCols} rowKey={(r) => r.key} title={(r) => app.graph.node(r.key)?.title ?? r.key} sub={(r) => `level ${r.level} · ${r.key}`} template="minmax(0,1fr) 9rem" keep empty="Nothing reached." onrow={(r) => preview.openKey(r.key)}>
            {#snippet cells(r)}<span class="chip">{kindWords(app.graph.node(r.key)?.kind ?? 'unknown')}</span>{/snippet}
          </DataTable>
        {:else if result.type === 'path'}
          {#if result.found}
            <div class="path-hops">
              {#each result.hops as h, i (i)}
                <div class="hop"><span class="mono">{h.from}</span><span class="muted">{h.side === 'out' ? '—' : '←'} {relationWords(h.rel, h.side)} {h.side === 'out' ? '→' : '—'}</span><span class="mono">{h.to}</span><span class="sub">{classWords(h.cls)} · {h.file}:{h.line}</span></div>
              {:else}<div class="hop">Same item.</div>{/each}
            </div>
          {:else}<div class="empty"><h3>No connection</h3><p class="muted">These items are not linked within 6 hops.</p></div>{/if}
        {:else}
          <div class="card pad stack-sm">
            {#each Object.entries(result.impact) as [name, list] (name)}
              <div><strong>{IMPACT_NAMES[name] ?? name}</strong> <span class="muted">{list.length}</span><div class="row-flex wrap">{#each list as k (k)}<button class="chip" type="button" onclick={() => go(name === 'jira' ? `jira:${k}` : k)}>{k}</button>{:else}<span class="muted">none</span>{/each}</div></div>
            {/each}
          </div>
        {/if}
      </section>
      <section class="span-5">
        <div class="sec-h"><h2>On the graph</h2></div>
        <div class="graph-wrap"><GraphCanvas nodes={app.loaded.data.graph?.nodes ?? []} edges={app.loaded.data.graph?.edges ?? []} highlight={lit} onselect={(k) => k && go(k)} /></div>
      </section>
    </div>
  {:else}
    <div class="card pad"><strong>Queries</strong><div class="helplist">{#each HELP as h (h)}<span>{h}</span>{/each}</div></div>
  {/if}
</div>
