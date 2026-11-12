import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const read = (name: string) => readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');

describe('the outline sits beside the trace and the network only', () => {
  const page = read('routes/Graph.svelte');
  it('draws the outline pane for those two views', () => {
    expect(page).toContain("const withOutline = $derived(view === 'trace' || view === 'network')");
    expect(page).toMatch(/\{#if withOutline\}<aside class="outline-side"[^>]*><OutlinePane/);
  });
  it('leaves the table and the outline view as whole pages', () => {
    expect(page).not.toContain('OutlineDetail');
    expect(page).not.toContain('outline-narrow');
  });
});

describe('the network answers the pointer', () => {
  const canvas = read('components/GraphCanvas.svelte');
  it('lights the item under the pointer with its neighbours and says what it is', () => {
    expect(canvas).toContain('onpointerleave');
    expect(canvas).toContain('class="graph-tip"');
    expect(canvas).toMatch(/hover \? s\.key === hover \|\| t\.key === hover/);
  });
  it('lets items step aside from the pointer and be dragged, and stays still when asked to', () => {
    expect(canvas).toContain("sim.force('pointer'");
    expect(canvas).toContain('prefers-reduced-motion');
    expect(canvas).toContain('node.fx');
  });
});

describe('the outline folds criteria and tasks under their feature', () => {
  const node = read('components/OutlineNode.svelte');
  const pane = read('components/OutlinePane.svelte');
  it('opens only the project and its epics by default', () => {
    expect(node).toContain("expand === 'auto' && depth < 2");
  });
  it('draws nothing below a closed branch, and slides the rest in and out', () => {
    expect(node).toMatch(/\{#if open\}\s*<ul transition:slide/);
    expect(node).toContain('animate:flip');
  });
  it('opens the chosen feature and closes what was opened by hand before', () => {
    expect(pane).toContain('[...trail, selected]');
    expect(pane).toMatch(/void selected;\s*marks = new Map\(\)/);
  });
});

describe('the trace map moves with its model', () => {
  const map = read('components/TraceMap.svelte');
  it('uses svelte transitions and an animate function, each on its own layer', () => {
    expect(map).toContain("from 'svelte/transition'");
    expect(map).toContain('animate:glide');
    expect(map).toMatch(/class="trace-node"[^>]*in:fly=\{enter\(n, 'in'\)\} out:fly=\{enter\(n, 'out'\)\}/);
    expect(map).not.toMatch(/class="trace-node"[^>]*transform=/);
  });
  it('honours reduced motion through one helper', () => {
    const motion = read('lib/motion.ts');
    expect(motion).toContain('prefers-reduced-motion: reduce');
    expect(map).not.toMatch(/duration: \d+[,}]/);
  });
});
