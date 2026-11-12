<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import Pill from './Pill.svelte';
  import { wordLook } from '../lib/status';

  let { nodeKey, onpick }: { nodeKey: string; onpick: (key: string) => void } = $props();
  const node = $derived(app.graph.node(nodeKey));
  const links = $derived(node ? app.graph.neighbors(nodeKey, 'both') : []);
  const isFeature = $derived(app.features.some((f) => f.id === nodeKey));
</script>

{#if node}
  <div class="card panel">
    <div>
      <h3>{node.title}</h3>
      <p class="sub mono">{node.key}</p>
    </div>
    <dl>
      <dt>Kind</dt><dd>{node.kind}</dd>
      <dt>Status</dt><dd><Pill look={wordLook(node.status)} /></dd>
      {#if node.station}<dt>Station</dt><dd>{node.station}{node.condition ? ` · ${node.condition}` : ''}</dd>{/if}
      {#if node.jira}<dt>Jira</dt><dd>{node.jira}</dd>{/if}
      {#if node.path}<dt>File</dt><dd class="mono">{node.path}{node.line ? `:${node.line}` : ''}</dd>{/if}
      {#if node.aliases.length}<dt>Aliases</dt><dd>{node.aliases.join(', ')}</dd>{/if}
    </dl>
    {#if isFeature}<a class="btn" href={href('features', nodeKey)}>Open feature</a>{/if}
    <div>
      <p class="sub">{links.length} link{links.length === 1 ? '' : 's'}</p>
      <div class="linklist">
        {#each links.slice(0, 30) as l, i (i)}
          <button type="button" onclick={() => onpick(l.other)}>{l.side === 'out' ? '→' : '←'} {l.rel} {l.other}</button>
        {/each}
      </div>
    </div>
  </div>
{/if}
