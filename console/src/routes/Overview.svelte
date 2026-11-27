<script lang="ts">
  import Mark from '../components/Mark.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import PageHead from '../components/PageHead.svelte';
  import Pill from '../components/Pill.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import { app } from '../lib/data/store.svelte';
  import { computeMetrics, type Metrics } from '../lib/data/metrics';
  import { plural } from '../lib/format';
  import { href } from '../lib/router';
  import { lintLook, wordLook } from '../lib/status';

  const SHOWN = 5;
  const m = $derived(app.metrics);
  const titles = $derived(new Map<string, string>([...app.features.map((f) => [f.id, f.title] as const), ...app.tasks.map((t) => [t.id, t.title.replace(/^\[[A-Za-z-]+\]\s*/, '')] as const)]));
  const shown = $derived(m.attention.slice(0, SHOWN));
  const more = $derived(m.attention.length - shown.length);
  const several = $derived(app.scopes.length > 1 && app.scope === '*');
  const projects = $derived(
    (several ? app.scopes : app.scopes.filter((s) => app.scope === '*' || s.scope === app.scope)).map((s) => ({ scope: s, m: computeMetrics(app.loaded, s.scope) })),
  );

  const bucket = (p: Metrics['progress']) => {
    const n = (word: string) => p.find((x) => x.progress === word)?.count ?? 0;
    return { done: n('done'), inProgress: n('in-progress') + n('blocked'), blocked: n('blocked'), notStarted: n('not-started') + n('planned'), planned: n('planned') };
  };
  const label = (b: ReturnType<typeof bucket>) =>
    `${b.done} done, ${b.inProgress} in progress of which ${b.blocked} blocked, ${b.notStarted} not started of which ${b.planned} planned`;
</script>

<PageHead title="Overview" lede="What needs a person, and how the work is going." />
<div class="stack">
  <StaleBanner />

  <section>
    <div class="sec-h">
      <div>
        <h2>{m.attention.length ? `${plural(m.attention.length, 'thing')} need${m.attention.length === 1 ? 's' : ''} you` : 'Nothing is waiting on you'}</h2>
        <p class="sub">A story that is blocked, fails lint or waits on a question, and a task marked blocked.</p>
      </div>
    </div>
    {#if shown.length}
      <div class="ledger" style:--cols="minmax(0,2fr) minmax(0,1fr) 2rem">
        {#each shown as a (a.kind + a.id)}
          <a class="lrow" href={a.kind === 'feature' ? href('features', a.id) : href('board')}>
            <span><span class="name">{a.id}</span><div class="sub">{titles.get(a.id) ?? ''}</div></span>
            <span data-label="Why" class="muted">{a.reason}</span>
            <span aria-hidden="true">→</span>
          </a>
        {/each}
        {#if more > 0}
          <a class="lrow" href={href('features')}><span class="muted">{plural(more, 'more thing')} need you</span><span></span><span aria-hidden="true">→</span></a>
        {/if}
      </div>
    {:else}
      <div class="empty"><p class="muted">No story is blocked, failing lint or waiting on a question, and no task is blocked.</p></div>
    {/if}
  </section>

  <section>
    <div class="sec-h"><div><h2>Progress</h2><p class="sub">Tasks by the status recorded in each plan</p></div><a class="btn ghost" href={href('board')}>Open the board</a></div>
    {#if projects.length}
      <div class="card pad stack-sm">
        {#each projects as p (p.scope.scope)}
          {@const b = bucket(p.m.progress)}
          <div class="stack-sm">
            <div class="row-flex wrap">
              <strong>{p.scope.name}</strong>
              {#if several}<span class="chip">{p.scope.scope}</span>{/if}
              <span class="sub">{plural(p.m.epics, 'epic')} · {plural(p.m.features, 'story', 'stories')} · {plural(p.m.tasks, 'task')}</span>
            </div>
            {#if p.m.tasks}
              <div class="stackbar" role="img" aria-label={label(b)}>
                <span style:--w={b.done} style:--c="var(--color-ok)"></span>
                <span style:--w={b.inProgress} style:--c="var(--color-warn)"></span>
                <span style:--w={b.notStarted} style:--c="var(--rule-strong)"></span>
              </div>
              <div class="legend">
                <span><Mark shape={wordLook('done').shape} />Done · {b.done}</span>
                <span><Mark shape={wordLook('in-progress').shape} />In progress · {b.inProgress}{b.blocked ? ` (${b.blocked} blocked)` : ''}</span>
                <span><Mark shape={wordLook('not-started').shape} />Not started · {b.notStarted}{b.planned ? ` (${b.planned} planned)` : ''}</span>
              </div>
            {:else}
              <p class="muted">No task is planned yet. The planning skill writes tasks; they then appear here.</p>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <OwnerEmpty kind="scopes" what="project" />
    {/if}
  </section>

  <section class="stack-sm">
    <div class="row-flex wrap gap-2">
      <a class="chip" href={href('features')}>{plural(m.features, 'story', 'stories')}</a>
      <a class="chip" href={href('graph')}>{m.acs} acceptance criteria</a>
      <a class="chip" href={href('board')}>{plural(m.tasks, 'task')}</a>
      <a class="chip" href={href('records')}>{plural(m.records, 'record')}</a>
    </div>
    <div class="row-flex wrap">
      <Pill look={lintLook('pass')} /><strong class="num">{m.lintPass}</strong>
      <Pill look={lintLook('fail')} /><strong class="num">{m.lintFail}</strong>
      <a class="btn ghost" href={href('quality')}>Quality</a>
    </div>
  </section>
</div>
