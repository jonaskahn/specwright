// Reads a story's acceptance criteria out of its parsed Markdown, so the preview can show them as
// cards or a table. Everything here is derived: the story file stays as written, and a criterion
// that does not read as Given/When/Then keeps its original blocks, so nothing is ever lost.

import type { Block, Doc, Inline } from './parse';

export type Keyword = 'Given' | 'When' | 'Then' | 'And' | 'But';
export type Tag = 'happy' | 'validation' | 'ui' | 'other';

export interface Step {
  kw: Keyword;
  c: Inline[];
}

export interface Criterion {
  id: string;
  title: string;
  /** First and last source line, so a preview aimed at a line can find its criterion. */
  line: number;
  end: number;
  steps: Step[];
  /** Blocks that are not steps: a criterion written as prose, or a note under the steps. */
  rest: Block[];
  tag: Tag;
  /** True when its Given is the shared background, shown once above the cards. */
  background: boolean;
}

export interface Section {
  heading: Block;
  /** Text between the heading and the first criterion. */
  lead: Block[];
  items: Criterion[];
  /** The Given that three or more criteria share, with the criteria it applies to. */
  background: { step: Step; ids: string[] } | null;
  before: Block[];
  after: Block[];
}

const KEYWORDS: Keyword[] = ['Given', 'When', 'Then', 'And', 'But'];
const ID = /^((?:[A-Z]{2,5}:)?AC-(?:[A-Z]{2,5}-)?\d{3,4}(?:-\d+)?)\s*(?:[—–:-]\s*)?(.*)$/;
const SHARED = 3;

export function plainOf(items: Inline[]): string {
  return items
    .map((i) => {
      if (i.t === 'text' || i.t === 'code') return i.v;
      if (i.t === 'ref') return i.id;
      if (i.t === 'image') return i.alt;
      return plainOf(i.c);
    })
    .join('');
}

const asKeyword = (text: string): Keyword | null => KEYWORDS.find((k) => k.toLowerCase() === text.trim().replace(/:$/, '').toLowerCase()) ?? null;

/** Drop the closing punctuation of a step, so "…is Active." reads like the rest. */
function tidy(step: Step): Step {
  const c = [...step.c];
  const first = c[0];
  if (first?.t === 'text') c[0] = { t: 'text', v: first.v.replace(/^\s+/, '') };
  const last = c[c.length - 1];
  if (last?.t === 'text') c[c.length - 1] = { t: 'text', v: last.v.replace(/[\s,;.]+$/, '') };
  return { kw: step.kw, c };
}

/** The steps of one list item, when its first words are a keyword (bold or plain). */
function fromItem(c: Inline[]): Step | null {
  const [head, ...tail] = c;
  if (!head) return null;
  if (head.t === 'strong') {
    const kw = asKeyword(plainOf(head.c));
    return kw ? tidy({ kw, c: tail }) : null;
  }
  if (head.t === 'text') {
    const match = /^\s*(Given|When|Then|And|But)\b[\s:,]*/.exec(head.v);
    return match ? tidy({ kw: match[1] as Keyword, c: [{ t: 'text', v: head.v.slice(match[0].length) }, ...tail] }) : null;
  }
  return null;
}

/** A paragraph that holds several steps, because Markdown joined its lines: split at each keyword. */
function fromPara(c: Inline[]): Step[] | null {
  const out: Step[] = [];
  let current: Step | null = null;
  for (const item of c) {
    if (item.t !== 'text') {
      if (!current) return null;
      current.c.push(item);
      continue;
    }
    const parts = item.v.split(/(?<![^\s,;])(Given|When|Then|And|But)(?=\s)/);
    if (parts[0]) {
      if (current) current.c.push({ t: 'text', v: parts[0] });
      else if (parts[0].trim()) return null;
    }
    for (let i = 1; i < parts.length; i += 2) {
      current = { kw: parts[i] as Keyword, c: parts[i + 1] ? [{ t: 'text', v: parts[i + 1] }] : [] };
      out.push(current);
    }
  }
  const steps = out.map(tidy);
  return steps.length > 0 && (steps[0].kw === 'Given' || steps[0].kw === 'When') ? steps : null;
}

/** Steps taken from a block, or null when the block is not made of steps. */
function stepsOf(block: Block): Step[] | null {
  if (block.t === 'para') return fromPara(block.c);
  if (block.t !== 'list' || block.ordered) return null;
  const found: Step[] = [];
  for (const item of block.items) {
    const first = item.c[0];
    const step = first?.t === 'para' ? fromItem(first.c) : null;
    if (!step || item.c.length > 1) return null;
    found.push(step);
  }
  return found;
}

const REFUSED = /\b(refus\w*|reject\w*|invalid|errors?|blank|mismatch\w*|too[- ](?:short|long)|expired|not allowed|denied|fails?|failed|missing|required|exceeds?|duplicate|nothing is saved|not (?:saved|created|sent))\b/i;
const INTERFACE = /\b(shown|displayed|visible|hidden|label|disabled|enabled|read-?only|cannot be edited|icon|placeholder|layout|focus)\b/i;
const DISPLAY = /\b(is|are) (?:displayed|shown|rendered|visible)\b/i;

