import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const read = (name: string) => readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');

describe('the outline is beside every view of the graph page', () => {
  const page = read('routes/Graph.svelte');
  it('draws the outline pane whatever the view is', () => {
    expect(page).toMatch(/<aside class="outline-side"[^>]*><OutlinePane/);
    expect(page).not.toMatch(/\{#if view !== 'outline'\}<aside/);
  });
  it('shows what was chosen in the outline view, and the full tree on a narrow screen', () => {
    expect(page).toContain('<OutlineDetail');
    expect(page).toContain('class="outline-narrow"');
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
