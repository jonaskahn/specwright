<script lang="ts">
  import { onDestroy } from 'svelte';
  import type { Simulation } from 'd3-force';
  import type { GraphEdge, GraphNode } from '../../contract/types';
  import { build, hue, simulate, type Link, type Vertex } from '../lib/graph/layout';
  import { kindWords } from '../lib/vocabulary';

  let {
    nodes,
    edges,
    selected = null,
    highlight = new Set<string>(),
    onselect,
  }: { nodes: GraphNode[]; edges: GraphEdge[]; selected?: string | null; highlight?: Set<string>; onselect: (key: string | null) => void } = $props();

  let canvas: HTMLCanvasElement | undefined = $state();
  let vertices: Vertex[] = [];
  let links: Link[] = [];
  let sim: Simulation<Vertex, Link> | null = null;
  let view = { x: 0, y: 0, k: 1 };
  let width = 0;
  let height = 0;
  let frame = 0;
  let touched = false;
  /** The layout has been framed once; later reheats from the mouse never move the view. */
  let framed = false;
  /** The item under the pointer, and the items it links to; they stay lit while the rest fades. */
  let hover: string | null = null;
  let near = new Map<string, Set<string>>();
  let cursor = $state<'grab' | 'grabbing' | 'pointer'>('grab');
  let tip = $state<{ x: number; y: number; kind: string; title: string; key: string; links: number } | null>(null);
  /** Where the pointer is in the layout; items close to it step aside a little. */
  const field = { x: 0, y: 0, on: false };
  const PUSH = { radius: 64, force: 0.9 };
  const calm = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  const css = (name: string) => (canvas ? getComputedStyle(canvas).getPropertyValue(name).trim() : '#888');

  function rebuild() {
    sim?.stop();
    const previous = new Map(vertices.map((v) => [v.key, v]));
    ({ vertices, links } = build(nodes, edges, previous));
    near = new Map();
    for (const l of links) {
      const a = (l.source as Vertex).key;
      const b = (l.target as Vertex).key;
      near.set(a, (near.get(a) ?? new Set()).add(b));
      near.set(b, (near.get(b) ?? new Set()).add(a));
    }
    hover = null;
    tip = null;
    touched = false;
    framed = false;
    sim = simulate(vertices, links, schedule);
    sim.force('pointer', (alpha: number) => {
      if (!field.on || !alpha) return;
      for (const v of vertices) {
        const dx = (v.x ?? 0) - field.x;
        const dy = (v.y ?? 0) - field.y;
        const d = Math.hypot(dx, dy);
        if (d > 0.1 && d < PUSH.radius) {
          const f = (1 - d / PUSH.radius) * PUSH.force;
          v.vx = (v.vx ?? 0) + (dx / d) * f;
          v.vy = (v.vy ?? 0) + (dy / d) * f;
        }
      }
    });
    sim.on('end', fit);
    sim.alpha(0.9).restart();
    schedule();
  }

  /** Frame the settled layout, unless the person has already panned or zoomed. */
  function fit() {
    if (touched || framed || !vertices.length || !width || !height) return;
    framed = true;
    const xs = vertices.map((v) => v.x ?? 0);
    const ys = vertices.map((v) => v.y ?? 0);
    const dx = Math.max(...xs) - Math.min(...xs) + 80;
    const dy = Math.max(...ys) - Math.min(...ys) + 80;
    const k = Math.min(2.2, Math.max(0.2, 0.9 * Math.min(width / dx, height / dy)));
    view = { k, x: -k * (Math.max(...xs) + Math.min(...xs)) / 2, y: -k * (Math.max(...ys) + Math.min(...ys)) / 2 };
    schedule();
  }

  function schedule() {
    if (!frame) frame = requestAnimationFrame(() => { frame = 0; draw(); });
  }

  function color(kind: string, alpha = 1) {
    return `oklch(58% 0.15 ${hue(kind)} / ${alpha})`;
  }

  function shape(ctx: CanvasRenderingContext2D, v: Vertex) {
    const { x = 0, y = 0 } = v;
    const r = v.key === hover ? v.r * 1.3 : v.r;
    ctx.beginPath();
    if (v.kind === 'task') ctx.rect(x - r, y - r, r * 2, r * 2);
    else if (['q', 'dec', 'cr', 'amendment', 'risk'].includes(v.kind)) { ctx.moveTo(x, y - r * 1.2); ctx.lineTo(x + r * 1.15, y + r * 0.9); ctx.lineTo(x - r * 1.15, y + r * 0.9); ctx.closePath(); }
    else if (['epic', 'bo', 'idea'].includes(v.kind)) { ctx.moveTo(x, y - r * 1.2); ctx.lineTo(x + r * 1.2, y); ctx.lineTo(x, y + r * 1.2); ctx.lineTo(x - r * 1.2, y); ctx.closePath(); }
    else ctx.arc(x, y, r, 0, Math.PI * 2);
  }

  function draw() {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.translate(width / 2 + view.x, height / 2 + view.y);
    ctx.scale(view.k, view.k);
    const focus = hover ? new Set([hover, ...(near.get(hover) ?? [])]) : highlight;
    const dim = focus.size > 0;
    const touching = (s: Vertex, t: Vertex) => (hover ? s.key === hover || t.key === hover : dim && focus.has(s.key) && focus.has(t.key));
    const rule = css('--rule-strong') || '#999';
    for (const l of links) {
      const s = l.source as Vertex;
      const t = l.target as Vertex;
      const lit = touching(s, t);
      ctx.globalAlpha = dim && !lit ? 0.12 : l.cls === 'mentioned' ? 0.5 : 0.9;
      ctx.strokeStyle = lit ? css('--accent') : rule;
      ctx.lineWidth = (lit ? 2 : l.cls === 'structural' ? 1.4 : 1) / view.k;
      ctx.setLineDash(l.cls === 'mentioned' ? [3 / view.k, 3 / view.k] : []);
      ctx.beginPath();
      ctx.moveTo(s.x ?? 0, s.y ?? 0);
      ctx.lineTo(t.x ?? 0, t.y ?? 0);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    if (links.length < 700) {
      // Arrowheads: each link points the way the data states it (a feature serves an objective).
      for (const l of links) {
        const s = l.source as Vertex;
        const t = l.target as Vertex;
        const dx = (t.x ?? 0) - (s.x ?? 0);
        const dy = (t.y ?? 0) - (s.y ?? 0);
        const len = Math.hypot(dx, dy);
        if (len < t.r * 2.5) continue;
        const lit = touching(s, t);
        const ux = dx / len;
        const uy = dy / len;
        const tipX = (t.x ?? 0) - ux * (t.r + 1);
        const tipY = (t.y ?? 0) - uy * (t.r + 1);
        const size = 5 / Math.min(Math.max(view.k, 0.6), 2);
        ctx.globalAlpha = dim && !lit ? 0.12 : l.cls === 'mentioned' ? 0.4 : 0.85;
        ctx.fillStyle = lit ? css('--accent') : rule;
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(tipX - ux * size - uy * size * 0.5, tipY - uy * size + ux * size * 0.5);
        ctx.lineTo(tipX - ux * size + uy * size * 0.5, tipY - uy * size - ux * size * 0.5);
        ctx.closePath();
        ctx.fill();
      }
    }
    const ink = css('--ink');
    ctx.font = `${11 / Math.min(view.k, 1.4)}px ${css('--font-body') || 'sans-serif'}`;
    ctx.textAlign = 'center';
    for (const v of vertices) {
      const lit = !dim || focus.has(v.key);
      ctx.globalAlpha = lit ? 1 : 0.18;
      shape(ctx, v);
      ctx.fillStyle = color(v.kind);
      ctx.fill();
      if (v.key === selected || v.key === hover || (dim && focus.has(v.key))) {
        ctx.lineWidth = 2.2 / view.k;
        ctx.strokeStyle = v.key === selected || v.key === hover ? ink : css('--accent');
        ctx.stroke();
      }
      if (v.key === selected || v.key === hover || (lit && (view.k > 1.4 || (dim && focus.size < 14)))) {
        ctx.fillStyle = ink;
        ctx.fillText(v.key.replace(/^[A-Z][A-Z0-9]*:/, ''), v.x ?? 0, (v.y ?? 0) - v.r * (v.key === hover ? 1.3 : 1) - 5);
      }
    }
    ctx.globalAlpha = 1;
  }

  function resize() {
    if (!canvas) return;
    const box = canvas.getBoundingClientRect();
    width = box.width;
    height = box.height;
    const dpr = devicePixelRatio || 1;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    schedule();
  }

  function world(e: PointerEvent | WheelEvent) {
    const box = canvas!.getBoundingClientRect();
    return { x: (e.clientX - box.left - width / 2 - view.x) / view.k, y: (e.clientY - box.top - height / 2 - view.y) / view.k };
  }

  function hit(e: PointerEvent): string | null {
    const p = world(e);
    let best: Vertex | null = null;
    let bestD = Infinity;
    for (const v of vertices) {
      const d = Math.hypot((v.x ?? 0) - p.x, (v.y ?? 0) - p.y);
      if (d < v.r + 5 / view.k && d < bestD) { best = v; bestD = d; }
    }
    return best?.key ?? null;
  }

  let drag: { x: number; y: number; moved: boolean; node: Vertex | null } | null = null;
  function down(e: PointerEvent) {
    touched = true;
    canvas!.setPointerCapture(e.pointerId);
    const key = hit(e);
    const node = key ? (vertices.find((v) => v.key === key) ?? null) : null;
    if (node) {
      node.fx = node.x;
      node.fy = node.y;
      if (!calm()) sim?.alphaTarget(0.2).restart();
    }
    drag = { x: e.clientX, y: e.clientY, moved: false, node };
    cursor = 'grabbing';
    field.on = false;
  }
  function move(e: PointerEvent) {
    if (!drag) {
      const key = hit(e);
      const p = world(e);
      const box = canvas!.getBoundingClientRect();
      field.x = p.x;
      field.y = p.y;
      field.on = !key && !calm();
      if (field.on && sim && sim.alpha() < 0.05) sim.alpha(0.06).restart();
      if (key !== hover) {
        hover = key;
        cursor = key ? 'pointer' : 'grab';
      }
      const v = key ? vertices.find((x) => x.key === key) : null;
      tip = v ? { x: Math.min(e.clientX - box.left + 18, Math.max(0, width - 240)), y: e.clientY - box.top + 20, kind: kindWords(v.kind), title: v.title, key: v.key, links: near.get(v.key)?.size ?? 0 } : null;
      schedule();
      return;
    }
    const dx = e.clientX - drag.x;
    const dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    if (drag.node) {
      const p = world(e);
      drag.node.fx = p.x;
      drag.node.fy = p.y;
      if (calm()) {
        drag.node.x = p.x;
        drag.node.y = p.y;
      }
    } else {
      view.x += dx;
      view.y += dy;
    }
    drag.x = e.clientX;
    drag.y = e.clientY;
    schedule();
  }
  function up(e: PointerEvent) {
    if (drag && !drag.moved) onselect(hit(e));
    if (drag?.node) {
      drag.node.fx = null;
      drag.node.fy = null;
      sim?.alphaTarget(0);
    }
    drag = null;
    cursor = hover ? 'pointer' : 'grab';
  }
  function leave() {
    field.on = false;
    hover = null;
    tip = null;
    if (!drag) cursor = 'grab';
    schedule();
  }
  function wheel(e: WheelEvent) {
    e.preventDefault();
    touched = true;
    const before = world(e);
    view.k = Math.min(6, Math.max(0.2, view.k * Math.exp(-e.deltaY * 0.0015)));
    const box = canvas!.getBoundingClientRect();
    view.x = e.clientX - box.left - width / 2 - before.x * view.k;
    view.y = e.clientY - box.top - height / 2 - before.y * view.k;
    schedule();
  }
  function reset() { touched = false; framed = false; fit(); }

  $effect(() => {
    void nodes; void edges;
    if (canvas) rebuild();
  });
  $effect(() => { void selected; void highlight; schedule(); });
  $effect(() => {
    if (!canvas) return;
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    return () => observer.disconnect();
  });
  onDestroy(() => { sim?.stop(); cancelAnimationFrame(frame); });
</script>

<!-- svelte-ignore a11y_no_interactive_element_to_noninteractive_role -->
<canvas
  bind:this={canvas}
  aria-label={`Network of ${nodes.length} items and ${edges.length} links. A table and a trace map of the same items are available.`}
  role="img"
  onpointerdown={down}
  onpointermove={move}
  onpointerup={up}
  onpointerleave={leave}
  style:cursor={cursor}
  onwheel={wheel}
  ondblclick={reset}
></canvas>
{#if tip}
  <div class="graph-tip" role="presentation" style:left={`${tip.x}px`} style:top={`${tip.y}px`}>
    <p class="sub">{tip.kind} · <span class="mono">{tip.key.replace(/^[A-Z][A-Z0-9]*:/, '')}</span></p>
    <strong>{tip.title}</strong>
    <p class="sub">{tip.links} {tip.links === 1 ? 'link' : 'links'}</p>
  </div>
{/if}
