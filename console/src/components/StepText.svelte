<script lang="ts">
  import type { Inline } from '../lib/markdown/parse';
  import { valuesOf } from '../lib/markdown/criteria';
  import MdInline from './MdInline.svelte';

  let { items }: { items: Inline[] } = $props();
</script>

{#each valuesOf(items) as piece, n (n)}{#if piece.t === 'value'}<span class="ac-val">{piece.v}</span>{:else}<MdInline items={[piece.item]} />{/if}{/each}
