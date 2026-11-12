<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import GraphCanvas from '../components/GraphCanvas.svelte';
  import Icon from '../components/Icon.svelte';
  import OutlinePane from '../components/OutlinePane.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import TraceView from '../components/TraceView.svelte';
  import { app } from '../lib/data/store.svelte';
  import { acrossProjects, buildTree, crossLinks, projectGraph, scopedGraph } from '../lib/data/selectors';
  import { hue } from '../lib/graph/layout';
  import { LEVEL_KINDS } from '../lib/graph/trace';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
  import type { Col } from '../lib/table';
  import { kindWords } from '../lib/vocabulary';

  type Node = ReturnType<typeof scopedGraph>['nodes'][number];
  const LIMIT = 2500;
  const VIEWS = ['trace', 'network', 'table', 'outline'] as const;
  type View = (typeof VIEWS)[number];

  let text = $state('');
  let hidden = $state(new Set<string>());
  let mentions = $state(false);
  let selected = $state<string | null>(null);
  let code = $state(false);
  let outlineOpen = $state(true);

  const view = $derived<View>((VIEWS as readonly string[]).includes(app.route.query.get('view') ?? '') ? (app.route.query.get('view') as View) : 'trace');
  /** The outline sits beside the trace and the network; the table and the outline view are whole pages. */
  const withOutline = $derived(view === 'trace' || view === 'network');
  const scopes = $derived(app.scopes);
  const cross = $derived(crossLinks(app.loaded));
  /** One project, every project in turn ("*"), or only the links between projects ("~"). */
  const project = $derived.by(() => {
    const asked = app.route.query.get('project');
    if (asked === '*' && scopes.length > 1) return '*';
    if (asked === '~' && cross) return '~';
    if (asked && scopes.some((s) => s.scope === asked)) return asked;
    if (app.scope !== '*' && scopes.some((s) => s.scope === app.scope)) return app.scope;
    return scopes.length === 1 ? scopes[0].scope : scopes.length ? '*' : '*';
  });

  $effect(() => { if (app.route.param) selected = app.route.param; });
  $effect(() => { const key = preview.current?.key; if (key) selected = key; });

  /** Choosing an item lights its chain; choosing it again clears it. Reading it is the eye, below. */
  function pick(id: string | null) {
    selected = id;
  }
  const view_ = (key: string) => {
    selected = key;
    preview.openKey(key);
  };
  const setView = (v: View) => app.setQuery({ view: v === 'trace' ? null : v });
  const setProject = (p: string) => app.setQuery({ project: p });

  const single = $derived(project !== '*' && project !== '~' ? projectGraph(app.loaded, project) : null);
  const across = $derived(project === '~' ? acrossProjects(app.loaded) : null);
  const sections = $derived(project === '*' ? scopes.map((s) => ({ scope: s.scope, name: s.name, graph: projectGraph(app.loaded, s.scope) })) : []);
  const everything = $derived(scopedGraph(app.loaded, '*'));
  const shown = $derived(single ? { nodes: single.nodes, edges: single.edges } : (across ?? everything));
  const all = $derived(shown.nodes);
  const kinds = $derived([...new Set(all.map((n) => n.kind))].sort());
  const needle = $derived(text.trim().toLowerCase());
  const nodes = $derived(all.filter((n) => !hidden.has(n.kind) && (!needle || `${n.key} ${n.title}`.toLowerCase().includes(needle))).slice(0, LIMIT));
  const keys = $derived(new Set(nodes.map((n) => n.key)));
  const edges = $derived(shown.edges.filter((e) => keys.has(e.from) && keys.has(e.to) && (mentions || e.class !== 'mentioned')));
  const roots = $derived(buildTree(app.loaded, project === '*' || project === '~' ? '*' : project));
  const chainCount = $derived(all.filter((n) => n.kind in LEVEL_KINDS).length);
  const ghost = $derived(selected?.startsWith('gap:') ? selected : null);

  const tableCols: Col<Node>[] = [
    { id: 'key', label: 'Identifier', value: (n) => n.key, sortable: true },
    { id: 'kind', label: 'Kind', value: (n) => n.kind, sortable: true, facet: true, facetLabel: (v) => kindWords(v) },
    { id: 'status', label: 'Status', value: (n) => n.status, sortable: true, facet: true },
    { id: 'title', label: 'Title', value: (n) => n.title, sortable: true },
    { id: 'scope', label: 'Project', value: (n) => n.scope, facet: true, hidden: true },
  ];

  function toggle(kind: string) {
    const next = new Set(hidden);
    if (next.has(kind)) next.delete(kind); else next.add(kind);
    hidden = next;
  }
</script>

