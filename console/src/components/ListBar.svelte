<script lang="ts">
  import { app } from '../lib/data/store.svelte';

  type Chip = { key: string; label: string; count: number };

  let {
    chips,
    active,
    onpick,
    what,
    expand = null,
    onexpand,
  }: {
    /** Filter chips, "All" first; none are drawn unless there is something to choose between. */
    chips: Chip[];
    active: string;
    onpick: (key: string) => void;
    /** What the list holds, for the screen reader: "criteria", "tasks". */
    what: string;
    /** Label of the expand link, or null in the table, which has nothing to expand. */
    expand?: string | null;
    onexpand?: () => void;
  } = $props();
  const view = $derived(app.prefs.listView);
</script>

<div class="ac-bar">
  {#if chips.length > 2}
    <div class="ac-chips" role="group" aria-label={`Filter ${what}`}>
      {#each chips as c (c.key)}
        <button class="ac-chip" type="button" aria-pressed={active === c.key} onclick={() => onpick(c.key)}>{c.label} {c.count}</button>
      {/each}
    </div>
  {/if}
  <div class="ac-tools">
    {#if view === 'cards' && expand}<button class="ac-link" type="button" onclick={onexpand}>{expand}</button>{/if}
    <div class="seg" role="group" aria-label={`Layout of the ${what}`}>
      <button type="button" aria-pressed={view === 'cards'} onclick={() => app.setPref('listView', 'cards')}>Cards</button>
      <button type="button" aria-pressed={view === 'table'} onclick={() => app.setPref('listView', 'table')}>Table</button>
    </div>
  </div>
</div>
