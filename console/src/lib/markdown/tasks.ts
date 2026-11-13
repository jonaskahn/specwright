// Reads a plan's task list out of its parsed Markdown, so the preview can show tasks as cards or a
// table. Like the criteria reader it only derives: the file is untouched, and a task whose lines are
// not labelled keeps its original blocks.

import { plainOf } from './criteria';
import type { Block, Doc, Inline } from './parse';

export type Label = 'traces' | 'touches' | 'depends' | 'visuals' | 'done' | 'stop';

export interface Task {
  id: string;
  title: string;
  /** The word in a leading "[layer]" prefix, lower case, or null. */
  layer: string | null;
  /** Marked [P]: it can run in parallel with its neighbours. */
  parallel: boolean;
  fields: Partial<Record<Label, Inline[]>>;
  rest: Block[];
  line: number;
  end: number;
}

export interface TaskSection {
  heading: Block;
  lead: Block[];
  items: Task[];
  before: Block[];
  after: Block[];
}

/** The labels in the order a task card shows them, with the words on screen. */
export const LABELS: [Label, string][] = [
  ['done', 'Done when'],
  ['traces', 'Traces to'],
  ['depends', 'Depends on'],
  ['visuals', 'Visuals'],
  ['touches', 'Touches'],
  ['stop', 'Stop and ask if'],
];

const NAMES: Record<string, Label> = { 'traces to': 'traces', touches: 'touches', 'depends on': 'depends', visuals: 'visuals', 'done when': 'done', 'stop and ask if': 'stop' };
const ID = /^((?:[A-Z]{2,5}:)?TASK-(?:[A-Z]{2,5}-)?\d{3,4}-\d+)\s*(?:[—–:-]\s*)?(.*)$/;
const LABEL = /(?<![^\s])(Traces to|Touches|Depends on|Done when|Stop and ask if|Visuals):[ \t]*/;

/** Drop a trailing full stop and surrounding space from a value. */
function tidy(items: Inline[]): Inline[] {
  const c = [...items];
  const first = c[0];
  if (first?.t === 'text') c[0] = { t: 'text', v: first.v.replace(/^\s+/, '') };
  const last = c[c.length - 1];
  if (last?.t === 'text') c[c.length - 1] = { t: 'text', v: last.v.replace(/[\s]+$/, '') };
  return c.filter((i) => !(i.t === 'text' && i.v === ''));
}

/** Labelled values from one paragraph, which Markdown made of several joined lines. */
function labelled(c: Inline[]): Partial<Record<Label, Inline[]>> | null {
  const out: Partial<Record<Label, Inline[]>> = {};
  let current: Inline[] | null = null;
  for (const item of c) {
    if (item.t !== 'text') {
      if (!current) return null;
      current.push(item);
      continue;
    }
    const parts = item.v.split(LABEL);
    if (parts[0]) {
      if (current) current.push({ t: 'text', v: parts[0] });
      else if (parts[0].trim()) return null;
    }
    for (let i = 1; i < parts.length; i += 2) {
      current = parts[i + 1] ? [{ t: 'text', v: parts[i + 1] }] : [];
      out[NAMES[parts[i].toLowerCase()]] ??= current;
    }
  }
  return Object.keys(out).length ? (Object.fromEntries(Object.entries(out).map(([k, v]) => [k, tidy(v!)])) as Partial<Record<Label, Inline[]>>) : null;
}

function fieldsOf(block: Block): Partial<Record<Label, Inline[]>> | null {
  if (block.t === 'para') return labelled(block.c);
  if (block.t !== 'list' || block.ordered) return null;
  const out: Partial<Record<Label, Inline[]>> = {};
  for (const item of block.items) {
    const first = item.c[0];
    const found = first?.t === 'para' ? labelled(first.c) : null;
    if (!found) return null;
    Object.assign(out, found);
  }
  return out;
}

const headingText = (b: Block) => (b.t === 'heading' ? plainOf(b.c).trim() : '');

/** The "Tasks" section of a task file, or null when it has no task headings. */
export function findTasks(doc: Doc): TaskSection | null {
  const at = doc.blocks.findIndex((b) => b.t === 'heading' && b.level === 2 && /^tasks$/i.test(headingText(b)));
  if (at < 0) return null;
  let stop = doc.blocks.findIndex((b, i) => i > at && b.t === 'heading' && b.level <= 2);
  if (stop < 0) stop = doc.blocks.length;
  const lead: Block[] = [];
  const items: Task[] = [];
  for (const block of doc.blocks.slice(at + 1, stop)) {
    const match = block.t === 'heading' && block.level === 3 ? ID.exec(headingText(block)) : null;
    if (match && block.t === 'heading') {
      let title = match[2].trim();
      const layer = /^\[([A-Za-z-]+)\]\s*/.exec(title);
      if (layer) title = title.slice(layer[0].length);
      const parallel = /\s*\[P\]\s*$/.test(title);
      if (parallel) title = title.replace(/\s*\[P\]\s*$/, '');
      items.push({ id: match[1], title: title || match[1], layer: layer ? layer[1].toLowerCase() : null, parallel, fields: {}, rest: [], line: block.line, end: block.end });
      continue;
    }
    const current = items[items.length - 1];
    if (!current) {
      lead.push(block);
      continue;
    }
    current.end = Math.max(current.end, block.end);
    const found = current.rest.length === 0 ? fieldsOf(block) : null;
    if (found) Object.assign(current.fields, found);
    else current.rest.push(block);
  }
  if (items.length === 0) return null;
  return { heading: doc.blocks[at], lead, items, before: doc.blocks.slice(0, at), after: doc.blocks.slice(stop) };
}
