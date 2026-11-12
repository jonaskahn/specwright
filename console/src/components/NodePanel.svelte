<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import Pill from './Pill.svelte';
  import { wordLook } from '../lib/status';
  import { classWords, kindWords, relationWords, resolutionWords, stationWords } from '../lib/vocabulary';

  let { nodeKey, onpick }: { nodeKey: string; onpick: (key: string) => void } = $props();
  const node = $derived(app.graph.node(nodeKey));
  const links = $derived(node ? app.graph.neighbors(nodeKey, 'both') : []);
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
  const isFeature = $derived(app.features.some((f) => f.id === nodeKey));
</script>

{#if node}
  <div class="card panel">
    <div>
      <h3>{node.title}</h3>
      <p class="sub mono">{node.key}</p>
    </div>
    <dl>
      <dt>Kind</dt><dd>{kindWords(node.kind)}</dd>
      <dt>Status</dt><dd><Pill look={wordLook(node.status)} /></dd>
      {#if node.station}<dt>Station</dt><dd>{stationWords(node.station)}{node.condition ? ` · ${node.condition.replace(/-/g, ' ')}` : ''}</dd>{/if}
      {#if node.jira}<dt>Jira</dt><dd>{node.jira}</dd>{/if}
      {#if node.path}<dt>File</dt><dd class="mono">{node.path}{node.line ? `:${node.line}` : ''}</dd>{/if}
      {#if node.aliases.length}<dt>Aliases</dt><dd>{node.aliases.join(', ')}</dd>{/if}
    </dl>
    {#if isFeature}<a class="btn" href={href('features', nodeKey)}>Open feature</a>{/if}
    <div class="stack-sm">
      <p class="sub">{links.length} link{links.length === 1 ? '' : 's'}</p>
      {#each groups as g (g.side + g.rel)}
        <div>
          <p class="sub group-h"><strong>{relationWords(g.rel, g.side)}</strong> ({g.items.length})</p>
          <div class="linklist">
            {#each g.items.slice(0, 20) as l, i (i)}
              <button type="button" title={`${classWords(l.cls)}. ${resolutionWords(l.res)}.`} onclick={() => onpick(l.other)}>
                <strong>{app.graph.node(l.other)?.title ?? l.other}</strong>
                <span class="mono">{l.other}</span>
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  </div>
{/if}
