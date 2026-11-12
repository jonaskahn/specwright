<script lang="ts">
  import type { Snippet } from 'svelte';
  let { title, lede = '', actions }: { title: string; lede?: string; actions?: Snippet } = $props();
</script>

<div class="ph">
  <div>
    <h1>{title}</h1>
    {#if lede}<p class="lede">{lede}</p>{/if}
  </div>
  {#if actions}<div class="actions">{@render actions()}</div>{/if}
</div>
