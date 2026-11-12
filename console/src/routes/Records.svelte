<script lang="ts">
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import { app } from '../lib/data/store.svelte';
  import { ago, daysSince } from '../lib/format';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';

  const NAMES: Record<string, string> = { q: 'Question', dec: 'Decision', cr: 'Change request', amendment: 'Amendment' };
  let kind = $state('');
  const shown = $derived(app.records.filter((r) => !kind || r.kind === kind));
  const kinds = $derived([...new Set(app.records.map((r) => r.kind))]);
</script>

<PageHead title="Records" lede="Questions, decisions and change requests." />
{#if app.records.length}
  <div class="stack-sm">
    <div class="seg" role="group" aria-label="Kind">
      <button type="button" aria-pressed={kind === ''} onclick={() => (kind = '')}>All</button>
      {#each kinds as k (k)}<button type="button" aria-pressed={kind === k} onclick={() => (kind = k)}>{NAMES[k] ?? k}</button>{/each}
    </div>
    <div class="ledger" style:--cols="minmax(0,2fr) 8rem 7rem minmax(0,1.2fr) 6rem">
      <div class="lhead"><span>Record</span><span>Kind</span><span>Status</span><span>Affects</span><span>Updated</span></div>
      {#each shown as r (r.id)}
        <div class="lrow">
          <span><span class="name">{r.id.split(':')[1]}</span><div class="sub">{r.title}</div></span>
          <span data-label="Kind" class="chip">{NAMES[r.kind] ?? r.kind}</span>
          <span data-label="Status"><Pill look={wordLook(r.status)} /></span>
          <span data-label="Affects" class="row-flex wrap">{#each r.affects as a (a)}<a class="chip" href={href('features', a)}>{a.split(':')[1]}</a>{:else}<span class="muted">none</span>{/each}</span>
          <span data-label="Updated" class="muted">{ago(daysSince(r.updated, app.today))}</span>
        </div>
      {/each}
    </div>
  </div>
{:else}
  <OwnerEmpty kind="records" what="record" />
{/if}
