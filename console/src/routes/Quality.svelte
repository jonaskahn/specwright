<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import { lintLook } from '../lib/status';

  const gates = $derived(app.loaded.data.quality?.gates ?? []);
  const drift = $derived(app.features.filter((f) => f.drift));
</script>

<PageHead title="Quality" lede="The lint gate, its results and published-text drift." />
{#if app.loaded.data.quality}
  <div class="stack">
    <div class="row-flex wrap">{#each gates as g (g)}<span class="chip">{g}</span>{:else}<span class="muted">No gate recorded: run the lint capability.</span>{/each}</div>
    <section>
      <div class="sec-h"><h2>Results</h2></div>
      {#if app.results.length}
        <div class="ledger" style:--cols="minmax(0,1.5fr) minmax(0,2fr)">
          <div class="lhead"><span>Item</span><span>Result</span></div>
          {#each app.results as r (r.id)}
            <a class="lrow" href={href('features', r.id)}><span class="name">{r.id}</span><span data-label="Result"><Pill look={lintLook(r.result)} /></span></a>
          {/each}
        </div>
      {:else}<div class="empty"><h3>No results</h3></div>{/if}
    </section>
    <section>
      <div class="sec-h"><h2>Findings</h2><span class="sub">{app.findings.length}</span></div>
      {#if app.findings.length}
        <div class="ledger" style:--cols="6rem 6rem minmax(0,1fr) minmax(0,1.5fr) 6rem">
          <div class="lhead"><span>Rule</span><span>Severity</span><span>Subject</span><span>Location</span><span>Waived</span></div>
          {#each app.findings as f, i (i)}
            <div class="lrow"><span class="name mono">{f.rule}</span><span data-label="Severity" class="chip">{f.severity ?? 'none'}</span><span data-label="Subject">{f.subject ?? 'none'}</span><span data-label="Location" class="sub mono">{f.location ?? 'none'}</span><span data-label="Waived">{f.waived ? 'yes' : 'no'}</span></div>
          {/each}
        </div>
      {:else}<div class="empty"><h3>No findings recorded</h3><p class="muted">The lint report lists no rule findings for this scope.</p></div>{/if}
    </section>
    {#if drift.length}
      <section>
        <div class="sec-h"><h2>Drift</h2></div>
        <div class="ledger keep" style:--cols="minmax(0,1fr) minmax(0,1fr)">
          {#each drift as f (f.id)}<a class="lrow" href={href('features', f.id)}><span class="name">{f.id}</span><span>{f.drift}</span></a>{/each}
        </div>
      </section>
    {/if}
  </div>
{:else}
  <OwnerEmpty kind="quality" what="quality" />
{/if}
