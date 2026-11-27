<script lang="ts">
  import Mark from '../components/Mark.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import { ATTENTION_WORDS, buildLanes, closedQuery, countsOf, filterLanes, orderStories, parseClosed, PROGRESS_COLUMNS, storyProgress, tasksByColumn, type LaneFilters, type StoryOrder } from '../lib/board';
  import { app } from '../lib/data/store.svelte';
  import { plural, shortKey } from '../lib/format';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { stateLook, wordLook } from '../lib/status';
  import { layerWords } from '../lib/vocabulary';

  const query = $derived(app.route.query);
  const filters = $derived<LaneFilters>({ text: query.get('q') ?? '', epic: query.get('epic') ?? '', retired: query.get('retired') === '1' });
  const order = $derived<StoryOrder>(query.get('order') === 'attention' ? 'attention' : 'id');
  const closed = $derived(parseClosed(query.get('closed')));
  const several = $derived(app.scopes.length > 1 && app.scope === '*');

  const everyLane = $derived(buildLanes(app.loaded, app.scope));
  const lanes = $derived(filterLanes(everyLane, filters));
  const total = $derived(countsOf(everyLane.flatMap((l) => l.stories.filter((s) => !s.retired))));
  const filtering = $derived(!!filters.text || !!filters.epic || filters.retired);

  /** The criterion whose tasks are lit; page state, so leaving the page clears it. */
  let picked = $state<string | null>(null);

  const set = (changes: Record<string, string | null>) => app.setQuery(changes);
  const clear = () => set({ q: null, epic: null, retired: null });
  function toggle(key: string) {
    const next = new Set(closed);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    set({ closed: closedQuery(next) });
  }
</script>

