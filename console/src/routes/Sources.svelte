<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince, shortKey } from '../lib/format';
  import { preview } from '../lib/preview.svelte';
  import { forKey } from '../lib/preview-target';
  import { wordLook } from '../lib/status';
  import type { Col } from '../lib/table';

  type Source = (typeof app.sources)[number];
  const cols: Col<Source>[] = [
    { id: 'source', label: 'Source', value: (s) => s.id, sortable: true },
    { id: 'kind', label: 'Kind', value: (s) => s.kind, sortable: true, facet: true },
    { id: 'status', label: 'Status', value: (s) => s.status, sortable: true, facet: true },
    { id: 'fetched', label: 'Fetched', value: (s) => s.fetchedAt, sortable: true },
    { id: 'file', label: 'File', value: (s) => s.path },
  ];
</script>

<PageHead title="Sources" lede="Imported material kept as evidence, with its age. Choose a row to read it." />
{#if app.sources.length}
  <DataTable id="sources" rows={app.sources} {cols} rowKey={(s) => s.id} title={(s) => shortKey(s.id)} sub={(s) => s.title} search={(s) => s.title} template="minmax(0,2fr) 7rem 7rem 8rem minmax(0,1.5fr)" canOpen={(s) => !!forKey(app.loaded, s.id)} onrow={(s) => preview.openKey(s.id)}>
    {#snippet cells(s)}
      <span data-label="Kind" class="chip">{s.kind}</span>
      <span data-label="Status"><Pill look={wordLook(s.status)} /></span>
      <span data-label="Fetched" class="muted">{ago(daysSince(s.fetchedAt, app.today))}</span>
      <span data-label="File" class="sub mono">{s.path ?? 'none'}</span>
    {/snippet}
  </DataTable>
{:else}
  <OwnerEmpty kind="sources" what="source" />
{/if}
