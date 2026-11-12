<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import Rung from '../components/Rung.svelte';
  import TraceMap from '../components/TraceMap.svelte';
  import { scopedGraph } from '../lib/data/selectors';
  import { focusModel } from '../lib/graph/trace';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince, shortKey } from '../lib/format';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { illustrationLook, lintLook, stateLook, wordLook } from '../lib/status';
  import type { Col } from '../lib/table';
  import { relationWords, stationWords } from '../lib/vocabulary';

  let { id }: { id: string } = $props();
  const feature = $derived(app.features.find((f) => f.id === id) ?? app.loaded.data.features?.rows.find((f) => f.id === id));
  const criteria = $derived(app.graph.nodes.size ? app.graph.down(id, 1).filter((r) => r.rel === 'has_ac') : []);
  const tasks = $derived(app.tasks.filter((t) => t.feature === id));
  const records = $derived(app.records.filter((r) => r.affects.includes(id) || feature?.openQuestions.includes(r.id) || feature?.openChanges.includes(r.id)));
  let picked = $state<string | null>(null);
  type Criterion = (typeof criteria)[number];
  type Task = (typeof tasks)[number];
  type Rec = (typeof records)[number];
  type Link = (typeof links)[number];
  const criterionCols: Col<Criterion>[] = [{ id: 'ac', label: 'Criterion', value: (c) => c.key, sortable: true }];
  const taskCols: Col<Task>[] = [
    { id: 'task', label: 'Task', value: (t) => t.id, sortable: true },
    { id: 'layer', label: 'Layer', value: (t) => t.layer, sortable: true, facet: true },
    { id: 'status', label: 'Status', value: (t) => t.status, facet: true },
  ];
  const recordCols: Col<Rec>[] = [
    { id: 'record', label: 'Record', value: (r) => r.id, sortable: true },
    { id: 'status', label: 'Status', value: (r) => r.status, facet: true },
  ];
  const linkCols: Col<Link>[] = [
    { id: 'link', label: 'Link', value: (l) => `${relationWords(l.rel, l.side)} ${l.other}`, sortable: true },
    { id: 'rel', label: 'Relation', value: (l) => l.rel, facet: true, hidden: true, facetLabel: (v) => relationWords(v, 'out') },
  ];
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
      <button class="btn" type="button" onclick={() => preview.openKey(id)}>Preview story</button>
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
        <TraceMap model={chain} selected={picked} onselect={(k) => { picked = k; if (k && !k.startsWith('gap:')) preview.openKey(k); else preview.close(); }} />
      </section>
    {/if}

    <div class="grid">
      <section class="span-6">
        <div class="sec-h"><h2>Acceptance criteria</h2><span class="sub">{feature.acCount}</span></div>
        {#if criteria.length}
          <DataTable id="acs" rows={criteria} cols={criterionCols} rowKey={(c) => c.key} title={(c) => shortKey(c.key)} sub={(c) => app.graph.node(c.key)?.title} template="minmax(0,1fr)" keep onrow={(c) => preview.openKey(c.key)} />
        {:else}<div class="empty"><p class="muted">No criteria in the graph.</p></div>{/if}
      </section>
      <section class="span-6">
        <div class="sec-h"><h2>Tasks</h2><span class="sub">{tasks.length}</span></div>
        {#if tasks.length}
          <DataTable id="ftasks" rows={tasks} cols={taskCols} rowKey={(t) => t.id} title={(t) => shortKey(t.id)} sub={(t) => t.title} template="minmax(0,1fr) 6rem 7rem" keep onrow={(t) => preview.openKey(t.id)}>
            {#snippet cells(t)}<span>{#if t.layer}<span class="chip">{t.layer}</span>{/if}</span><Pill look={wordLook(t.status)} />{/snippet}
          </DataTable>
        {:else}<div class="empty"><p class="muted">No tasks yet. sw-plan owns tasks.</p></div>{/if}
      </section>
    </div>

    <section>
      <div class="sec-h"><h2>Records and links</h2></div>
      {#if records.length}
        <DataTable id="frecords" rows={records} cols={recordCols} rowKey={(r) => r.id} title={(r) => r.id} sub={(r) => r.title} template="minmax(0,1fr) 7rem" keep onrow={(r) => preview.openKey(r.id)}>
          {#snippet cells(r)}<Pill look={wordLook(r.status)} />{/snippet}
        </DataTable>
      {/if}
      {#if links.length}
        <div class="spaced">
          <DataTable id="flinks" rows={links} cols={linkCols} rowKey={(l) => `${l.side}|${l.rel}|${l.other}`} title={(l) => `${relationWords(l.rel, l.side)} ${app.graph.node(l.other)?.title ?? l.other}`} sub={(l) => l.other} template="minmax(0,1fr)" keep onrow={(l) => preview.openKey(l.other)} />
        </div>
      {/if}
      {#if !records.length && !links.length}<div class="empty"><p class="muted">No related records.</p></div>{/if}
    </section>
  </div>
{:else}
  <PageHead title="Feature not found" lede={id} />
  <div class="empty"><h3>No feature is called {id}</h3><a class="btn" href={href('features')}>All features</a></div>
{/if}
