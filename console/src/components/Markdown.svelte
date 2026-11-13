<script lang="ts">
  import { setContext, tick } from 'svelte';
  import { app } from '../lib/data/store.svelte';
  import { dirOf } from '../lib/markdown/links';
  import { findCriteria } from '../lib/markdown/criteria';
  import { findTasks } from '../lib/markdown/tasks';
  import { hitRange, parseInline, parseMarkdown, type OutlineEntry } from '../lib/markdown/parse';
  import { preview } from '../lib/preview.svelte';
  import { forFile, forKey } from '../lib/preview-target';
  import { MD, type MdContext } from './md';
  import Criteria from './Criteria.svelte';
  import Tasks from './Tasks.svelte';
  import MdBlocks from './MdBlocks.svelte';
  import MdInline from './MdInline.svelte';

  let {
    text,
    scope,
    path,
    line = 1,
    criteria = false,
    tasks = false,
    outline = $bindable<OutlineEntry[]>([]),
  }: { text: string; scope: string; path: string; line?: number; criteria?: boolean; tasks?: boolean; outline?: OutlineEntry[] } = $props();

  const doc = $derived(parseMarkdown(text));
  const hit = $derived(hitRange(doc, line > 1 ? line : 0));
  /** A story's criteria and a plan's tasks are drawn as cards or a table, with the front matter left to the Details tab; any other file is drawn as written. */
  const section = $derived(criteria ? findCriteria(doc) : null);
  const plan = $derived(tasks ? findTasks(doc) : null);
  let root = $state<HTMLElement | null>(null);

  function jump(id: string) {
    const slug = id.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').trim().replace(/\s+/g, '-');
    root?.querySelector(`[id="md-${slug}"]`)?.scrollIntoView({ block: 'start' });
  }

  const context: MdContext = {
    get scope() {
      return scope;
    },
    get dir() {
      return dirOf(path);
    },
    get hit() {
      return hit;
    },
    openDoc: (target) => preview.open(forFile(scope, target)),
    openRef: (id) => {
      const target = forKey(app.loaded, id.includes(':') ? id : `${scope}:${id}`) ?? forKey(app.loaded, id);
      if (target) preview.open(target);
    },
    jump,
  };
  setContext(MD, context);

  $effect(() => {
    outline = doc.outline;
  });
  $effect(() => {
    const marked = hit;
    void text;
    if (!marked) return;
    void tick().then(() => root?.querySelector('.md-hit')?.scrollIntoView({ block: 'start' }));
  });
</script>

<article class="md" bind:this={root}>
  {#if doc.meta && !section && !plan}
    <dl class="md-meta">
      {#each doc.meta as [name, value] (name)}
        <dt>{name}</dt>
        <dd>{#if value}<MdInline items={parseInline(value)} />{:else}<span class="muted">none</span>{/if}</dd>
      {/each}
    </dl>
  {/if}
  {#if section}
    <MdBlocks blocks={section.before} />
    <Criteria {section} />
    <MdBlocks blocks={section.after} />
  {:else if plan}
    <MdBlocks blocks={plan.before} />
    <Tasks section={plan} />
    <MdBlocks blocks={plan.after} />
  {:else}
    <MdBlocks blocks={doc.blocks} />
  {/if}
</article>
