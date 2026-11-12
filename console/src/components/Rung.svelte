<script lang="ts">
  import { RUNGS, label, rungSteps, type MarkShape } from '../lib/status';
  import Mark from './Mark.svelte';
  let { state, condition = null }: { state: string; condition?: string | null } = $props();
  const steps = $derived(rungSteps(state, condition));
  const shapes: Record<string, MarkShape> = { done: 'check', current: 'diamond', blocked: 'triangle', todo: 'hollow', off: 'square' };
</script>

<span class="rung" role="img" aria-label={`${label(state)}${condition === 'blocked' ? ', blocked' : ''}`}>
  {#each steps as step, i (RUNGS[i])}
    {#if i > 0}<span class="bar" class:done={step === 'done' || step === 'current' || step === 'blocked'}></span>{/if}
    <span class="step {step}" title={label(RUNGS[i])}><Mark shape={shapes[step]} /></span>
  {/each}
</span>
