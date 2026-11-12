<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { wordLook } from '../lib/status';

  let text = $state('');
  const shown = $derived(app.registry.filter((r) => !text.trim() || `${r.id} ${r.title ?? ''} ${r.jiraKey ?? ''} ${r.aliases.join(' ')}`.toLowerCase().includes(text.trim().toLowerCase())));
</script>

<PageHead title="Registry" lede="Every ID the workspace has issued. Withdrawn IDs stay listed and their numbers are never reused." />
{#if app.registry.length}
  <div class="stack-sm">
    <input class="input" style:max-inline-size="20rem" type="search" placeholder="Filter by ID, title or Jira key" aria-label="Filter the registry" bind:value={text} />
    <div class="ledger" style:--cols="minmax(0,1.3fr) 6rem 8rem 8rem minmax(0,2fr)">
      <div class="lhead"><span>ID</span><span>Kind</span><span>Jira</span><span>State</span><span>Title</span></div>
      {#each shown as r (r.id)}
        <div class="lrow">
          <span class="name mono">{r.id}</span><span data-label="Kind" class="chip">{r.kind ?? 'none'}</span>
          <span data-label="Jira">{r.jiraKey ?? 'none'}</span><span data-label="State"><Pill look={wordLook(r.state)} /></span>
          <span data-label="Title">{r.title ?? 'none'}</span>
        </div>
      {/each}
    </div>
  </div>
{:else}
  <OwnerEmpty kind="registry" what="registry" />
{/if}
