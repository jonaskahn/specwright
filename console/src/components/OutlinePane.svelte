<script lang="ts">
  import { filterTree, pathTo, type TreeNode } from '../lib/data/selectors';
  import OutlineNode from './OutlineNode.svelte';

  let { roots, selected, onpick }: { roots: TreeNode[]; selected: string | null; onpick: (key: string) => void } = $props();

  let text = $state('');
  let expand = $state<'auto' | 'all' | 'none'>('auto');
  let pane = $state<HTMLElement | null>(null);

  const shown = $derived(roots.map((r) => filterTree(r, text)).filter((r): r is TreeNode => !!r));
  /** Everything above the chosen item, so it is never hidden inside a closed branch. */
  const forced = $derived.by(() => {
    const out = new Set<string>();
    if (text.trim()) for (const r of shown) for (const k of keys(r)) out.add(k);
    if (selected) for (const r of roots) for (const k of pathTo(r, selected) ?? []) out.add(k);
    return out;
  });
  function keys(node: TreeNode): string[] {
    return node.children.length ? [node.key, ...node.children.flatMap(keys)] : [];
  }

  $effect(() => {
    const key = selected;
    if (!key) return;
    queueMicrotask(() => pane?.querySelector(`[data-key="${CSS.escape(key)}"]`)?.scrollIntoView({ block: 'nearest' }));
  });
</script>

<div class="outline" bind:this={pane}>
  <div class="row-flex wrap gap-2">
    <input class="input" type="search" placeholder="Find in the outline" aria-label="Find in the outline" bind:value={text} />
    <button class="btn ghost" type="button" onclick={() => (expand = 'all')}>Expand all</button>
    <button class="btn ghost" type="button" onclick={() => (expand = 'none')}>Collapse all</button>
  </div>
  <div class="o-tree">
    {#each shown as root (root.key)}<OutlineNode node={root} {selected} {expand} {forced} {onpick} />{:else}<p class="muted">Nothing matches.</p>{/each}
  </div>
</div>
