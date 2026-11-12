<script lang="ts">
  interface Item { label: string; value: number; tone?: string }
  let { items, total = 0 }: { items: Item[]; total?: number } = $props();
  const max = $derived(total || Math.max(1, ...items.map((i) => i.value)));
</script>

<div class="measures">
  {#each items as item (item.label)}
    <div class="measure">
      <span>{item.label}</span>
      <span class="track"><span class="fill" style:--w={Math.round((item.value / max) * 100)}></span></span>
      <span class="n">{item.value}</span>
    </div>
  {/each}
</div>
