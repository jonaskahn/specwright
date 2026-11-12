<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { preview } from '../lib/preview.svelte';
  import { forKey } from '../lib/preview-target';
  import { wordLook } from '../lib/status';
  import type { Col } from '../lib/table';
  import { kindWords } from '../lib/vocabulary';

  type Entry = (typeof app.registry)[number];
  const cols: Col<Entry>[] = [
    { id: 'id', label: 'Identifier', value: (r) => r.id, sortable: true },
    { id: 'kind', label: 'Kind', value: (r) => r.kind, sortable: true, facet: true, facetLabel: (v) => kindWords(v) },
    { id: 'jira', label: 'Jira', value: (r) => r.jiraKey, sortable: true },
    { id: 'state', label: 'State', value: (r) => r.state, sortable: true, facet: true },
    { id: 'title', label: 'Title', value: (r) => r.title, sortable: true },
  ];
</script>

<PageHead title="Registry" lede="Every identifier the workspace has issued. Withdrawn identifiers stay listed and their numbers are never reused." />
{#if app.registry.length}
  <DataTable id="registry" rows={app.registry} {cols} rowKey={(r) => r.id} title={(r) => r.id} search={(r) => r.aliases.join(' ')} template="minmax(0,1.3fr) 6rem 8rem 8rem minmax(0,2fr)" canOpen={(r) => !!forKey(app.loaded, r.id)} onrow={(r) => preview.openKey(r.id)}>
    {#snippet cells(r)}
      <span data-label="Kind" class="chip">{r.kind ? kindWords(r.kind) : 'none'}</span>
      <span data-label="Jira">{r.jiraKey ?? 'none'}</span>
      <span data-label="State"><Pill look={wordLook(r.state)} /></span>
      <span data-label="Title">{r.title ?? 'none'}</span>
    {/snippet}
  </DataTable>
{:else}
  <OwnerEmpty kind="registry" what="registry" />
{/if}
