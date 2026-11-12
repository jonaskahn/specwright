<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince } from '../lib/format';
  import { wordLook } from '../lib/status';
</script>

<PageHead title="Sources" lede="Imported material kept as evidence, with its age." />
{#if app.sources.length}
  <div class="ledger" style:--cols="minmax(0,2fr) 7rem 7rem 8rem minmax(0,1.5fr)">
    <div class="lhead"><span>Source</span><span>Kind</span><span>Status</span><span>Fetched</span><span>File</span></div>
    {#each app.sources as s (s.id)}
      <div class="lrow">
        <span><span class="name">{s.id.split(':')[1]}</span><div class="sub">{s.title}</div></span>
        <span data-label="Kind" class="chip">{s.kind}</span>
        <span data-label="Status"><Pill look={wordLook(s.status)} /></span>
        <span data-label="Fetched" class="muted">{ago(daysSince(s.fetchedAt, app.today))}</span>
        <span data-label="File" class="sub mono">{s.path ?? 'none'}</span>
      </div>
    {/each}
  </div>
{:else}
  <OwnerEmpty kind="sources" what="source" />
{/if}
