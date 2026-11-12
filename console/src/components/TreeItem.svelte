<script lang="ts">
  import type { TreeNode } from '../lib/data/selectors';
  import { wordLook } from '../lib/status';
  import { href } from '../lib/router';
  import { kindWords } from '../lib/vocabulary';
  import Mark from './Mark.svelte';
  import TreeItem from './TreeItem.svelte';
  let { node, depth = 0 }: { node: TreeNode; depth?: number } = $props();
  const look = $derived(wordLook(node.status));
  const link = $derived(node.kind === 'feat' ? href('features', node.key) : node.kind === 'project' || node.kind === 'gap' ? null : href('graph', node.key));
</script>

{#if node.children.length}
  <details open={depth < 4}>
    <summary>
      <span class="kind">{kindWords(node.kind)}</span>
      {#if node.status}<Mark shape={look.shape} />{/if}
      {#if link}<a class="name" href={link}>{node.title}</a>{:else}<span class="name">{node.title}</span>{/if}
      {#if node.kind !== 'gap'}<span class="sub mono">{node.key}</span>{/if}
    </summary>
    <ul>
      {#each node.children as child (child.key)}
        <li><TreeItem node={child} depth={depth + 1} /></li>
      {/each}
    </ul>
  </details>
{:else}
  <svelte:element this={link ? 'a' : 'div'} class="leaf" href={link ?? undefined}>
    <span class="kind">{kindWords(node.kind)}</span>
    {#if node.status}<Mark shape={look.shape} />{/if}
    <span class="name">{node.title}</span>
    {#if node.kind !== 'gap'}<span class="sub mono">{node.key}</span>{/if}
  </svelte:element>
{/if}