<PageHead title="Board" lede="Each epic is a lane. Each row is a story, and each task sits in the column of the status its plan records." />
{#if everyLane.length}
  <div class="stack-sm">
    <StaleBanner />
    <div class="board-sum" role="group" aria-label="Summary">
      <button type="button" class="sum" aria-pressed={!filtering} onclick={clear}><strong class="num">{total.stories}</strong> {total.stories === 1 ? 'story' : 'stories'}</button>
      <span class="sum"><strong class="num">{total.done}</strong> of {plural(total.tasks, 'task')} done</span>
      <button type="button" class="sum bad" aria-pressed={order === 'attention'} disabled={!total.blocked && order !== 'attention'} onclick={() => set({ order: order === 'attention' ? null : 'attention' })}>
        <strong class="num">{total.blocked}</strong> blocked · needs a person first
      </button>
    </div>
    <div class="row-flex wrap gap-2 board-tools">
      <input class="input" type="search" placeholder="Find a story, criterion or task" aria-label="Find a story, criterion or task" value={filters.text} oninput={(e) => set({ q: e.currentTarget.value })} />
      <select class="select" aria-label="Epic" value={filters.epic} onchange={(e) => set({ epic: e.currentTarget.value })}>
        <option value="">Epic: all</option>
        {#each everyLane as l (l.key)}<option value={l.key}>{l.title}</option>{/each}
      </select>
      <label class="row-flex"><input type="checkbox" checked={filters.retired} onchange={(e) => set({ retired: e.currentTarget.checked ? '1' : null })} /> Show retired stories</label>
      {#if filtering}<button class="btn ghost" type="button" onclick={clear}>Clear filters</button>{/if}
    </div>

    {#each lanes as lane (lane.key)}
      {@const open = !closed.has(lane.key)}
      <section class="klane">
        <button class="klane-h" type="button" aria-expanded={open} onclick={() => toggle(lane.key)}>
          <span class="chev" aria-hidden="true"></span>
          <strong>{lane.title}</strong>
          {#if lane.scope && several}<span class="chip">{lane.scope}</span>{/if}
          <span class="sub num">{plural(lane.counts.stories, 'story', 'stories')} · {plural(lane.counts.tasks, 'task')} · {lane.counts.done} done</span>
          {#if lane.counts.blocked}<span class="bad num">{lane.counts.blocked} blocked</span>{/if}
          {#if lane.counts.retired && !filters.retired}<span class="sub">{plural(lane.counts.retired, 'retired story', 'retired stories')} hidden</span>{/if}
        </button>
        {#if open}
          <div class="lane" role="table" aria-label={`Tasks of ${lane.title} by status`}>
            <div class="lane-grid lane-head" role="row">
              <span class="lane-col-h" role="columnheader">Story</span>
              {#each PROGRESS_COLUMNS as col (col)}
                {@const look = wordLook(col)}
                <span class="lane-col-h row-flex" role="columnheader"><Mark shape={look.shape} />{look.label}</span>
              {/each}
            </div>
            {#each orderStories(lane.stories, order) as s (s.id)}
              {@const cols = tasksByColumn(s)}
              {@const p = storyProgress(s)}
              <div class="lane-grid lane-row" class:retired={s.retired} role="row">
                <div class="lane-col lane-story-cell" role="cell">
                  {#if s.feature}
                    <span class="row-flex wrap">
                      <a class="name mono" href={href('features', s.id)}>{shortKey(s.id)}</a>
                      {#if several}<span class="chip">{s.scope}</span>{/if}
                      {#if s.retired}<span class="chip">Retired</span>{/if}
                    </span>
                    <span class="lane-story">{s.title}</span>
                    <span class="row-flex wrap"><Pill look={stateLook(s.feature.state, s.feature.condition)} /></span>
                    {#if s.attention}<span class="lane-note">{ATTENTION_WORDS[s.attention]}</span>{/if}
                    <span class="sub num">{p.total ? `${p.done} of ${plural(p.total, 'task')} done` : 'No task is planned yet'}</span>
                    {#each s.criteria as c (c.key)}
                      <button class="lane-item" class:gap={!c.covered && s.tasks.length > 0} class:picked={picked === c.key} type="button" aria-pressed={picked === c.key} title={shortKey(c.key)} onclick={() => (picked = picked === c.key ? null : c.key)}>
                        <span>{c.title}</span>
                        {#if !c.covered && s.tasks.length}<span class="lane-note">No task covers this criterion</span>{/if}
                      </button>
                    {:else}
                      <span class="lane-note">No acceptance criterion yet</span>
                    {/each}
                    {#if s.feature.next}<code class="chip lane-cmd" title="Run this to move the story on">{`/${s.feature.next} ${shortKey(s.id)}`}</code>{/if}
                  {:else}
                    <span class="lane-story">{s.title}</span>
                    <span class="lane-note">A task names a story that no file lists.</span>
                  {/if}
                </div>
                {#each PROGRESS_COLUMNS as col (col)}
                  <div class="lane-col lane-cell" role="cell">
                    {#each cols[col] as t (t.id)}
                      <button class="lane-card" class:gap={t.traces.length === 0 && s.criteria.length > 0} class:dim={picked !== null && !t.traces.includes(picked)} type="button" onclick={() => preview.openKey(t.id)}>
                        <span class="chip" title={t.id}>{shortKey(t.id)}</span>
                        <span>{t.title}</span>
                        {#if t.layer}<span class="chip">{layerWords(t.layer)}</span>{/if}
                        {#if t.progress === null}<span class="sub">Status not recorded</span>{/if}
                        {#if t.progress === 'done' && t.evidence}<span class="sub">{t.evidence}</span>{/if}
                        {#if t.traces.length === 0 && s.criteria.length}<span class="lane-note">Not tied to an acceptance criterion</span>{/if}
                        {#each t.traces as k (k)}<span class="sub">For: {s.criteria.find((c) => c.key === k)?.title ?? shortKey(k)}</span>{/each}
                      </button>
                    {/each}
                  </div>
                {/each}
              </div>
            {/each}
          </div>
        {/if}
      </section>
    {:else}
      <div class="empty"><p class="muted">Nothing matches. <button class="btn ghost" type="button" onclick={clear}>Clear filters</button></p></div>
    {/each}
  </div>
{:else}
  <OwnerEmpty kind="features" what="story" />
{/if}
