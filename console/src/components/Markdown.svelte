<script lang="ts">
  import { setContext, tick } from 'svelte';
  import { app } from '../lib/data/store.svelte';
  import { dirOf } from '../lib/markdown/links';
  import { hitRange, parseInline, parseMarkdown, type OutlineEntry } from '../lib/markdown/parse';
  import { preview } from '../lib/preview.svelte';
  import { forFile, forKey } from '../lib/preview-target';
  import { MD, type MdContext } from './md';
  import MdBlocks from './MdBlocks.svelte';
  import MdInline from './MdInline.svelte';

  let {
    text,
    scope,
    path,
    line = 1,
    outline = $bindable<OutlineEntry[]>([]),
  }: { text: string; scope: string; path: string; line?: number; outline?: OutlineEntry[] } = $props();

  const doc = $derived(parseMarkdown(text));
  const hit = $derived(hitRange(doc, line > 1 ? line : 0));
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
  {#if doc.meta}
    <dl class="md-meta">
      {#each doc.meta as [name, value] (name)}
        <dt>{name}</dt>
        <dd>{#if value}<MdInline items={parseInline(value)} />{:else}<span class="muted">none</span>{/if}</dd>
      {/each}
    </dl>
  {/if}
  <MdBlocks blocks={doc.blocks} />
</article>
