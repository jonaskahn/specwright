<script lang="ts">
  import type { TreeNode } from '../lib/data/selectors';
  import { wordLook } from '../lib/status';
  import { kindWords } from '../lib/vocabulary';
  import Icon from './Icon.svelte';
  import Mark from './Mark.svelte';
  import OutlineNode from './OutlineNode.svelte';

  let {
    node,
    depth = 0,
    selected = null,
    expand,
    forced,
    onpick,
    onview,
  }: {
    node: TreeNode;
    depth?: number;
    selected?: string | null;
    /** 'auto' opens project and epic and leaves each feature closed; 'all' and 'none' are the buttons above the tree. */
    expand: 'auto' | 'all' | 'none';
    /** Keys that must be open so the chosen item is visible. */
    forced: Set<string>;
    onpick: (key: string) => void;
    onview: (key: string) => void;
  } = $props();

  const look = $derived(wordLook(node.status));
  /** A branch the person opened by hand with its arrow. */
  let byHand = $state(false);
  const open = $derived(expand === 'all' || forced.has(node.key) || (expand === 'auto' && depth < 2));
  const pickable = $derived(node.kind !== 'gap' && node.kind !== 'project');
  const SHORT: Record<string, string> = { bo: 'Objective', epic: 'Epic', feat: 'Feature', ac: 'Criterion', task: 'Task', project: 'Project' };
  const label = $derived(node.kind === 'gap' ? node.title : (SHORT[node.kind] ?? kindWords(node.kind)));
</script>

{#snippet row()}
  <span class="o-kind">{label}</span>
  {#if node.status}<Mark shape={look.shape} />{/if}
  <span class="o-name">{node.kind === 'gap' ? '' : node.title}</span>
  {#if node.foreign}<span class="chip">{node.foreign}</span>{/if}
  {#if node.counts}<span class="o-count" title="Criteria and tasks">{node.counts.ac} {node.counts.ac === 1 ? 'criterion' : 'criteria'} · {node.counts.task} {node.counts.task === 1 ? 'task' : 'tasks'}</span>{/if}
{/snippet}

{#snippet eye()}
  {#if pickable && node.kind !== 'code'}<button class="o-eye" type="button" aria-label={`View ${node.title}`} title="View" onclick={() => onview(node.key)}><Icon name="eye" size="sm" /></button>{/if}
{/snippet}

{#if node.children.length}
  <details {open} ontoggle={(e) => (byHand = e.currentTarget.open)}>
    <summary class:picked={selected === node.key} data-key={node.key}>
      <span class="o-chev" aria-hidden="true"></span>
      {#if pickable}<button class="o-row" type="button" aria-current={selected === node.key ? 'true' : undefined} onclick={(e) => { e.preventDefault(); onpick(node.key); }}>{@render row()}</button>{:else}<span class="o-row">{@render row()}</span>{/if}
      {@render eye()}
    </summary>
    <!-- A closed branch draws nothing below it, so a thousand criteria cost nothing until a feature is opened. -->
    {#if open || byHand}
      <ul>
        {#each node.children as child (child.key)}
          <li><OutlineNode node={child} depth={depth + 1} {selected} {expand} {forced} {onpick} {onview} /></li>
        {/each}
      </ul>
    {/if}
  </details>
{:else if pickable}
  <div class="o-line" class:picked={selected === node.key} data-key={node.key}>
    <button class="o-row leaf" type="button" aria-current={selected === node.key ? 'true' : undefined} onclick={() => onpick(node.key)}>{@render row()}</button>
    {@render eye()}
  </div>
{:else}
  <div class="o-row leaf">{@render row()}</div>
{/if}
