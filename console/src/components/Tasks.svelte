<script lang="ts">
  import { getContext } from 'svelte';
  import { slide } from 'svelte/transition';
  import { app } from '../lib/data/store.svelte';
  import { LABELS, type Task, type TaskSection } from '../lib/markdown/tasks';
  import { ms } from '../lib/motion';
  import Icon from './Icon.svelte';
  import ListBar from './ListBar.svelte';
  import { MD, type MdContext } from './md';
  import MdBlocks from './MdBlocks.svelte';
  import MdInline from './MdInline.svelte';
  import StepText from './StepText.svelte';

  let { section }: { section: TaskSection } = $props();
  const md = getContext<MdContext>(MD);

  let filter = $state('all');
  let open = $state<Record<string, boolean>>({});

  const items = $derived(section.items);
  const NONE = 'other';
  const layerOf = (t: Task) => t.layer ?? NONE;
  const layers = $derived([...new Set(items.map(layerOf))]);
  const active = $derived(filter !== 'all' && layers.includes(filter) ? filter : 'all');
  const shown = $derived(active === 'all' ? items : items.filter((t) => layerOf(t) === active));
  const everyOpen = $derived(shown.length > 0 && shown.every((t) => open[t.id]));
  const hitId = $derived(items.find((t) => md.hit && md.hit[0] >= t.line && md.hit[0] <= t.end)?.id ?? null);
  const view = $derived(app.prefs.listView);
  const word = (layer: string) => (layer === NONE ? 'Other' : layer[0].toUpperCase() + layer.slice(1));
  const count = (layer: string) => items.filter((t) => layerOf(t) === layer).length;
  const heldBy = (t: Task) => !!md.hit && md.hit[0] >= t.line && md.hit[0] <= t.end;
  /** A value of "None" says nothing, so it is left out of a card. */
  const said = (t: Task, key: (typeof LABELS)[number][0]) => {
    const v = t.fields[key];
    return v && v.length > 0 && !(v.length === 1 && v[0].t === 'text' && /^none\.?$/i.test(v[0].v.trim())) ? v : null;
  };

  // A task that was asked for opens (the document scrolls to it); otherwise the first one does.
  $effect(() => {
    const first = hitId ?? items[0]?.id;
    open = first ? { [first]: true } : {};
  });

  const toggle = (t: Task) => (open[t.id] = !open[t.id]);
  const setAll = () => {
    const next = !everyOpen;
    for (const t of shown) open[t.id] = next;
  };
</script>

<section class="ac">
  <div class="ac-title">
    <h2 class="md-h" id="md-tasks">Tasks</h2>
    <span class="ac-count">{items.length}</span>
  </div>
  {#if section.lead.length}<MdBlocks blocks={section.lead} />{/if}

  <ListBar
    chips={[{ key: 'all', label: 'All', count: items.length }, ...layers.map((l) => ({ key: l, label: word(l), count: count(l) }))]}
    {active}
    onpick={(k) => (filter = k)}
    what="tasks"
    expand={everyOpen ? 'Collapse all' : 'Expand all'}
    onexpand={setAll}
  />

  {#if view === 'cards'}
    <div class="ac-list">
      {#each shown as t (t.id)}
        <article class="ac-card" class:md-hit={heldBy(t)} data-line={t.line}>
          <button class="ac-head" type="button" aria-expanded={!!open[t.id]} onclick={() => toggle(t)}>
            <span class="ac-chev" class:open={open[t.id]}><Icon name="chevron" /></span>
            <span class="ac-id">{t.id}</span>
            <span class="ac-name">{t.title}</span>
            {#if t.parallel}<span class="ac-bg" title="Can run in parallel with the tasks around it">Parallel</span>{/if}
            {#if t.layer}<span class="pill neutral">{word(t.layer)}</span>{/if}
          </button>
          {#if open[t.id]}
            <div class="ac-body" transition:slide={{ duration: ms(180) }}>
              {#each LABELS as [key, label] (key)}
                {@const v = said(t, key)}
                {#if v}
                  <p class="tk-row" class:tk-done={key === 'done'}><span class="tk-label">{label}</span><span class="ac-text"><StepText items={v} /></span></p>
                {/if}
              {/each}
              {#if t.rest.length}<div class="md"><MdBlocks blocks={t.rest} /></div>{/if}
            </div>
          {/if}
        </article>
      {/each}
    </div>
  {:else}
    <div class="ac-table">
      <table>
        <thead><tr><th>Task</th><th>Traces to</th><th>Depends on</th><th>Done when</th></tr></thead>
        <tbody>
          {#each shown as t (t.id)}
            <tr class:md-hit={heldBy(t)} data-line={t.line}>
              <td>
                <span class="ac-id">{t.id}</span><strong>{t.title}</strong>
                {#if t.layer}<span class="pill neutral">{word(t.layer)}</span>{/if}
              </td>
              <td>{#if said(t, 'traces')}<MdInline items={t.fields.traces!} />{/if}</td>
              <td>{#if said(t, 'depends')}<MdInline items={t.fields.depends!} />{:else}<span class="ac-dim">None</span>{/if}</td>
              <td>
                {#if said(t, 'done')}<p><StepText items={t.fields.done!} /></p>{/if}
                {#if said(t, 'stop')}<p class="ac-dim">Stop and ask if: <StepText items={t.fields.stop!} /></p>{/if}
                {#if t.rest.length && !said(t, 'done')}<MdBlocks blocks={t.rest} />{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
