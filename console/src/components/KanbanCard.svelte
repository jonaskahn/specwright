<script lang="ts">
  import { idleTone, layerSplit, type Card } from '../lib/board';
  import { ago } from '../lib/format';
  import { href } from '../lib/router';
  import { illustrationLook, lintLook, stateLook } from '../lib/status';
  import Pill from './Pill.svelte';

  let {
    card,
    several,
    dense = false,
    open,
    copy,
    shown = null,
    column,
    index,
  }: {
    card: Card;
    /** More than one project in view: show which one the card is from. */
    several: boolean;
    dense?: boolean;
    open: (key: string) => void;
    copy: (command: string) => void;
    /** A command that could not be copied, shown as text instead. */
    shown?: string | null;
    column: string;
    index: number;
  } = $props();

  const f = $derived(card.feature);
  const blocker = $derived(f.blockers[0]);
  const questions = $derived(f.openQuestions.length);
  const changes = $derived(f.openChanges.length);
  const days = $derived(card.idle);
</script>

<article class="kcard {card.condition}" data-col={column} data-idx={index}>
  <button class="kcard-main" type="button" data-card onclick={() => open(f.id)}>
    <span class="k-top">
      <span class="mono name">{f.id.replace(/^[A-Z][A-Z0-9]*:/, '')}</span>
      {#if several}<span class="chip">{f.scope}</span>{/if}
      {#if f.jira}<span class="chip" title="Published to Jira">{f.jira}</span>{/if}
    </span>
    <span class="k-title">{f.title}</span>
    {#if card.epics.length}
      <span class="k-epics">{#each card.epics as e (e.key)}<span class="chip" title={`Epic ${e.key}`}>{e.title}</span>{/each}</span>
    {/if}
    {#if !dense}
      <span class="k-sig">
        <span title="Acceptance criteria">{f.acCount} AC</span>
        <span title={card.layers.length ? `Tasks by layer: ${layerSplit(card.layers)}` : 'Tasks'}>{f.taskCount} {f.taskCount === 1 ? 'task' : 'tasks'}{card.layers.length ? ` (${layerSplit(card.layers)})` : ''}</span>
        {#if questions}<span class="bad" title="Open questions">{questions} {questions === 1 ? 'question' : 'questions'}</span>{/if}
        {#if changes}<span class="warn" title="Open change requests">{changes} {changes === 1 ? 'change' : 'changes'}</span>{/if}
        {#if f.drift}<span class="warn" title="Published text differs from the draft">drift</span>{/if}
        {#if f.signoff}<span title="Sign-off">{f.signoff}</span>{/if}
      </span>
      <span class="k-pills">
        <Pill look={stateLook(f.state, f.condition)} />
        {#if f.lint}<Pill look={lintLook(f.lint)} />{/if}
        {#if f.illustration}<Pill look={illustrationLook(f.illustration)} />{/if}
      </span>
    {/if}
    {#if blocker}<span class="k-block">{blocker}{f.blockers.length > 1 ? ` (+${f.blockers.length - 1} more)` : ''}</span>{/if}
  </button>
  <footer class="k-foot">
    <span class="sub">
      {#if f.next}<strong>{f.next}</strong>{#if f.turn}{` · ${f.turn}`}{/if}{:else}No next step{/if}
    </span>
    <span class="k-idle {idleTone(days)}" title="Time since the feature last changed">{days === null ? 'no date' : ago(days)}</span>
    {#if card.command}<button class="btn ghost" type="button" title={`Copy ${card.command}`} onclick={() => copy(card.command!)}>Copy command</button>{/if}
    <a class="btn ghost" href={href('features', f.id)}>Page</a>
    {#if shown && shown === card.command}<code class="k-cmd">{shown}</code>{/if}
  </footer>
</article>
