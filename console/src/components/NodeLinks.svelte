<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { classWords, relationWords, resolutionWords } from '../lib/vocabulary';

  let { nodeKey, onpick }: { nodeKey: string; onpick: (key: string) => void } = $props();
  const links = $derived(app.graph.node(nodeKey) ? app.graph.neighbors(nodeKey, 'both') : []);
  /** Links grouped by what they say, so a feature reads "Has acceptance criterion (3)". */
  const groups = $derived.by(() => {
    const out = new Map<string, { rel: string; side: 'out' | 'in'; items: typeof links }>();
    for (const l of links) {
      const id = `${l.side}:${l.rel}`;
      if (!out.has(id)) out.set(id, { rel: l.rel, side: l.side, items: [] });
      out.get(id)!.items.push(l);
    }
    return [...out.values()].sort((a, b) => (a.rel === 'mentions' ? 1 : 0) - (b.rel === 'mentions' ? 1 : 0) || a.rel.localeCompare(b.rel));
  });
</script>

<div class="stack-sm">
  <p class="sub">{links.length} link{links.length === 1 ? '' : 's'}</p>
  {#each groups as g (g.side + g.rel)}
    <div>
      <p class="sub group-h"><strong>{relationWords(g.rel, g.side)}</strong> ({g.items.length})</p>
      <div class="linklist">
        {#each g.items.slice(0, 40) as l, i (i)}
          <button type="button" title={`${classWords(l.cls)}. ${resolutionWords(l.res)}.`} onclick={() => onpick(l.other)}>
            <strong>{app.graph.node(l.other)?.title ?? l.other}</strong>
            {#if l.rel === 'touches'}<span>{resolutionWords(l.res)}</span>{:else}<span class="mono">{l.other}</span>{/if}
          </button>
        {/each}
      </div>
    </div>
  {/each}
</div>
