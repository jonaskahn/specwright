<script lang="ts">
  import { filterTree, pathTo, type TreeNode } from '../lib/data/selectors';
  import OutlineNode from './OutlineNode.svelte';

  let { roots, selected, onpick, onview }: { roots: TreeNode[]; selected: string | null; onpick: (key: string) => void; onview: (key: string) => void } = $props();

  let text = $state('');
  let expand = $state<'auto' | 'all' | 'none'>('auto');
  /** Branches opened or closed by hand. A new choice clears them, so only the chosen item stays open. */
  let marks = $state(new Map<string, boolean>());
  let pane = $state<HTMLElement | null>(null);

  const shown = $derived(roots.map((r) => filterTree(r, text)).filter((r): r is TreeNode => !!r));
  /** Everything above the chosen item, and the item itself, so a chosen feature shows its own criteria and tasks. */
  const forced = $derived.by(() => {
    const out = new Set<string>();
    if (text.trim()) for (const r of shown) for (const k of keys(r)) out.add(k);
    if (selected) {
      for (const r of roots) {
        const trail = pathTo(r, selected);
        if (trail) for (const k of [...trail, selected]) out.add(k);
      }
    }
    return out;
  });
  function keys(node: TreeNode): string[] {
    return node.children.length ? [node.key, ...node.children.flatMap(keys)] : [];
  }

  $effect(() => {
    void selected;
    marks = new Map();
  });
  const mark = (key: string, open: boolean) => (marks = new Map(marks).set(key, open));
  const all = (to: 'all' | 'none') => {
    marks = new Map();
    expand = to;
  };

  $effect(() => {
    const key = selected;
    if (!key) return;
    queueMicrotask(() => pane?.querySelector(`[data-key="${CSS.escape(key)}"]`)?.scrollIntoView({ block: 'nearest' }));
  });
</script>

<div class="outline" bind:this={pane}>
  <div class="row-flex wrap gap-2">
    <input class="input" type="search" placeholder="Find in the outline" aria-label="Find in the outline" bind:value={text} />
    <button class="btn ghost" type="button" onclick={() => all('all')}>Expand all</button>
    <button class="btn ghost" type="button" onclick={() => all('none')}>Collapse all</button>
  </div>
  <div class="o-tree">
    {#each shown as root (root.key)}<OutlineNode node={root} {selected} {expand} {forced} {marks} onmark={mark} {onpick} {onview} />{:else}<p class="muted">Nothing matches.</p>{/each}
  </div>
</div>
