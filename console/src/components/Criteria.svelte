<script lang="ts">
  import { getContext } from 'svelte';
  import { slide } from 'svelte/transition';
  import { app } from '../lib/data/store.svelte';
  import { columns, type Criterion, type Section, type Step, type Tag } from '../lib/markdown/criteria';
  import { ms } from '../lib/motion';
  import Icon from './Icon.svelte';
  import ListBar from './ListBar.svelte';
  import { MD, type MdContext } from './md';
  import MdBlocks from './MdBlocks.svelte';
  import StepText from './StepText.svelte';

  let { section }: { section: Section } = $props();
  const md = getContext<MdContext>(MD);

  const TAGS: Record<Tag, { label: string; tone: string }> = {
    happy: { label: 'Happy path', tone: 'ok' },
    validation: { label: 'Validation', tone: 'warn' },
    ui: { label: 'Interface rule', tone: 'accent' },
    other: { label: 'Free text', tone: 'neutral' },
  };
  const ORDER: Tag[] = ['happy', 'validation', 'ui', 'other'];

  let filter = $state<Tag | 'all'>('all');
  let open = $state<Record<string, boolean>>({});

  const items = $derived(section.items);
  const present = $derived(ORDER.filter((t) => items.some((c) => c.tag === t)));
  const active = $derived(filter !== 'all' && present.includes(filter) ? filter : 'all');
  const shown = $derived(active === 'all' ? items : items.filter((c) => c.tag === active));
  const everyOpen = $derived(shown.length > 0 && shown.every((c) => open[c.id]));
  const hitId = $derived(items.find((c) => md.hit && md.hit[0] >= c.line && md.hit[0] <= c.end)?.id ?? null);
  const ruled = $derived(section.background && shown.some((c) => c.background) ? section.background : null);
  const view = $derived(app.prefs.listView);

  // A criterion that was asked for opens (the document scrolls to it); otherwise the first one does, so the panel is never all closed.
  $effect(() => {
    const first = hitId ?? items[0]?.id;
    open = first ? { [first]: true } : {};
  });

  const count = (t: Tag | 'all') => (t === 'all' ? items.length : items.filter((c) => c.tag === t).length);
  const toggle = (c: Criterion) => (open[c.id] = !open[c.id]);
  const setAll = () => {
    const next = !everyOpen;
    for (const c of shown) open[c.id] = next;
  };
  const kwClass = (s: Step) => `ac-kw ${s.kw.toLowerCase()}`;
  const heldBy = (c: Criterion) => !!md.hit && md.hit[0] >= c.line && md.hit[0] <= c.end;
</script>

<section class="ac">
  <div class="ac-title">
    <h2 class="md-h" id="md-acceptance-criteria">Acceptance criteria</h2>
    <span class="ac-count">{items.length}</span>
  </div>
  {#if section.lead.length}<MdBlocks blocks={section.lead} />{/if}

  <ListBar
    chips={[{ key: 'all', label: 'All', count: items.length }, ...present.map((t) => ({ key: t, label: TAGS[t].label, count: count(t) }))]}
    active={active}
    onpick={(k) => (filter = k as Tag | 'all')}
    what="criteria"
    expand={everyOpen ? 'Collapse all' : 'Expand all'}
    onexpand={setAll}
  />

  {#if ruled}
    <div class="ac-background">
      <p class="ac-eyebrow">Background <span>applies to {ruled.ids.filter((id) => shown.some((c) => c.id === id)).join(', ')}</span></p>
      <p class="ac-step"><span class={kwClass(ruled.step)}>{ruled.step.kw}</span><span class="ac-text"><StepText items={ruled.step.c} /></span></p>
    </div>
  {/if}

  {#if view === 'cards'}
    <div class="ac-list">
      {#each shown as c (c.id)}
        <article class="ac-card" class:md-hit={heldBy(c)} data-line={c.line}>
          <button class="ac-head" type="button" aria-expanded={!!open[c.id]} onclick={() => toggle(c)}>
            <span class="ac-chev" class:open={open[c.id]}><Icon name="chevron" /></span>
            <span class="ac-id">{c.id}</span>
            <span class="ac-name">{c.title}</span>
            {#if c.background}<span class="ac-bg">Background</span>{/if}
            <span class="pill {TAGS[c.tag].tone}">{TAGS[c.tag].label}</span>
          </button>
          {#if open[c.id]}
            <div class="ac-body" transition:slide={{ duration: ms(180) }}>
              {#each c.steps as s, n (n)}
                <p class="ac-step"><span class={kwClass(s)}>{s.kw}</span><span class="ac-text"><StepText items={s.c} /></span></p>
              {/each}
              {#if c.rest.length}<div class="md"><MdBlocks blocks={c.rest} /></div>{/if}
            </div>
          {/if}
        </article>
      {/each}
    </div>
  {:else}
    <div class="ac-table">
      <table>
        <thead><tr><th>Criterion</th><th>Given</th><th>When</th><th>Then</th></tr></thead>
        <tbody>
          {#each shown as c (c.id)}
            {@const cols = columns(c.steps)}
            <tr class:md-hit={heldBy(c)} data-line={c.line}>
              <td><span class="ac-id">{c.id}</span><strong>{c.title}</strong></td>
              <td>
                {#if c.background}<span class="ac-dim">Background</span>{/if}
                {#each cols.given as s, n (n)}<p><StepText items={s.c} /></p>{/each}
              </td>
              <td>{#each cols.when as s, n (n)}<p><StepText items={s.c} /></p>{/each}</td>
              <td>
                {#each cols.then as s, n (n)}<p>{#if s.kw !== 'Then'}<span class="ac-and">{s.kw} </span>{/if}<StepText items={s.c} /></p>{/each}
                {#if cols.given.length + cols.when.length + cols.then.length === 0 && c.rest.length}<MdBlocks blocks={c.rest} />{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
