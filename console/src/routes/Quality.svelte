<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { preview } from '../lib/preview.svelte';
  import { forKey } from '../lib/preview-target';
  import { lintLook } from '../lib/status';
  import type { Col } from '../lib/table';

  const gates = $derived(app.loaded.data.quality?.gates ?? []);
  const drift = $derived(app.features.filter((f) => f.drift));
  type Result = (typeof app.results)[number];
  type Finding = (typeof app.findings)[number];
  type Feature = (typeof app.features)[number];
  const resultCols: Col<Result>[] = [
    { id: 'item', label: 'Item', value: (r) => r.id, sortable: true },
    { id: 'result', label: 'Result', value: (r) => r.result, sortable: true, facet: true },
  ];
  const findingCols: Col<Finding>[] = [
    { id: 'rule', label: 'Rule', value: (f) => f.rule, sortable: true, facet: true },
    { id: 'severity', label: 'Severity', value: (f) => f.severity, sortable: true, facet: true },
    { id: 'subject', label: 'Subject', value: (f) => f.subject, sortable: true },
    { id: 'location', label: 'Location', value: (f) => f.location },
    { id: 'waived', label: 'Waived', value: (f) => (f.waived ? 'yes' : 'no'), facet: true },
  ];
  const driftCols: Col<Feature>[] = [
    { id: 'feature', label: 'Feature', value: (f) => f.id, sortable: true },
    { id: 'drift', label: 'Drift', value: (f) => f.drift, sortable: true },
  ];
</script>

<PageHead title="Quality" lede="The lint gate, its results and published-text drift." />
{#if app.loaded.data.quality}
  <div class="stack">
    <div class="row-flex wrap">{#each gates as g (g)}<span class="chip">{g}</span>{:else}<span class="muted">No gate recorded: run the lint capability.</span>{/each}</div>
    <section>
      <div class="sec-h"><h2>Results</h2></div>
      {#if app.results.length}
        <DataTable id="results" rows={app.results} cols={resultCols} rowKey={(r) => r.id} title={(r) => r.id} template="minmax(0,1.5fr) minmax(0,2fr)" canOpen={(r) => !!forKey(app.loaded, r.id)} onrow={(r) => preview.openKey(r.id)}>
          {#snippet cells(r)}<span data-label="Result"><Pill look={lintLook(r.result)} /></span>{/snippet}
        </DataTable>
      {:else}<div class="empty"><h3>No results</h3></div>{/if}
    </section>
    <section>
      <div class="sec-h"><h2>Findings</h2><span class="sub">{app.findings.length}</span></div>
      {#if app.findings.length}
        <DataTable id="findings" rows={app.findings} cols={findingCols} rowKey={(f) => `${f.scope}|${f.rule}|${f.subject}|${f.location}`} title={(f) => f.rule} template="6rem 6rem minmax(0,1fr) minmax(0,1.5fr) 6rem" search={(f) => f.subject ?? ''}>
          {#snippet cells(f)}
            <span data-label="Severity" class="chip">{f.severity ?? 'none'}</span><span data-label="Subject">{f.subject ?? 'none'}</span>
            <span data-label="Location" class="sub mono">{f.location ?? 'none'}</span><span data-label="Waived">{f.waived ? 'yes' : 'no'}</span>
          {/snippet}
        </DataTable>
      {:else}<div class="empty"><h3>No findings recorded</h3><p class="muted">The lint report lists no rule findings for this scope.</p></div>{/if}
    </section>
    {#if drift.length}
      <section>
        <div class="sec-h"><h2>Drift</h2></div>
        <DataTable id="drift" rows={drift} cols={driftCols} rowKey={(f) => f.id} title={(f) => f.id} template="minmax(0,1fr) minmax(0,1fr)" keep onrow={(f) => preview.openKey(f.id)}>
          {#snippet cells(f)}<span>{f.drift}</span>{/snippet}
        </DataTable>
      </section>
    {/if}
  </div>
{:else}
  <OwnerEmpty kind="quality" what="quality" />
{/if}
