<script lang="ts">
  import type { Coverage } from '../lib/graph/trace';
  import { percent } from '../lib/format';

  let { measures, active = null, onpick }: { measures: Coverage[]; active?: string | null; onpick: (id: string | null) => void } = $props();
</script>

{#if measures.length}
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
        <span class="v"><strong>{m.have}</strong> of {m.total}{done ? ' · complete' : ` · ${m.gaps.length} missing`}</span>
        <span class="meter" aria-hidden="true"><i style:--w={`${percent(m.have, m.total)}%`}></i></span>
      </button>
    {/each}
  </div>
{/if}
