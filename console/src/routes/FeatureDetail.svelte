<script lang="ts">
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import Rung from '../components/Rung.svelte';
  import TraceMap from '../components/TraceMap.svelte';
  import { scopedGraph } from '../lib/data/selectors';
  import { focusModel } from '../lib/graph/trace';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince } from '../lib/format';
  import { href } from '../lib/router';
  import { illustrationLook, lintLook, stateLook, wordLook } from '../lib/status';
  import { relationWords, stationWords } from '../lib/vocabulary';

  let { id }: { id: string } = $props();
  const feature = $derived(app.features.find((f) => f.id === id) ?? app.loaded.data.features?.rows.find((f) => f.id === id));
  const criteria = $derived(app.graph.nodes.size ? app.graph.down(id, 1).filter((r) => r.rel === 'has_ac') : []);
  const tasks = $derived(app.tasks.filter((t) => t.feature === id));
  const records = $derived(app.records.filter((r) => r.affects.includes(id) || feature?.openQuestions.includes(r.id) || feature?.openChanges.includes(r.id)));
  let picked = $state<string | null>(null);
  const chain = $derived.by(() => {
    if (!app.graph.nodes.has(id)) return null;
    const g = scopedGraph(app.loaded, app.scope);
    const jira = new Map(app.registry.filter((r) => r.jiraKey).map((r) => [r.id, r.jiraKey as string]));
    return focusModel(g.nodes, g.edges, id, { jira });
  });
  const links = $derived(app.graph.nodes.has(id) ? app.graph.neighbors(id, 'both').filter((l) => l.rel !== 'has_ac') : []);
</script>

{#if feature}
  <PageHead title={feature.title} lede={feature.id}>
    {#snippet actions()}
      <a class="btn" href={href('features')}>All features</a>
      <a class="btn primary" href={href('graph', id)}>Show in graph</a>
    {/snippet}
  </PageHead>
  <div class="stack">
    <div class="card pad stack-sm">
      <Rung state={feature.state} condition={feature.condition} />
      <div class="row-flex wrap">
        <Pill look={stateLook(feature.state, feature.condition)} />
        <Pill look={lintLook(feature.lint)} />
        <Pill look={illustrationLook(feature.illustration)} />
        {#if feature.station}<span class="chip">Station: {stationWords(feature.station)}</span>{/if}
        {#if feature.next}<span class="chip">Next: {feature.next}{feature.turn ? ` · ${feature.turn}` : ''}</span>{/if}
      </div>
      <dl class="facts">
        <div><dt>Updated</dt><dd>{ago(daysSince(feature.updated, app.today))}</dd></div>
        <div><dt>Jira</dt><dd>{feature.jira ?? 'not published'}</dd></div>
        <div><dt>Sign-off</dt><dd>{feature.signoff ?? 'not set'}</dd></div>
        <div><dt>Drift</dt><dd>{feature.drift ?? 'none'}</dd></div>
        <div><dt>Snapshot</dt><dd>{feature.snapshotDate ? ago(daysSince(feature.snapshotDate, app.today)) : 'none'}</dd></div>
        <div><dt>Objectives</dt><dd>{feature.bo.join(', ') || 'none'}</dd></div>
      </dl>
      {#if feature.blockers.length}
        <div class="banner danger"><div>{#each feature.blockers as b (b)}<p>{b}</p>{/each}</div></div>
      {/if}
    </div>

    {#if chain && chain.nodes.length > 1}
      <section>
        <div class="sec-h"><h2>Where this feature sits</h2><span class="sub">Goal, epic, criteria and tasks it connects to. Missing links are shown too.</span></div>
        <TraceMap model={chain} selected={picked} onselect={(k) => (picked = k)} />
      </section>
    {/if}

    <div class="grid">
      <section class="span-6">
        <div class="sec-h"><h2>Acceptance criteria</h2><span class="sub">{feature.acCount}</span></div>
        <div class="ledger keep">
          {#each criteria as c (c.key)}
            <a class="lrow" style:--cols="minmax(0,1fr)" href={href('graph', c.key)}>
              <span><span class="name">{c.key.split(':')[1]}</span><div class="sub">{app.graph.node(c.key)?.title}</div></span>
            </a>
          {:else}
            <div class="lrow" style:--cols="minmax(0,1fr)"><span class="muted">No criteria in the graph.</span></div>
          {/each}
        </div>
      </section>
      <section class="span-6">
        <div class="sec-h"><h2>Tasks</h2><span class="sub">{tasks.length}</span></div>
        <div class="ledger keep">
          {#each tasks as t (t.id)}
            <div class="lrow" style:--cols="minmax(0,1fr) 7rem">
              <span><span class="name">{t.id.split(':')[1]}</span><div class="sub">{t.title}</div></span><Pill look={wordLook(t.status)} />
            </div>
          {:else}
            <div class="lrow" style:--cols="minmax(0,1fr)"><span class="muted">No tasks yet. sw-plan owns tasks.</span></div>
          {/each}
        </div>
      </section>
    </div>

    <section>
      <div class="sec-h"><h2>Records and links</h2></div>
      <div class="ledger keep">
        {#each records as r (r.id)}
          <div class="lrow" style:--cols="minmax(0,1fr) 7rem">
            <span><span class="name">{r.id}</span><div class="sub">{r.title}</div></span><Pill look={wordLook(r.status)} />
          </div>
        {/each}
        {#each links as l, i (i)}
          <a class="lrow" style:--cols="minmax(0,1fr)" href={href('graph', l.other)}>
            <span class="sub">{relationWords(l.rel, l.side)} {app.graph.node(l.other)?.title ?? l.other} <span class="mono">{l.other}</span></span>
          </a>
        {/each}
        {#if !records.length && !links.length}<div class="lrow" style:--cols="minmax(0,1fr)"><span class="muted">No related records.</span></div>{/if}
      </div>
    </section>
  </div>
{:else}
  <PageHead title="Feature not found" lede={id} />
  <div class="empty"><h3>No feature is called {id}</h3><a class="btn" href={href('features')}>All features</a></div>
{/if}
