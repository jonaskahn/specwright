<script lang="ts">
  import { getContext } from 'svelte';
  import type { Block, Span } from '../lib/markdown/parse';
  import { MD, type MdContext } from './md';
  import MdBlocks from './MdBlocks.svelte';
  import MdInline from './MdInline.svelte';

  let { blocks }: { blocks: Block[] } = $props();
  const md = getContext<MdContext>(MD);
  const marked = (s: Span) => !!md.hit && s.line >= md.hit[0] && s.end <= md.hit[1];
</script>

{#each blocks as b, n (n)}
  {#if b.t === 'heading'}
    <svelte:element this={`h${b.level}`} class="md-h" class:md-hit={marked(b)} id={`md-${b.id}`} data-line={b.line}><MdInline items={b.c} /></svelte:element>
  {:else if b.t === 'para'}
    <p class:md-hit={marked(b)} data-line={b.line}><MdInline items={b.c} /></p>
  {:else if b.t === 'list'}
    <svelte:element this={b.ordered ? 'ol' : 'ul'} class="md-list" data-line={b.line}>
      {#each b.items as it, k (k)}
        <li class:md-hit={marked(it)} class:md-task={it.checked !== null} data-line={it.line}>
          {#if it.checked !== null}<input type="checkbox" checked={it.checked} disabled aria-label={it.checked ? 'Done' : 'Not done'} />{/if}
          <div><MdBlocks blocks={it.c} /></div>
        </li>
      {/each}
    </svelte:element>
  {:else if b.t === 'quote'}
    <blockquote class:md-hit={marked(b)} data-line={b.line}><MdBlocks blocks={b.c} /></blockquote>
  {:else if b.t === 'code'}
    <pre class="md-code" class:md-hit={marked(b)} data-line={b.line}><code>{b.v}</code></pre>
  {:else if b.t === 'table'}
    <div class="md-table" class:md-hit={marked(b)} data-line={b.line}>
      <table>
        <thead><tr>{#each b.head as cell, c (c)}<th class={b.align[c] ?? ''}><MdInline items={cell} /></th>{/each}</tr></thead>
        <tbody>
          {#each b.rows as row, r (r)}
            <tr>{#each row as cell, c (c)}<td class={b.align[c] ?? ''}><MdInline items={cell} /></td>{/each}</tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if b.t === 'rule'}
    <hr />
  {:else}
    <pre class="md-raw" class:md-hit={marked(b)} data-line={b.line}>{b.v}</pre>
  {/if}
{/each}
