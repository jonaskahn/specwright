<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import TreeItem from '../components/TreeItem.svelte';
  import { app } from '../lib/data/store.svelte';
  import { buildTree } from '../lib/data/selectors';

  const roots = $derived(buildTree(app.loaded, app.scope));
</script>

<PageHead title="Tree" lede="Project, epic, feature, criterion and task, as the graph links them." />
{#if roots.some((r) => r.children.length)}
  <div class="card pad tree">
    {#each roots as root (root.key)}<TreeItem node={root} />{/each}
  </div>
{:else}
  <OwnerEmpty kind="graph" what="graph" />
{/if}
