<script lang="ts">
  import DataTable from '../components/DataTable.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import Rung from '../components/Rung.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince } from '../lib/format';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { lintLook, stateLook } from '../lib/status';
  import type { Col } from '../lib/table';
  import { stationWords } from '../lib/vocabulary';

  type Feature = (typeof app.features)[number];
  const cols: Col<Feature>[] = [
    { id: 'id', label: 'Feature', value: (f) => f.id, sortable: true },
    { id: 'rung', label: 'Rung', value: (f) => f.state },
    { id: 'state', label: 'State', value: (f) => f.state, sortable: true, facet: true, facetLabel: (v) => stateLook(v).label },
    { id: 'lint', label: 'Lint', value: (f) => f.lint },
    { id: 'open', label: 'Open', value: (f) => f.openQuestions.length + f.openChanges.length, sortable: true },
    { id: 'updated', label: 'Updated', value: (f) => f.updated, sortable: true },
    { id: 'page', label: '', value: () => null },
    { id: 'station', label: 'Station', value: (f) => f.station, facet: true, hidden: true, facetLabel: stationWords },
    { id: 'turn', label: 'Turn', value: (f) => f.turn, facet: true, hidden: true },
    { id: 'condition', label: 'Condition', value: (f) => f.condition, facet: true, hidden: true, facetLabel: (v) => v.replace(/-/g, ' ') },
  ];
</script>

<PageHead title="Features" lede="Every story in the workspace, with its place on the lifecycle. Choose a row to read the story." />
<div class="stack">
  <StaleBanner />
  {#if app.features.length}
    <DataTable id="features" rows={app.features} {cols} rowKey={(f) => f.id} title={(f) => f.id} sub={(f) => f.title} search={(f) => f.title} template="minmax(0,2fr) 11rem 8rem minmax(9rem,1.4fr) 4rem 6rem 5rem" wide onrow={(f) => preview.openKey(f.id)}>
      {#snippet cells(f)}
        <span data-label="Rung"><Rung state={f.state} condition={f.condition} /></span>
        <span data-label="State"><Pill look={stateLook(f.state, f.condition)} /></span>
        <span data-label="Lint"><Pill look={lintLook(f.lint)} /></span>
        <span data-label="Open" class="num">{f.openQuestions.length + f.openChanges.length}</span>
        <span data-label="Updated" class="muted">{ago(daysSince(f.updated, app.today))}</span>
        <a class="btn ghost" href={href('features', f.id)}>Page</a>
      {/snippet}
    </DataTable>
  {:else}
    <OwnerEmpty kind="features" what="feature" />
  {/if}
</div>
