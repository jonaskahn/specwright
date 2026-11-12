<script lang="ts">
  import type { Look } from '../lib/status';
  import Mark from './Mark.svelte';
  let { look }: { look: Look } = $props();
</script>

<span class="pill {look.tone}"><Mark shape={look.shape} />{look.label}</span>
