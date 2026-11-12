<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import { stateLook } from '../lib/status';
  import { stationWords } from '../lib/vocabulary';

  const order = ['shape', 'spec', 'review', 'plan', 'publish', 'dev', 'inactive'];
  const lanes = $derived.by(() => {
    const names = [...new Set(app.features.map((f) => f.station ?? 'unknown'))];
    names.sort((a, b) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99));
    return names.map((name) => ({ name, items: app.features.filter((f) => (f.station ?? 'unknown') === name) }));
  });
</script>

<PageHead title="Board" lede="Features by station, with their condition and blockers." />
{#if lanes.length}
  <div class="board">
    {#each lanes as lane (lane.name)}
      <section class="lane">
        <h3><span>{stationWords(lane.name === 'unknown' ? null : lane.name)}</span><span class="muted num">{lane.items.length}</span></h3>
        {#each lane.items as f (f.id)}
          <a class="card" href={href('features', f.id)}>
            <span class="name">{f.id}</span>
            <span class="sub">{f.title}</span>
            <span><Pill look={stateLook(f.state, f.condition)} /></span>
            {#each f.blockers as b (b)}<span class="sub">{b}</span>{/each}
          </a>
        {/each}
      </section>
    {/each}
  </div>
{:else}
  <OwnerEmpty kind="features" what="feature" />
{/if}
