<script lang="ts">
  import { OWNERS } from '../../contract/types';
  import { app } from '../lib/data/store.svelte';
  import Icon from './Icon.svelte';
  const stale = $derived(app.loaded.stale);
  const invalid = $derived(app.loaded.invalid);
</script>

{#if stale.length || invalid.length}
  <div class="banner warn" role="status">
    <Icon name="warn" />
    <div>
      {#if stale.length}
        <p><strong>Some data is older than the rest:</strong> {stale.map((k) => `${k} (${OWNERS[k]})`).join(', ')}. The owning skill refreshes each file.</p>
      {/if}
      {#if invalid.length}
        <p><strong>Could not read:</strong> {invalid.join(', ')}. Run <code>data.py check</code>.</p>
      {/if}
    </div>
  </div>
{/if}
