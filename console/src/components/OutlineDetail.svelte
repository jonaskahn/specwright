<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
  import { kindWords } from '../lib/vocabulary';
  import Icon from './Icon.svelte';
  import NodeLinks from './NodeLinks.svelte';
  import Pill from './Pill.svelte';

  let { selected, onpick, onview }: { selected: string | null; onpick: (key: string | null) => void; onview: (key: string) => void } = $props();
  const node = $derived(selected ? app.graph.node(selected) : undefined);
  const feature = $derived(selected ? app.features.find((f) => f.id === selected) : undefined);
</script>

{#if node && selected}
  <section class="card pad stack-sm outline-detail" aria-label="Chosen item">
    <div class="row-flex wrap">
      <div>
        <p class="sub">{kindWords(node.kind)} · <span class="mono">{selected}</span></p>
        <h2>{node.title}</h2>
      </div>
      <span class="spacer"></span>
      <button class="btn" type="button" onclick={() => onview(selected)}><Icon name="eye" size="sm" />View</button>
      {#if feature}<a class="btn" href={href('features', feature.id)}>Open feature</a>{/if}
      <a class="btn" href={href('graph', selected)}>Show in trace</a>
    </div>
    <div class="row-flex wrap">
      <Pill look={wordLook(node.status)} />
      {#if node.scope && app.scopes.length > 1}<span class="chip">{node.scope}</span>{/if}
      {#if node.path}<span class="sub mono">{node.path}{node.line > 1 ? `:${node.line}` : ''}</span>{/if}
    </div>
    <NodeLinks nodeKey={selected} onpick={(key) => onpick(key)} />
  </section>
{:else}
  <div class="empty"><h3>Choose an item in the outline</h3><p class="muted">Its links, its status and where it lives appear here. The eye opens its file.</p></div>
{/if}
