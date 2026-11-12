<script lang="ts">
  import { OWNERS } from '../../contract/types';
  import { app } from '../lib/data/store.svelte';
  let { kind, what }: { kind: string; what: string } = $props();
  const missing = $derived(app.loaded.missing[kind]);
  const invalid = $derived(app.loaded.invalid.includes(kind));
</script>

<div class="empty">
  {#if missing || invalid}
    <h3>{invalid ? 'This file could not be read' : `No ${what} data yet`}</h3>
    <p class="muted">
      <code>{kind}.json</code> is owned by <strong>{OWNERS[kind] ?? 'a skill'}</strong>. Run that skill, or
      <code>data.py export {kind} --as {OWNERS[kind]}</code>, then reload.
    </p>
  {:else}
    <h3>No {what}</h3>
    <p class="muted">Nothing matches here yet.</p>
  {/if}
</div>
