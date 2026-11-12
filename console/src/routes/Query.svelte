<script lang="ts">
  import GraphCanvas from '../components/GraphCanvas.svelte';
  import PageHead from '../components/PageHead.svelte';
  import { app } from '../lib/data/store.svelte';
  import { HELP, keysOf, runQuery, type QueryResult } from '../lib/query/parse';
  import { href } from '../lib/router';

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
  const go = (key: string) => (location.hash = href('graph', key));
</script>

<PageHead title="Query" lede="Ask the graph: find, show, neighbors, up, down, path, impact." />
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
          <div class="ledger" style:--cols="minmax(0,1.3fr) 5rem 7rem minmax(0,2fr)">
            <div class="lhead"><span>Key</span><span>Kind</span><span>Status</span><span>Title</span></div>
            {#each result.nodes.slice(0, 200) as n (n.key)}
              <button class="lrow" type="button" onclick={() => go(n.key)}><span class="name mono">{n.key}</span><span class="chip">{n.kind}</span><span>{n.status ?? 'none'}</span><span>{n.title}</span></button>
            {:else}<div class="lrow"><span class="muted">Nothing found.</span></div>{/each}
          </div>
        {:else if result.type === 'edges'}
          <div class="ledger" style:--cols="3rem minmax(0,1fr) minmax(0,1.2fr) 9rem">
            <div class="lhead"><span>Way</span><span>Relation</span><span>Item</span><span>Where</span></div>
            {#each result.rows as r, i (i)}
              <button class="lrow" type="button" onclick={() => go(r.other)}><span>{r.side === 'out' ? '→' : '←'}</span><span class="chip">{r.rel}</span><span class="mono">{r.other}</span><span class="sub">{r.cls}/{r.res ?? '-'}</span></button>
            {:else}<div class="lrow"><span class="muted">No links.</span></div>{/each}
          </div>
        {:else if result.type === 'levels'}
          <div class="ledger keep" style:--cols="minmax(0,1fr) 9rem">
            {#each result.rows as r (r.key)}
              <button class="lrow" type="button" onclick={() => go(r.key)}><span class="mono" style:padding-inline-start={`${(r.level - 1) * 16}px`}>{r.key}</span><span class="chip">{r.rel}</span></button>
            {:else}<div class="lrow"><span class="muted">Nothing reached.</span></div>{/each}
          </div>
        {:else if result.type === 'path'}
          {#if result.found}
            <div class="path-hops">
              {#each result.hops as h, i (i)}
                <div class="hop"><span class="mono">{h.from}</span><span class="muted">{h.side === 'out' ? '—' : '←'} {h.rel} {h.side === 'out' ? '→' : '—'}</span><span class="mono">{h.to}</span><span class="sub">{h.cls}/{h.res ?? '-'} · {h.file}:{h.line}</span></div>
              {:else}<div class="hop">Same item.</div>{/each}
            </div>
          {:else}<div class="empty"><h3>No connection</h3><p class="muted">These items are not linked within 6 hops.</p></div>{/if}
        {:else}
          <div class="card pad stack-sm">
            {#each Object.entries(result.impact) as [name, list] (name)}
              <div><strong>{name}</strong> <span class="muted">{list.length}</span><div class="row-flex wrap">{#each list as k (k)}<button class="chip" type="button" onclick={() => go(name === 'jira' ? `jira:${k}` : k)}>{k}</button>{:else}<span class="muted">none</span>{/each}</div></div>
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
