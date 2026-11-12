<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
</script>

<PageHead title="Tasks" lede="Implementation tasks, one list per feature plan." />
{#if app.tasks.length}
  <div class="ledger" style:--cols="minmax(0,2fr) 11rem 7rem minmax(0,1.5fr)">
    <div class="lhead"><span>Task</span><span>Feature</span><span>Status</span><span>Traces to</span></div>
    {#each app.tasks as t (t.id)}
      <div class="lrow">
        <span><span class="name">{t.id.split(':')[1]}</span><div class="sub">{t.title}</div></span>
        <a data-label="Feature" class="chip" href={href('features', t.feature)}>{t.feature.split(':')[1]}</a>
        <span data-label="Status"><Pill look={wordLook(t.status)} /></span>
        <span data-label="Traces to" class="sub">{t.traces.map((k) => k.split(':')[1]).join(', ') || 'none'}</span>
      </div>
    {/each}
  </div>
{:else}
  <OwnerEmpty kind="tasks" what="task" />
{/if}
