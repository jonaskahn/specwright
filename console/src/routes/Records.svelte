<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince, shortKey } from '../lib/format';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
  import type { Col } from '../lib/table';

  const NAMES: Record<string, string> = { q: 'Question', dec: 'Decision', cr: 'Change request', amendment: 'Amendment' };
  type Rec = (typeof app.records)[number];
  const cols: Col<Rec>[] = [
    { id: 'record', label: 'Record', value: (r) => r.id, sortable: true },
    { id: 'kind', label: 'Kind', value: (r) => r.kind, sortable: true, facet: true, facetLabel: (v) => NAMES[v] ?? v },
    { id: 'status', label: 'Status', value: (r) => r.status, sortable: true, facet: true },
    { id: 'affects', label: 'Affects', value: (r) => r.affects.map(shortKey).join(', ') || null },
    { id: 'updated', label: 'Updated', value: (r) => r.updated, sortable: true },
  ];
</script>

<PageHead title="Records" lede="Questions, decisions and change requests. Choose a row to read the record." />
{#if app.records.length}
  <DataTable id="records" rows={app.records} {cols} rowKey={(r) => r.id} title={(r) => shortKey(r.id)} sub={(r) => r.title} search={(r) => r.title} template="minmax(0,2fr) 8rem 7rem minmax(0,1.2fr) 6rem" onrow={(r) => preview.openKey(r.id)}>
    {#snippet cells(r)}
      <span data-label="Kind" class="chip">{NAMES[r.kind] ?? r.kind}</span>
      <span data-label="Status"><Pill look={wordLook(r.status)} /></span>
      <span data-label="Affects" class="row-flex wrap">{#each r.affects as a (a)}<a class="chip" href={href('features', a)}>{shortKey(a)}</a>{:else}<span class="muted">none</span>{/each}</span>
      <span data-label="Updated" class="muted">{ago(daysSince(r.updated, app.today))}</span>
    {/snippet}
  </DataTable>
{:else}
  <OwnerEmpty kind="records" what="record" />
{/if}
