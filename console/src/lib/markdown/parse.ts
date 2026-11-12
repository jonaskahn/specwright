// A small Markdown reader for the preview panel. It turns text into a tree of plain values; the
// components draw that tree as elements. Nothing here produces HTML, and raw HTML in a document
// stays text, so a document can never inject markup or script into the console.

export type Inline =
  | { t: 'text'; v: string }
  | { t: 'code'; v: string }
  | { t: 'em' | 'strong'; c: Inline[] }
  | { t: 'link'; href: string; c: Inline[] }
  | { t: 'image'; src: string; alt: string }
  | { t: 'ref'; id: string };

export interface Span {
  /** First and last source line of the block, 1-based, front matter included. */
  line: number;
  end: number;
}

export interface Item extends Span {
  /** null for a plain item, true or false for a task item. */
  checked: boolean | null;
  c: Block[];
}

export type Align = 'left' | 'center' | 'right' | null;

export type Block =
  | ({ t: 'heading'; level: number; id: string; c: Inline[] } & Span)
  | ({ t: 'para'; c: Inline[] } & Span)
  | ({ t: 'list'; ordered: boolean; items: Item[] } & Span)
  | ({ t: 'quote'; c: Block[] } & Span)
  | ({ t: 'code'; lang: string; v: string } & Span)
  | ({ t: 'table'; head: Inline[][]; align: Align[]; rows: Inline[][][] } & Span)
  | ({ t: 'rule' } & Span)
  | ({ t: 'raw'; v: string } & Span);

export interface OutlineEntry {
  level: number;
  id: string;
  text: string;
  line: number;
}

export interface Doc {
  /** Front matter as key and value pairs, or null when the file has none. */
  meta: [string, string][] | null;
  metaEnd: number;
  blocks: Block[];
  /** Headings of level one to three, for the table of contents. */
  outline: OutlineEntry[];
  lines: number;
}

// The kinds of identifier a spec uses, with an optional project prefix: REF:FEAT-001, AC-001-2.
const REF = /(?<![\w-])(?:[A-Z]{2,5}:)?(?:FEAT|AC|TASK|BR|NFR|FR|BO|EPIC|Q|DEC|CR|SRC|ASSET|AMD|STK|IDEA)-(?:[A-Z]{2,5}-)?\d{3,4}(?:-\d+)?(?![\w-])/g;

function plain(inline: Inline[]): string {
  return inline
    .map((i) => {
      if (i.t === 'text' || i.t === 'code') return i.v;
      if (i.t === 'ref') return i.id;
      if (i.t === 'image') return i.alt;
      return plain(i.c);
    })
    .join('');
}

function withRefs(text: string): Inline[] {
  const out: Inline[] = [];
  let at = 0;
  for (const m of text.matchAll(REF)) {
    if (m.index > at) out.push({ t: 'text', v: text.slice(at, m.index) });
    out.push({ t: 'ref', id: m[0] });
    at = m.index + m[0].length;
  }
  if (at < text.length) out.push({ t: 'text', v: text.slice(at) });
  return out;
}

