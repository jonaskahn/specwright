<script lang="ts">
  import Icon from '../components/Icon.svelte';
  import Mark from '../components/Mark.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import {
    ATTENTION_WORDS, buildLanes, closedQuery, columnCounts, countsOf, criterionState, filterLanes, LOOSE, needsAttention, orderStories, parseClosed,
    percentDone, PROGRESS_COLUMNS, storyProgress, tasksByColumn, tasksFor, UNPLACED, type AttentionCard, type LaneFilters, type StoryOrder,
  } from '../lib/board';
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
  const filtering = $derived(!!filters.text || !!filters.epic || filters.retired);

  /** Every story once, even when it belongs to two epics, so the summary counts each piece of work once. */
  const everyStory = $derived([...new Map(everyLane.flatMap((l) => l.stories).filter((s) => !s.retired).map((s) => [s.id, s])).values()]);
  const total = $derived(countsOf(everyStory));
  const columns = $derived(columnCounts(everyStory));
  const epics = $derived(everyLane.filter((l) => l.key !== LOOSE && l.key !== UNPLACED).length);
  const looseStories = $derived(everyLane.find((l) => l.key === LOOSE)?.stories.filter((s) => !s.retired).length ?? 0);
  const cards = $derived(needsAttention(everyLane));
  const allShut = $derived(lanes.length > 0 && lanes.every((l) => closed.has(l.key)));

  /** The criterion whose tasks are lit; page state, so leaving the page clears it. */
  let picked = $state<string | null>(null);
  let copied = $state<string | null>(null);

  const set = (changes: Record<string, string | null>) => app.setQuery(changes);
  const clear = () => set({ q: null, epic: null, retired: null });
  function toggle(key: string) {
    const next = new Set(closed);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    set({ closed: closedQuery(next) });
  }
  const foldAll = () => set({ closed: allShut ? null : closedQuery(new Set(lanes.map((l) => l.key))) });
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      copied = text;
      setTimeout(() => { if (copied === text) copied = null; }, 1600);
    } catch {
      copied = null;
    }
  }
  const open = (c: AttentionCard) => { if (c.target.kind === 'task') preview.openKey(c.target.key); };
  const icon = (c: AttentionCard) => (c.key.startsWith('task:') || c.key.startsWith('blocked:') ? 'warn' : c.key.startsWith('lint:') ? 'lintfail' : c.key.startsWith('gap:') ? 'gap' : 'help');
  const eyebrow = (key: string) => (key === LOOSE || key === UNPLACED ? 'Unassigned' : 'Epic');
  const columnLook = (col: (typeof PROGRESS_COLUMNS)[number]) => wordLook(col);
</script>