/**
 * A coarse kind for a criterion. A refusal or an error is validation; a display rule is the
 * interface; any other readable criterion is the main flow; one that did not read as steps is other.
 */
export function tagOf(title: string, steps: Step[] = []): Tag {
  const outcome = steps.filter((s) => s.kw !== 'Given' && s.kw !== 'When').map((s) => plainOf(s.c));
  if (REFUSED.test(title) || outcome.some((t) => REFUSED.test(t))) return 'validation';
  const action = steps.find((s) => s.kw === 'When');
  if (INTERFACE.test(title) || (action && DISPLAY.test(plainOf(action.c)))) return 'ui';
  return steps.length > 0 ? 'happy' : 'other';
}

/**
 * When three or more criteria open with the same Given, show it once. The cards that used it lose
 * the line, and the block above them names which ones it applies to.
 */
export function hoist(items: Criterion[]): { items: Criterion[]; background: Section['background'] } {
  const counts = new Map<string, number>();
  const first = (c: Criterion) => c.steps.find((s) => s.kw === 'Given');
  for (const c of items) {
    const given = first(c);
    if (given) {
      const key = plainOf(given.c).toLowerCase().replace(/\s+/g, ' ').trim();
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  const [top] = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  if (!top || top[1] < SHARED) return { items, background: null };
  const same = (c: Criterion) => {
    const given = first(c);
    return !!given && plainOf(given.c).toLowerCase().replace(/\s+/g, ' ').trim() === top[0];
  };
  let step: Step | null = null;
  const ids: string[] = [];
  const next = items.map((c) => {
    if (!same(c)) return c;
    const given = first(c)!;
    step ??= given;
    ids.push(c.id);
    return { ...c, background: true, steps: c.steps.filter((s) => s !== given) };
  });
  return { items: next, background: step ? { step, ids } : null };
}

const headingText = (b: Block) => (b.t === 'heading' ? plainOf(b.c).trim() : '');

/** The "Acceptance criteria" section of a story as criteria, or null when it has none. */
export function findCriteria(doc: Doc): Section | null {
  const at = doc.blocks.findIndex((b) => b.t === 'heading' && b.level === 2 && /^acceptance criteria$/i.test(headingText(b)));
  if (at < 0) return null;
  let stop = doc.blocks.findIndex((b, i) => i > at && b.t === 'heading' && b.level <= 2);
  if (stop < 0) stop = doc.blocks.length;
  const lead: Block[] = [];
  const items: Criterion[] = [];
  for (const block of doc.blocks.slice(at + 1, stop)) {
    const match = block.t === 'heading' && block.level === 3 ? ID.exec(headingText(block)) : null;
    if (match && block.t === 'heading') {
      items.push({ id: match[1], title: match[2].trim() || match[1], line: block.line, end: block.end, steps: [], rest: [], tag: 'other', background: false });
      continue;
    }
    const current = items[items.length - 1];
    if (!current) {
      lead.push(block);
      continue;
    }
    current.end = Math.max(current.end, block.end);
    const steps = current.rest.length === 0 ? stepsOf(block) : null;
    if (steps) current.steps.push(...steps);
    else current.rest.push(block);
  }
  if (items.length === 0) return null;
  for (const c of items) c.tag = tagOf(c.title, c.steps);
  const { items: shaped, background } = hoist(items);
  return { heading: doc.blocks[at], lead, items: shaped, background, before: doc.blocks.slice(0, at), after: doc.blocks.slice(stop) };
}

export type Piece = { t: 'value'; v: string } | { t: 'inline'; item: Inline };

const VALUE = /(["“][^"“”\n]{1,80}["”])/;

/** A step's inlines with each quoted value picked out, so it can be drawn as a chip. */
export function valuesOf(items: Inline[]): Piece[] {
  return items.flatMap((item): Piece[] => {
    if (item.t !== 'text') return [{ t: 'inline', item }];
    return item.v
      .split(VALUE)
      .filter((part) => part !== '')
      .map((part): Piece => (VALUE.test(part) && part.length > 2 ? { t: 'value', v: part } : { t: 'inline', item: { t: 'text', v: part } }));
  });
}

/** One step per column for the table: Given, When, and Then with its And and But lines. */
export function columns(steps: Step[]): { given: Step[]; when: Step[]; then: Step[] } {
  const out = { given: [] as Step[], when: [] as Step[], then: [] as Step[] };
  let into: keyof typeof out = 'given';
  for (const step of steps) {
    if (step.kw === 'Given') into = 'given';
    else if (step.kw === 'When') into = 'when';
    else if (step.kw === 'Then') into = 'then';
    out[into].push(step);
  }
  return out;
}
