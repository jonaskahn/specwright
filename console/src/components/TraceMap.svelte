<script lang="ts">
  import { hue } from '../lib/graph/layout';
  import { BOX, chainOf, LEVEL_NAMES, type TraceLink, type TraceModel, type TraceNode } from '../lib/graph/trace';
  import { shortKey } from '../lib/format';
  import { wordLook, type MarkShape } from '../lib/status';
  import { kindWords } from '../lib/vocabulary';

  let {
    model,
    selected = null,
    emphasis = new Set<string>(),
    onselect,
  }: { model: TraceModel; selected?: string | null; emphasis?: Set<string>; onselect: (id: string | null) => void } = $props();

  let manual = $state<number | null>(null);
  let room = $state(0);
  const fitted = $derived(room > 0 ? Math.min(1, Math.max(0.6, (room - 16) / model.width)) : 1);
  const zoom = $derived(manual ?? fitted);
  const chain = $derived(selected ? chainOf(model, selected) : null);
  const byId = $derived(new Map(model.nodes.map((n) => [n.id, n])));
  const dimmed = (id: string) => (chain ? !chain.nodes.has(id) : emphasis.size > 0 && !emphasis.has(id));
  const columns = $derived(model.levels.map((lv) => ({ lv, x: BOX.pad + model.levels.indexOf(lv) * (BOX.w + BOX.gapX), words: kindWords(LEVEL_NAMES[lv], true) })));

  function path(l: TraceLink): string {
    const a = byId.get(l.left)!;
    const b = byId.get(l.right)!;
    const x1 = a.x + BOX.w;
    const y1 = a.y + BOX.h / 2;
    const x2 = b.x;
    const y2 = b.y + BOX.h / 2;
    const bend = Math.max(BOX.gapX / 2, (x2 - x1) / 2);
    return `M${x1} ${y1} C${x1 + bend} ${y1} ${x2 - bend} ${y2} ${x2} ${y2}`;
  }
  const lit = (l: TraceLink) => !!chain && chain.links.has(l.id);
  const linkDim = (l: TraceLink) => (chain ? !chain.links.has(l.id) : emphasis.size > 0 && !(emphasis.has(l.left) && emphasis.has(l.right)));

  function fit(text: string, max = 25): string {
    return text.length > max ? text.slice(0, max - 1).trimEnd() + '…' : text;
  }
  function look(n: TraceNode): { shape: MarkShape; label: string } {
    const found = wordLook(n.status);
    return { shape: found.shape, label: found.label };
  }
  const sentence = (n: TraceNode) =>
    n.gap ? `${n.title}. Next step: ask ${n.next}.` : `${kindWords(n.kind)}: ${n.title}. ${n.status ? look(n).label + '.' : ''}${n.jira ? ' Jira issue ' + n.jira + '.' : ''}`;

  function key(e: KeyboardEvent, n: TraceNode) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onselect(selected === n.id ? null : n.id);
    }
  }
  const GLYPH: Record<string, string> = {
    check: 'M6 1.2a4.8 4.8 0 1 1 0 9.6 4.8 4.8 0 0 1 0-9.6zM3.7 6.1l1.6 1.6 3-3.3',
    triangle: 'M6 1.2l5 9.2H1z',
    square: 'M2 2h8v8H2z',
    diamond: 'M6 .8L11.2 6 6 11.2.8 6z',
    circle: 'M6 1.2a4.8 4.8 0 1 1 0 9.6 4.8 4.8 0 0 1 0-9.6z',
    hollow: 'M6 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z',
  };
</script>

<div class="trace">
  <div class="trace-tools" role="group" aria-label="Zoom">
    <button class="btn" type="button" aria-label="Zoom out" disabled={zoom <= 0.6} onclick={() => (manual = Math.max(0.6, +(zoom - 0.2).toFixed(2)))}>−</button>
    <button class="btn" type="button" aria-label="Zoom in" disabled={zoom >= 1.6} onclick={() => (manual = Math.min(1.6, +(zoom + 0.2).toFixed(2)))}>+</button>
    <button class="btn" type="button" onclick={() => (manual = null)}>Fit to width</button>
    {#if selected}<button class="btn" type="button" onclick={() => onselect(null)}>Clear selection</button>{/if}
  </div>
  <div class="trace-scroll" bind:clientWidth={room}>
    <svg
      class="trace-svg"
      role="group"
      aria-label={`Trace map with ${model.nodes.length} items in ${model.levels.length} levels. Choose an item to light up everything it connects to.`}
      width={model.width * zoom}
      height={model.height * zoom}
      viewBox={`0 0 ${model.width} ${model.height}`}
    >
      <defs>
        <marker id="trace-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0L8 4L0 8z" class="trace-arrowhead" />
        </marker>
      </defs>
      {#each columns as c (c.lv)}
        <text class="trace-col" x={c.x} y={20}>{c.words}</text>
      {/each}
      {#each model.links as l (l.id)}
        <path class="trace-link {l.cls}" class:lit={lit(l)} class:dim={linkDim(l)} d={path(l)} marker-end="url(#trace-arrow)">
          <title>{l.sentence}</title>
        </path>
      {/each}
      {#each model.nodes as n (n.id)}
        <g
          class="trace-node"
          class:gap={!!n.gap}
          class:picked={selected === n.id}
          class:dim={dimmed(n.id)}
          class:emph={emphasis.has(n.id)}
          transform={`translate(${n.x} ${n.y})`}
          role="button"
          tabindex="0"
          aria-pressed={selected === n.id}
          aria-label={sentence(n)}
          onclick={() => onselect(selected === n.id ? null : n.id)}
          onkeydown={(e) => key(e, n)}
        >
          <title>{sentence(n)}</title>
          <rect class="card-bg" width={BOX.w} height={BOX.h} rx="10" />
          {#if !n.gap}<rect class="bar" width="5" height={BOX.h} rx="2.5" style:fill={`oklch(58% 0.15 ${hue(n.kind)})`} />{/if}
          <text class="t-kind" x="14" y="16">{n.gap ? 'Missing link' : n.kind === 'code' ? kindWords(n.kind) : `${kindWords(n.kind)} · ${shortKey(n.key ?? '')}`}</text>
          <text class="t-title" x="14" y="33">{fit(n.title)}</text>
          {#if n.gap}
            <text class="t-note" x="14" y="47">Next step: ask {n.next}</text>
          {:else}
            {#if n.status}
              <g transform="translate(14 38)"><path class="glyph" d={GLYPH[look(n).shape] ?? GLYPH.hollow} /></g>
              <text class="t-note" x="30" y="47">{look(n).label}{n.jira ? ` · Jira ${n.jira}` : ''}</text>
            {:else if n.jira}
              <text class="t-note" x="14" y="47">Jira {n.jira}</text>
            {/if}
          {/if}
        </g>
      {/each}
    </svg>
  </div>
</div>
