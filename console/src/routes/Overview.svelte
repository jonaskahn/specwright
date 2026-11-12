<script lang="ts">
  import Pill from '../components/Pill.svelte';
  import PageHead from '../components/PageHead.svelte';
  import StaleBanner from '../components/StaleBanner.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import { lintLook, stateLook } from '../lib/status';
  import { plural } from '../lib/format';

  const m = $derived(app.metrics);
  const tones: Record<string, string> = { ok: 'var(--color-ok)', warn: 'var(--color-warn)', danger: 'var(--color-danger)', accent: 'var(--accent)', neutral: 'var(--rule-strong)' };
  const toneOf = (state: string) => tones[stateLook(state).tone];
  const focus = $derived(
    app.features
      .filter((f) => f.condition === 'blocked' || /fail/i.test(f.lint ?? '') || f.openQuestions.length || f.openChanges.length)
      .slice(0, 6),
  );
  const gates = $derived(app.loaded.data.quality?.gates ?? []);
</script>

<PageHead title="Overview" lede="What the workspace holds, and where it needs a person." />
<div class="stack">
  <StaleBanner />
  {#if m.attention.length}
    <div class="attention" role="status">
      <span class="pill danger">{plural(m.attention.length, 'item')} need attention</span>
      {#each m.attention.slice(0, 3) as a (a.id)}
        <span><a class="name" href={href('features', a.id)}>{a.id}</a> <span class="muted">{a.reason}</span></span>
      {/each}
    </div>
  {/if}
  <div class="kpis" style:--n="4">
    <div class="kpi answer"><div class="l">Features</div><div class="v">{m.features}</div><div class="s">{m.ready}% ready for dev</div></div>
    <div class="kpi"><div class="l">Acceptance criteria</div><div class="v">{m.acs}</div><div class="s">{m.acsPerFeature} per feature</div></div>
    <div class="kpi"><div class="l">Tasks</div><div class="v">{m.tasks}</div><div class="s">{m.noTasks} features without tasks</div></div>
    <div class="kpi"><div class="l">Open questions</div><div class="v">{m.openQuestions}</div><div class="s">{m.openChanges} change requests open</div></div>
  </div>

  <section class="sec">
    <div class="sec-h"><div><h2>Lifecycle</h2><p class="sub">Features by state</p></div><a class="btn ghost" href={href('features')}>All features</a></div>
    <div class="card pad">
      {#if m.byState.length}
        <div class="stackbar" role="img" aria-label={m.byState.map((s) => `${s.count} ${s.state}`).join(', ')}>
          {#each m.byState as s (s.state)}<span style:--w={s.count} style:--c={toneOf(s.state)}></span>{/each}
        </div>
        <div class="legend">
          {#each m.byState as s (s.state)}<span><i style:--c={toneOf(s.state)}></i>{stateLook(s.state).label} · {s.count}</span>{/each}
        </div>
      {:else}
        <OwnerEmpty kind="features" what="feature" />
      {/if}
    </div>
  </section>

  <div class="grid">
    <section class="span-7">
      <div class="sec-h"><div><h2>Needs a person</h2><p class="sub">Blocked, failing lint, or waiting on a record</p></div></div>
      {#if focus.length}
        <div class="ledger" style:--cols="minmax(0,2fr) 8rem 10rem">
          <div class="lhead"><span>Feature</span><span>State</span><span>Why</span></div>
          {#each focus as f (f.id)}
            <a class="lrow" href={href('features', f.id)}>
              <span><span class="name">{f.id}</span><div class="sub">{f.title}</div></span>
              <span data-label="State"><Pill look={stateLook(f.state, f.condition)} /></span>
              <span data-label="Why" class="muted">{f.openQuestions.length ? plural(f.openQuestions.length, 'open question') : f.openChanges.length ? 'change request' : (f.lint ?? 'blocked')}</span>
            </a>
          {/each}
        </div>
      {:else}
        <div class="empty"><h3>Nothing is waiting</h3><p class="muted">No feature is blocked, failing lint or waiting on a question.</p></div>
      {/if}
    </section>
    <section class="span-5">
      <div class="sec-h"><div><h2>Quality</h2><p class="sub">Lint gate and results</p></div><a class="btn ghost" href={href('quality')}>Details</a></div>
      <div class="card pad stack-sm">
        <div class="row-flex wrap">
          {#each gates as g (g)}<span class="chip">{g}</span>{:else}<span class="muted">No lint gate recorded.</span>{/each}
        </div>
        <div class="row-flex wrap">
          <Pill look={lintLook('pass')} /><strong class="num">{m.lintPass}</strong>
          <Pill look={lintLook('fail')} /><strong class="num">{m.lintFail}</strong>
          <span class="muted">{m.lintUnknown} not run</span>
        </div>
        <p class="sub">{m.idle} features idle for {m.idleAfterDays}+ days · {m.staleSnapshots} snapshots older than 30 days</p>
      </div>
    </section>
  </div>
</div>
