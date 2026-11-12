<script lang="ts">
  import Bars from '../components/Bars.svelte';
  import PageHead from '../components/PageHead.svelte';
  import CoverageStrip from '../components/CoverageStrip.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import { scopedGraph } from '../lib/data/selectors';
  import { traceCoverage } from '../lib/graph/trace';
  import { href } from '../lib/router';
  import { app } from '../lib/data/store.svelte';
  import { stateLook } from '../lib/status';
  import { stationWords } from '../lib/vocabulary';

  const m = $derived(app.metrics);
  const cover = $derived.by(() => {
    const g = scopedGraph(app.loaded, app.scope);
    return traceCoverage(g.nodes, g.edges);
  });
</script>

<PageHead title="Metrics" lede="Numbers worked out from the data files. Nothing here is stored." />
<div class="stack">
  <StaleBanner />
  <div class="kpis" style:--n="4">
    <div class="kpi"><div class="l">Features</div><div class="v">{m.features}</div></div>
    <div class="kpi"><div class="l">Criteria per feature</div><div class="v">{m.acsPerFeature}</div></div>
    <div class="kpi"><div class="l">Tasks per feature</div><div class="v">{m.tasksPerFeature}</div></div>
    <div class="kpi"><div class="l">Idle {m.idleAfterDays}+ days</div><div class="v">{m.idle}</div></div>
  </div>
  {#if cover.length}
    <section class="stack-sm">
      <div class="sec-h"><h2>Traceability coverage</h2><span class="sub">How completely goals, features, criteria and tasks are linked. Choose a measure to see the gaps on the graph.</span></div>
      <CoverageStrip measures={cover} onpick={() => (location.hash = href('graph'))} />
    </section>
  {/if}
  <div class="grid">
    <section class="span-6 card pad stack-sm">
      <div class="sec-h"><h2>Features by state</h2></div>
      <Bars items={m.byState.map((s) => ({ label: stateLook(s.state).label, value: s.count }))} />
    </section>
    <section class="span-6 card pad stack-sm">
      <div class="sec-h"><h2>Features by station</h2></div>
      <Bars items={m.byStation.map((s) => ({ label: stationWords(s.station), value: s.count }))} />
    </section>
    <section class="span-6 card pad stack-sm">
      <div class="sec-h"><h2>Lint</h2></div>
      <Bars items={[{ label: 'Passing', value: m.lintPass }, { label: 'Failing', value: m.lintFail }, { label: 'Not run', value: m.lintUnknown }]} total={Math.max(1, m.features)} />
      {#if m.findingsBySeverity.length}<Bars items={m.findingsBySeverity.map((f) => ({ label: `Findings: ${f.severity}`, value: f.count }))} />{/if}
    </section>
    <section class="span-6 card pad stack-sm">
      <div class="sec-h"><h2>Business objectives</h2><span class="sub">Features per objective</span></div>
      {#if m.bo.length}<Bars items={m.bo.map((b) => ({ label: b.bo, value: b.features }))} />{:else}<p class="muted">No feature names an objective.</p>{/if}
    </section>
  </div>
</div>
