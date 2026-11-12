<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { shortKey } from '../lib/format';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
  import type { Col } from '../lib/table';

  type Task = (typeof app.tasks)[number];
  const cols: Col<Task>[] = [
    { id: 'task', label: 'Task', value: (t) => t.id, sortable: true },
    { id: 'feature', label: 'Feature', value: (t) => t.feature, sortable: true, facet: true, facetLabel: shortKey },
    { id: 'layer', label: 'Layer', value: (t) => t.layer, sortable: true, facet: true },
    { id: 'status', label: 'Status', value: (t) => t.status, sortable: true, facet: true },
    { id: 'traces', label: 'Traces to', value: (t) => t.traces.map(shortKey).join(', ') || null },
  ];
</script>

<PageHead title="Tasks" lede="Implementation tasks by feature and layer. Choose a row to read the task." />
{#if app.tasks.length}
  <DataTable id="tasks" rows={app.tasks} {cols} rowKey={(t) => t.id} title={(t) => shortKey(t.id)} sub={(t) => t.title} search={(t) => t.id} template="minmax(0,2fr) 8rem 7rem 7rem minmax(0,1.5fr)" onrow={(t) => preview.openKey(t.id)}>
    {#snippet cells(t)}
      <a data-label="Feature" class="chip" href={href('features', t.feature)}>{shortKey(t.feature)}</a>
      <span data-label="Layer">{#if t.layer}<span class="chip">{t.layer}</span>{:else}<span class="muted">none</span>{/if}</span>
      <span data-label="Status"><Pill look={wordLook(t.status)} /></span>
      <span data-label="Traces to" class="sub">{t.traces.map(shortKey).join(', ') || 'none'}</span>
    {/snippet}
  </DataTable>
{:else}
  <OwnerEmpty kind="tasks" what="task" />
{/if}