<PageHead title="Graph" lede="Outline and trace of goals, epics, features, acceptance criteria, tasks and code. Choose an item to light its whole chain; use the eye to read it.">
  {#snippet actions()}
    <div class="seg" role="group" aria-label="View">
      <button type="button" aria-pressed={view === 'trace'} onclick={() => setView('trace')}>Trace</button>
      <button type="button" aria-pressed={view === 'network'} onclick={() => setView('network')}>Network</button>
      <button type="button" aria-pressed={view === 'table'} onclick={() => setView('table')}>Table</button>
      <button type="button" aria-pressed={view === 'outline'} onclick={() => setView('outline')}>Outline</button>
    </div>
  {/snippet}
</PageHead>
{#if app.loaded.data.graph?.nodes.length}
  <div class="stack-sm">
    <div class="row-flex wrap gap-2">
      {#if scopes.length > 1 || cross}
        <select class="select" style:max-inline-size="18rem" aria-label="Project" value={project} onchange={(e) => setProject(e.currentTarget.value)}>
          {#each scopes as s (s.scope)}<option value={s.scope}>{s.name} ({s.scope})</option>{/each}
          {#if scopes.length > 1}<option value="*">Each project, separately</option>{/if}
          {#if cross}<option value="~">Links across projects ({cross})</option>{/if}
        </select>
      {/if}
      {#if view !== 'table' && view !== 'outline'}
        <input class="input" style:max-inline-size="18rem" type="search" placeholder="Find an item" aria-label="Find an item" bind:value={text} />
      {/if}
      {#if view === 'network'}
        {#each kinds as kind (kind)}
          <button class="pill" type="button" aria-pressed={!hidden.has(kind)} style:opacity={hidden.has(kind) ? 0.45 : 1} onclick={() => toggle(kind)}>
            <svg class="mk" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill={`oklch(58% 0.15 ${hue(kind)})`} /></svg>{kindWords(kind, true)}
          </button>
        {/each}
        <label class="row-flex"><input type="checkbox" bind:checked={mentions} /> Links that only mention an item</label>
      {/if}
      {#if view === 'trace'}
        <label class="row-flex"><input type="checkbox" bind:checked={code} /> Show code files that tasks change</label>
      {/if}
      {#if withOutline}
        <button class="btn ghost hide-narrow" type="button" aria-pressed={outlineOpen} onclick={() => (outlineOpen = !outlineOpen)}>{outlineOpen ? 'Hide outline' : 'Show outline'}</button>
      {/if}
    </div>
    {#if view === 'network' && all.length > LIMIT}<div class="banner warn">Showing the first {LIMIT} of {all.length} items. Narrow it with a filter.</div>{/if}
    {#if project === '~'}<p class="sub">Only links that join two projects, with the objectives, epics and features they join.</p>{/if}
    {#if ghost}
      <div class="card panel stack-sm">
        <h3>{app.loaded.data.graph?.nodes.find((n) => n.key === ghost)?.title ?? 'No link here'}</h3>
        <p class="sub">The data holds no link here. Ask the skill the placeholder names to add it; the console only reads.</p>
        <button class="btn" type="button" onclick={() => pick(null)}>Close</button>
      </div>
    {/if}

    <div class="graph-split" class:shut={!withOutline || !outlineOpen}>
      {#if withOutline}<aside class="outline-side" aria-label="Outline"><OutlinePane {roots} {selected} onpick={pick} onview={view_} /></aside>{/if}
      <div class="stack-sm">
        {#if view === 'outline'}
          <OutlinePane {roots} {selected} onpick={pick} onview={view_} />
        {:else if view === 'trace'}
          {#if project === '*'}
            {#each sections as s (s.scope)}
              <details class="project-section" open>
                <summary><h2>{s.name}</h2><span class="chip">{s.scope}</span></summary>
                <TraceView nodes={s.graph.nodes} edges={s.graph.edges} foreign={s.graph.foreign} {selected} onselect={pick} onview={view_} needle={text} {code} />
              </details>
            {/each}
          {:else if across}
            <TraceView nodes={across.nodes} edges={across.edges} {selected} onselect={pick} onview={view_} needle={text} {code} coverage={false} gaps={false} />
          {:else if single}
            <TraceView nodes={single.nodes} edges={single.edges} foreign={single.foreign} {selected} onselect={pick} onview={view_} needle={text} {code} />
          {/if}
        {:else if view === 'network'}
          {#if selected && !ghost}
            <div class="card pad row-flex wrap gap-2 picked-bar">
              <span class="sub">Chosen:</span><strong>{app.loaded.data.graph?.nodes.find((n) => n.key === selected)?.title ?? selected}</strong><span class="mono sub">{selected}</span>
              <span class="spacer"></span>
              <button class="btn" type="button" onclick={() => view_(selected!)}><Icon name="eye" size="sm" />View</button>
            </div>
          {/if}
          <div class="graph-wrap"><GraphCanvas {nodes} {edges} {selected} onselect={pick} /></div>
        {:else}
          <DataTable id="graph" rows={all} cols={tableCols} rowKey={(n) => n.key} title={(n) => n.key} template="minmax(0,1.4fr) 10rem 8rem minmax(0,2fr)" onrow={(n) => view_(n.key)}>
            {#snippet cells(n)}
              <span data-label="Kind" class="chip">{kindWords(n.kind)}</span>
              <span data-label="Status"><Pill look={wordLook(n.status)} /></span>
              <span data-label="Title">{n.title}</span>
            {/snippet}
          </DataTable>
        {/if}
      </div>
    </div>
    <p class="sub">Ask the graph a question in <a href={href('query')}><u>Query</u></a>. {chainCount} items in the chain.</p>
  </div>
{:else}
  <OwnerEmpty kind="graph" what="graph" />
{/if}