<PageHead title="Board" lede="Epics are lanes, stories are rows, and every task sits in the column of the status its plan records." />
{#if everyLane.length}
  <div class="bd">
    <StaleBanner />

    <section class="bsum" aria-label="Plan summary">
      <div class="bcard">
        <span class="bcard-l">Stories</span>
        <span class="bcard-n num">{total.stories}</span>
        <span class="bcard-s">{plural(epics, 'epic')}{looseStories ? ` · ${plural(looseStories, 'story', 'stories')} without an epic` : ''}</span>
      </div>
      <div class="bcard wide">
        <div class="bcard-top"><span class="bcard-l">Tasks done</span><span class="bcard-s num">{percentDone(total.done, total.tasks)}%</span></div>
        <span class="bcard-n num">{total.done} <span class="bcard-of">of {total.tasks}</span></span>
        <div class="bseg" aria-hidden="true">
          {#each ['done', 'in-progress', 'planned', 'blocked', 'not-started'] as col (col)}<i class={col}></i>{/each}
        </div>
        <div class="bleg">
          {#each ['done', 'in-progress', 'planned', 'blocked', 'not-started'] as col (col)}
            {@const look = wordLook(col)}
            <span><i class="sw {col}"></i>{look.label} <span class="num">{columns[col as keyof typeof columns]}</span></span>
          {/each}
        </div>
      </div>
      <button type="button" class="bcard bad-card" aria-pressed={order === 'attention'} disabled={!total.blocked && order !== 'attention'} onclick={() => set({ order: order === 'attention' ? null : 'attention' })}>
        <span class="bcard-l">Blocked</span>
        <span class="bcard-n num">{total.blocked}</span>
        <span class="bcard-s">Needs a person before it can move</span>
      </button>
    </section>

    {#if cards.length}
      <section class="battn" aria-labelledby="battn-h">
        <div class="row-flex"><h2 id="battn-h">Needs attention</h2><span class="count-pill num">{cards.length}</span></div>
        <div class="battn-grid">
          {#each cards as c (c.key)}
            {#if c.target.kind === 'feature'}
              <a class="acard {c.tone}" href={href('features', c.target.key)}>
                <Icon name={icon(c)} />
                <span class="acard-t"><span class="mono acard-code">{c.code}</span><span>{c.sentence}</span></span>
              </a>
            {:else}
              <button type="button" class="acard {c.tone}" onclick={() => open(c)}>
                <Icon name={icon(c)} />
                <span class="acard-t"><span class="mono acard-code">{c.code}</span><span>{c.sentence}</span></span>
              </button>
            {/if}
          {/each}
        </div>
      </section>
    {/if}

    <div class="btools">
      <label class="bsearch">
        <Icon name="query" size="sm" />
        <input type="search" placeholder="Find a story, criterion or task" aria-label="Find a story, criterion or task" value={filters.text} oninput={(e) => set({ q: e.currentTarget.value })} />
      </label>
      <label class="bpick">Epic
        <select aria-label="Epic" value={filters.epic} onchange={(e) => set({ epic: e.currentTarget.value })}>
          <option value="">All epics</option>
          {#each everyLane as l (l.key)}<option value={l.key}>{l.title}</option>{/each}
        </select>
      </label>
      <label class="bpick"><input type="checkbox" checked={filters.retired} onchange={(e) => set({ retired: e.currentTarget.checked ? '1' : null })} /> Show retired stories</label>
      {#if filtering}<button class="btn ghost" type="button" onclick={clear}>Clear filters</button>{/if}
      <span class="spacer"></span>
      <button class="btn" type="button" onclick={foldAll}><Icon name="unfold" size="sm" />{allShut ? 'Expand all' : 'Collapse all'}</button>
    </div>

    {#each lanes as lane (lane.key)}
      {@const shown = !closed.has(lane.key)}
      <section class="klane" class:loose={lane.key === LOOSE || lane.key === UNPLACED} aria-labelledby={`lane-${lane.key}`}>
        <div class="klane-bar">
          <button class="klane-chev" type="button" aria-expanded={shown} aria-label={`${shown ? 'Collapse' : 'Expand'} ${lane.title}`} onclick={() => toggle(lane.key)}>
            <span class="chev" aria-hidden="true"></span>
          </button>
          <div class="klane-t">
            <span class="eyebrow">{eyebrow(lane.key)}{#if lane.scope && several} · {lane.scope}{/if}</span>
            <h2 id={`lane-${lane.key}`}>{lane.title}</h2>
          </div>
          <div class="klane-pills">
            <span class="count-pill soft">{plural(lane.counts.stories, 'story', 'stories')}</span>
            <span class="count-pill soft">{plural(lane.counts.tasks, 'task')}</span>
            {#if lane.counts.blocked}<span class="count-pill bad">{lane.counts.blocked} blocked</span>{/if}
            {#if lane.counts.retired && !filters.retired}<span class="count-pill soft">{plural(lane.counts.retired, 'retired story', 'retired stories')} hidden</span>{/if}
          </div>
          <span class="spacer"></span>
          <div class="klane-meter">
            <div class="bmeter" aria-hidden="true"><i style:--w={`${percentDone(lane.counts.done, lane.counts.tasks)}%`}></i></div>
            <span class="num">{lane.counts.done} of {lane.counts.tasks} done</span>
          </div>
        </div>
        {#if shown}
          {@const counts = columnCounts(lane.stories)}
          <div class="lane" role="table" aria-label={`Tasks of ${lane.title} by status`}>
            <div class="lane-grid lane-head" role="row">
              <span class="lane-col-h" role="columnheader">Story</span>
              {#each PROGRESS_COLUMNS as col (col)}
                {@const look = columnLook(col)}
                <span class="lane-col-h col-h {col}" role="columnheader"><Mark shape={look.shape} />{look.label}<span class="num col-n">{counts[col]}</span></span>
              {/each}
            </div>
            {#each orderStories(lane.stories, order) as s (s.id)}
              {@const cols = tasksByColumn(s)}
              {@const p = storyProgress(s)}
              <div class="lane-grid lane-row" class:retired={s.retired} role="row">
                <div class="story-card" role="cell">
                  {#if s.feature}
                    <div class="story-top">
                      <span class="mono sub"><a class="story-id" href={href('features', s.id)}>{shortKey(s.id)}</a>{#if several} · {s.scope}{/if}</span>
                      <Pill look={stateLook(s.feature.state, s.feature.condition)} />
                    </div>
                    <h3><a href={href('features', s.id)}>{s.title}</a></h3>
                    {#if s.retired}<span class="lane-note">Retired</span>{/if}
                    {#if s.attention}<span class="lane-note">{ATTENTION_WORDS[s.attention]}</span>{/if}
                    <div class="story-prog">
                      <div class="bmeter thin" aria-hidden="true"><i style:--w={`${percentDone(p.done, p.total)}%`}></i></div>
                      <span class="sub num">{p.total ? `${p.done} of ${plural(p.total, 'task')}` : 'No task is planned yet'}</span>
                    </div>
                    <div class="story-crit">
                      <span class="eyebrow sm">Acceptance criteria</span>
                      {#each s.criteria as c (c.key)}
                        {@const state = criterionState(s, c.key)}
                        {@const n = tasksFor(s, c.key)}
                        <button class="crit {state === 'none' && s.tasks.length ? 'gap' : state}" class:picked={picked === c.key} type="button" aria-pressed={picked === c.key} title={shortKey(c.key)} onclick={() => (picked = picked === c.key ? null : c.key)}>
                          <Mark shape={state === 'met' ? 'check' : state === 'open' ? 'circle' : 'hollow'} />
                          <span class="crit-t">{c.title}</span>
                          <span class="crit-w">{state === 'met' ? 'Met' : state === 'open' ? plural(n, 'task') : s.tasks.length ? 'No task' : 'Not planned'}</span>
                        </button>
                      {:else}
                        <span class="lane-note">No acceptance criterion yet</span>
                      {/each}
                    </div>
                    {#if s.feature.next}
                      {@const cmd = `/${s.feature.next} ${shortKey(s.id)}`}
                      <button class="cmd" type="button" aria-label={`Copy command ${cmd}`} onclick={() => copy(cmd)}>
                        <span class="mono">{cmd}</span>
                        <span class="sub">{copied === cmd ? 'Copied' : ''}</span>
                        <Icon name="copy" size="sm" />
                      </button>
                    {/if}
                  {:else}
                    <h3>{s.title}</h3>
                    <span class="lane-note">A task names a story that no file lists.</span>
                  {/if}
                </div>
                {#each PROGRESS_COLUMNS as col, i (col)}
                  <div class="status-cell {col}" class:tall={i === 0 && !cols[col].length} role="cell">
                    {#each cols[col] as t (t.id)}
                      {@const untied = t.traces.length === 0 && s.criteria.length > 0}
                      <button class="lane-card {col}" class:gap={untied} class:dim={picked !== null && !t.traces.includes(picked)} type="button" onclick={() => preview.openKey(t.id)}>
                        <span class="lane-card-top">
                          <span class="mono sub" title={t.id}>{shortKey(t.id)}</span>
                          {#if t.layer}<span class="layer-chip">{layerWords(t.layer)}</span>{/if}
                        </span>
                        <span class="lane-card-t">{t.title}</span>
                        {#if t.traces.length}
                          <span class="tchips">
                            {#each t.traces as k (k)}
                              <span class="tchip {col}"><Mark shape={col === 'done' ? 'check' : 'circle'} />{s.criteria.find((c) => c.key === k)?.title ?? shortKey(k)}</span>
                            {/each}
                          </span>
                        {/if}
                        {#if untied}<span class="lane-note"><Icon name="warn" size="sm" />Not tied to an acceptance criterion</span>{/if}
                        {#if t.progress === null}<span class="sub">Status not recorded</span>{/if}
                        {#if t.progress === 'done' && t.evidence}<span class="evid mono">{t.evidence}</span>{/if}
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
