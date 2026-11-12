// Motion helpers shared by the graph views. Every duration passes through `ms`, so a person who
// asked their system for reduced motion gets the same state changes with no movement.

import { cubicOut } from 'svelte/easing';

export const calm = (): boolean => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
export const ms = (n: number): number => (calm() ? 0 : n);

/**
 * An `animate:` function for items inside a scaled drawing: it slides an item from where it was
 * to where it is, counting the zoom, because the browser reports screen pixels and the drawing
 * moves in its own units. (`flip` assumes the two are the same.)
 */
export function glide(_node: Element, { from, to }: { from: DOMRect; to: DOMRect }, { zoom = 1, duration = 260 }: { zoom?: number; duration?: number } = {}) {
  const dx = (from.left - to.left) / zoom;
  const dy = (from.top - to.top) / zoom;
  return {
    duration: ms(duration),
    easing: cubicOut,
    css: (_t: number, u: number) => `transform: translate(${dx * u}px, ${dy * u}px);`,
  };
}