/** Index of the bracket that closes the one at `open`, skipping nested pairs and escapes. */
function close(text: string, open: number, a: string, b: string): number {
  let depth = 0;
  for (let i = open; i < text.length; i++) {
    if (text[i] === '\\') i++;
    else if (text[i] === a) depth++;
    else if (text[i] === b && --depth === 0) return i;
  }
  return -1;
}

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let buffer = '';
  const flush = () => {
    if (buffer) out.push(...withRefs(buffer));
    buffer = '';
  };
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (ch === '\\' && i + 1 < text.length && /[\\`*_{}[\]()#+\-.!|<>~]/.test(text[i + 1])) {
      buffer += text[i + 1];
      i += 2;
      continue;
    }
    if (ch === '`') {
      const run = /^`+/.exec(text.slice(i))![0];
      const end = text.indexOf(run, i + run.length);
      if (end > 0) {
        flush();
        out.push({ t: 'code', v: text.slice(i + run.length, end).replace(/^ (.*) $/, '$1') });
        i = end + run.length;
        continue;
      }
    }
    if (ch === '!' && text[i + 1] === '[') {
      const end = close(text, i + 1, '[', ']');
      if (end > 0 && text[end + 1] === '(') {
        const stop = close(text, end + 1, '(', ')');
        if (stop > 0) {
          flush();
          out.push({ t: 'image', alt: text.slice(i + 2, end), src: text.slice(end + 2, stop).trim().split(/\s+/)[0] });
          i = stop + 1;
          continue;
        }
      }
    }
    if (ch === '[') {
      const end = close(text, i, '[', ']');
      if (end > 0 && text[end + 1] === '(') {
        const stop = close(text, end + 1, '(', ')');
        if (stop > 0) {
          flush();
          out.push({ t: 'link', href: text.slice(end + 2, stop).trim().split(/\s+/)[0], c: parseInline(text.slice(i + 1, end)) });
          i = stop + 1;
          continue;
        }
      }
    }
    if (ch === '<') {
      const auto = /^<((?:https?|mailto):[^\s<>]+)>/.exec(text.slice(i));
      if (auto) {
        flush();
        out.push({ t: 'link', href: auto[1], c: [{ t: 'text', v: auto[1] }] });
        i += auto[0].length;
        continue;
      }
    }
    if ((ch === '*' || ch === '_') && text[i + 1] !== ' ') {
      const strong = text[i + 1] === ch;
      const mark = strong ? ch + ch : ch;
      const from = i + mark.length;
      let end = text.indexOf(mark, from);
      while (end > 0 && (text[end - 1] === ' ' || (ch === '_' && /\w/.test(text[end + mark.length] ?? '')))) end = text.indexOf(mark, end + 1);
      const wordy = ch === '_' && /\w/.test(text[i - 1] ?? '');
      if (end > from && !wordy) {
        flush();
        out.push({ t: strong ? 'strong' : 'em', c: parseInline(text.slice(from, end)) });
        i = end + mark.length;
        continue;
      }
    }
    buffer += ch;
    i++;
  }
  flush();
  return out;
}

const FENCE = /^\s{0,3}(`{3,}|~{3,})\s*([^\s`]*)/;
const HEADING = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
const RULE = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
const MARKER = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
const QUOTE = /^\s{0,3}>\s?/;
const RAW = /^\s*<\/?[A-Za-z!][^>]*>?/;
const DELIM = /^\s*\|?\s*:?-{1,}:?\s*(?:\|\s*:?-{1,}:?\s*)*\|?\s*$/;

function cells(row: string): string[] {
  const body = row.trim().replace(/^\|/, '').replace(/\|$/, '');
  const out: string[] = [];
  let current = '';
  for (let i = 0; i < body.length; i++) {
    if (body[i] === '\\' && body[i + 1] === '|') {
      current += '|';
      i++;
    } else if (body[i] === '|') {
      out.push(current.trim());
      current = '';
    } else current += body[i];
  }
  out.push(current.trim());
  return out;
}

const indentOf = (line: string) => /^ */.exec(line.replace(/\t/g, '    '))![0].length;

function startsBlock(line: string, next: string | undefined): boolean {
  return FENCE.test(line) || HEADING.test(line) || RULE.test(line) || QUOTE.test(line) || MARKER.test(line) || RAW.test(line) || (line.includes('|') && next !== undefined && DELIM.test(next) && next.includes('-'));
}

function parseBlocks(lines: string[], first: number, slug: (text: string) => string): Block[] {
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const at = first + i;
    if (!line.trim()) {
      i++;
      continue;
    }
    const fence = FENCE.exec(line);
    if (fence) {
      const body: string[] = [];
      let j = i + 1;
      while (j < lines.length && !new RegExp(`^\\s{0,3}${fence[1][0]}{${fence[1].length},}\\s*$`).test(lines[j])) body.push(lines[j++]);
      blocks.push({ t: 'code', lang: fence[2], v: body.join('\n'), line: at, end: first + Math.min(j, lines.length - 1) });
      i = j + 1;
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) {
      const c = parseInline(heading[2]);
      blocks.push({ t: 'heading', level: heading[1].length, id: slug(plain(c)), c, line: at, end: at });
      i++;
      continue;
    }
    if (RULE.test(line)) {
      blocks.push({ t: 'rule', line: at, end: at });
      i++;
      continue;
    }
    if (line.includes('|') && i + 1 < lines.length && DELIM.test(lines[i + 1]) && lines[i + 1].includes('-')) {
      const head = cells(line);
      const align = cells(lines[i + 1]).map((c): Align => (c.startsWith(':') && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : c.startsWith(':') ? 'left' : null));
      const rows: Inline[][][] = [];
      let j = i + 2;
      while (j < lines.length && lines[j].trim() && lines[j].includes('|')) rows.push(cells(lines[j++]).map(parseInline));
      blocks.push({ t: 'table', head: head.map(parseInline), align, rows, line: at, end: first + j - 1 });
      i = j;
      continue;
    }
    if (QUOTE.test(line)) {
      const inner: string[] = [];
      let j = i;
      while (j < lines.length && lines[j].trim() && (QUOTE.test(lines[j]) || !startsBlock(lines[j], lines[j + 1]))) inner.push(lines[j++].replace(QUOTE, ''));
      blocks.push({ t: 'quote', c: parseBlocks(inner, at, slug), line: at, end: first + j - 1 });
      i = j;
      continue;
    }
    const marker = MARKER.exec(line);
    if (marker) {
      const base = indentOf(line);
      const ordered = /\d/.test(marker[2]);
      const items: Item[] = [];
      let j = i;
      while (j < lines.length) {
        const m = MARKER.exec(lines[j]);
        if (!m || indentOf(lines[j]) !== base || /\d/.test(m[2]) !== ordered) break;
        const body = [m[3]];
        let k = j + 1;
        while (k < lines.length) {
          const next = lines[k];
          if (!next.trim()) {
            const after = lines.slice(k + 1).find((l) => l.trim());
            if (after !== undefined && indentOf(after) > base) {
              body.push('');
              k++;
              continue;
            }
            break;
          }
          if (indentOf(next) <= base) break;
          body.push(next.replace(new RegExp(`^ {0,${base + 2}}`), ''));
          k++;
        }
        let checked: boolean | null = null;
        const task = /^\[([ xX])\]\s+(.*)$/.exec(body[0]);
        if (task) {
          checked = task[1] !== ' ';
          body[0] = task[2];
        }
        items.push({ checked, c: parseBlocks(body, first + j, slug), line: first + j, end: first + k - 1 });
        j = k;
        while (j < lines.length && !lines[j].trim()) j++;
        if (j < lines.length && !(MARKER.test(lines[j]) && indentOf(lines[j]) === base)) break;
      }
      blocks.push({ t: 'list', ordered, items, line: at, end: items[items.length - 1].end });
      i = j;
      continue;
    }
    if (RAW.test(line)) {
      const body: string[] = [];
      let j = i;
      while (j < lines.length && lines[j].trim()) body.push(lines[j++]);
      blocks.push({ t: 'raw', v: body.join('\n'), line: at, end: first + j - 1 });
      i = j;
      continue;
    }
    const body = [line.trim()];
    let j = i + 1;
    while (j < lines.length && lines[j].trim() && !startsBlock(lines[j], lines[j + 1])) body.push(lines[j++].trim());
    blocks.push({ t: 'para', c: parseInline(body.join(' ')), line: at, end: first + j - 1 });
    i = j;
  }
  return blocks;
}

function frontMatter(lines: string[]): { meta: [string, string][] | null; end: number } {
  if (lines[0]?.trim() !== '---') return { meta: null, end: 0 };
  const stop = lines.findIndex((l, i) => i > 0 && l.trim() === '---');
  if (stop < 0) return { meta: null, end: 0 };
  const meta: [string, string][] = [];
  for (const line of lines.slice(1, stop)) {
    const pair = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(line);
    if (pair) meta.push([pair[1], pair[2].replace(/^\[(.*)\]$/, '$1').replace(/^["'](.*)["']$/, '$1')]);
    else if (meta.length && /^\s*-\s+/.test(line)) {
      const last = meta[meta.length - 1];
      last[1] = last[1] ? `${last[1]}, ${line.replace(/^\s*-\s+/, '')}` : line.replace(/^\s*-\s+/, '');
    }
  }
  return { meta, end: stop + 1 };
}

export function parseMarkdown(text: string): Doc {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const { meta, end } = frontMatter(lines);
  const seen = new Map<string, number>();
  const slug = (value: string) => {
    const base = value.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').trim().replace(/\s+/g, '-') || 'section';
    const n = seen.get(base) ?? 0;
    seen.set(base, n + 1);
    return n ? `${base}-${n}` : base;
  };
  const blocks = parseBlocks(lines.slice(end), end + 1, slug);
  const outline: OutlineEntry[] = [];
  const walk = (list: Block[]) => {
    for (const b of list) if (b.t === 'heading' && b.level <= 3) outline.push({ level: b.level, id: b.id, text: plain(b.c), line: b.line });
  };
  walk(blocks);
  return { meta, metaEnd: end, blocks, outline, lines: lines.length };
}

/**
 * The lines to mark for a target line: the whole section when the line is a heading, the item
 * when it is in a list, otherwise the block that holds it.
 */
export function hitRange(doc: Doc, line: number): [number, number] | null {
  if (line < 1) return null;
  const top = doc.blocks;
  const at = top.findIndex((b) => b.line <= line && line <= b.end);
  if (at < 0) return null;
  const block = top[at];
  if (block.t === 'heading') {
    const next = top.slice(at + 1).find((b) => b.t === 'heading' && b.level <= block.level);
    return [block.line, next ? next.line - 1 : doc.lines];
  }
  if (block.t === 'list') {
    const item = block.items.find((it) => it.line <= line && line <= it.end);
    if (item) return [item.line, item.end];
  }
  return [block.line, block.end];
}
