<script lang="ts">
  import { getContext } from 'svelte';
  import { imageUrl, resolveLink } from '../lib/markdown/links';
  import type { Inline } from '../lib/markdown/parse';
  import { MD, type MdContext } from './md';
  import MdInline from './MdInline.svelte';

  let { items }: { items: Inline[] } = $props();
  const md = getContext<MdContext>(MD);
</script>

{#each items as item, n (n)}
  {#if item.t === 'text'}{item.v}
  {:else if item.t === 'code'}<code>{item.v}</code>
  {:else if item.t === 'em'}<em><MdInline items={item.c} /></em>
  {:else if item.t === 'strong'}<strong><MdInline items={item.c} /></strong>
  {:else if item.t === 'ref'}<button class="md-ref mono" type="button" onclick={() => md.openRef(item.id)}>{item.id}</button>
  {:else if item.t === 'image'}
    {@const src = imageUrl(md.scope, md.dir, item.src)}
    {@const full = resolveLink(item.src, md.dir)}
    {#if src && full.kind === 'doc'}
      <button class="md-picture" type="button" title="Open the picture full size" onclick={() => md.openDoc(full.path)}><img class="md-img" {src} alt={item.alt} loading="lazy" /></button>
    {:else if src}<img class="md-img" {src} alt={item.alt} loading="lazy" />{:else}<span class="muted">[{item.alt || 'image'}]</span>{/if}
  {:else if item.t === 'link'}
    {@const target = resolveLink(item.href, md.dir)}
    {#if target.kind === 'external'}<a class="md-link" href={target.href} target="_blank" rel="noopener noreferrer"><MdInline items={item.c} /></a>
    {:else if target.kind === 'doc'}<button class="md-link" type="button" onclick={() => md.openDoc(target.path)}><MdInline items={item.c} /></button>
    {:else if target.kind === 'anchor'}<button class="md-link" type="button" onclick={() => md.jump(target.id)}><MdInline items={item.c} /></button>
    {:else}<MdInline items={item.c} />{/if}
  {/if}
{/each}
