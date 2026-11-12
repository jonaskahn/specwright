<script lang="ts">
  import type { MarkShape } from '../lib/status';
  let { shape }: { shape: MarkShape } = $props();
</script>

<svg class="mk" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
  {#if shape === 'circle'}
    <circle cx="8" cy="8" r="6" fill="currentColor" />
  {:else if shape === 'check'}
    <circle cx="8" cy="8" r="7" fill="currentColor" />
    <path d="M4.6 8.2l2.4 2.4 4.4-4.8" fill="none" stroke="var(--surface)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
  {:else if shape === 'triangle'}
    <path d="M8 1.8l7 12.4H1z" fill="currentColor" />
  {:else if shape === 'square'}
    <rect x="2.5" y="2.5" width="11" height="11" rx="2" fill="currentColor" />
  {:else if shape === 'diamond'}
    <path d="M8 1l7 7-7 7-7-7z" fill="currentColor" />
  {:else}
    <circle cx="8" cy="8" r="5.6" fill="none" stroke="currentColor" stroke-width="1.8" />
  {/if}
</svg>
