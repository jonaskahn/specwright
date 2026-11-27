<script lang="ts">
  import type { Coverage } from '../lib/graph/trace';
  import { percent, plural } from '../lib/format';
  import { shortKey } from '../lib/format';

  let { measures, active = null, onpick, broken = 0, items = 0 }: { measures: Coverage[]; active?: string | null; onpick: (id: string | null) => void; broken?: number; items?: number } = $props();
  const gaps = $derived(measures.reduce((n, m) => n + m.gaps.length, 0));
</script>

{#if measures.length}
  <section class="health" aria-labelledby="health-h">
    <div class="health-h">
      <h2 id="health-h">Chain health</h2>
      {#if gaps}<span class="count-pill warn">{plural(gaps, 'gap')}</span>{/if}
      {#if broken}<span class="count-pill bad">{plural(broken, 'broken reference')}</span>{/if}
      <span class="spacer"></span>
      <span class="sub">{plural(items, 'item')} in the chain</span>
    </div>
    <div class="coverage" role="group" aria-label="How completely the chain is linked">
      {#each measures as m (m.id)}
        {@const done = m.gaps.length === 0}
        <button
          class="cover"
          class:done
          type="button"
          aria-pressed={active === m.id}
          disabled={done}
          title={done ? 'Nothing is missing' : 'Point at the items that miss this link'}
          onclick={() => onpick(active === m.id ? null : m.id)}
        >
          <span class="l">{m.label}</span>
          <span class="v"><strong>{m.have}</strong> of {m.total}</span>
          <span class="meter" aria-hidden="true"><i style:--w={`${percent(m.have, m.total)}%`}></i></span>
          <span class="w">{done ? 'Complete' : `${m.gaps.length} missing · ${m.gaps.slice(0, 1).map(shortKey).join('')}`}</span>
        </button>
      {/each}
    </div>
  </section>
{/if}
