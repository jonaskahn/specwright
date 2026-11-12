import { describe, expect, it } from 'vitest';
import { imageUrl, resolveLink, resolvePath } from '../src/lib/markdown/links';
import { hitRange, parseInline, parseMarkdown, type Block } from '../src/lib/markdown/parse';

const STORY = `---
id: FEAT-001
title: Refund
bo: [BO-001]
aliases:
  - STORY-9
---
# Refund request

## Acceptance criteria

### AC-001-1
Given a paid order, When the buyer asks, Then one request is made.

### AC-001-2
Given a duplicate, When asked again, Then it is refused.

## Notes

- first point
- [x] done task
- [ ] open task
  - nested item

| Rule | Limit |
|:-----|------:|
| BR-001 | 14 \\| 30 days |

> quoted text

\`\`\`py
print("<b>no</b>")
\`\`\`

<script>alert(1)</script>
`;

const doc = parseMarkdown(STORY);
const kinds = (blocks: Block[]) => blocks.map((b) => b.t);

describe('the markdown reader', () => {
  it('reads front matter as pairs, joining list items', () => {
    expect(doc.meta).toEqual([
      ['id', 'FEAT-001'],
      ['title', 'Refund'],
      ['bo', 'BO-001'],
      ['aliases', 'STORY-9'],
    ]);
    expect(doc.metaEnd).toBe(7);
  });

  it('reads every block kind and keeps source line numbers, front matter included', () => {
    expect(kinds(doc.blocks)).toEqual(['heading', 'heading', 'heading', 'para', 'heading', 'para', 'heading', 'list', 'table', 'quote', 'code', 'raw']);
    const heading = doc.blocks.find((b) => b.t === 'heading' && b.c[0].t === 'ref')!;
    expect([heading.line, heading.end]).toEqual([12, 12]);
    expect(doc.blocks[0].line).toBe(8);
  });

  it('builds an outline of the first three heading levels with unique ids', () => {
    expect(doc.outline.map((o) => [o.level, o.text, o.id])).toEqual([
      [1, 'Refund request', 'refund-request'],
      [2, 'Acceptance criteria', 'acceptance-criteria'],
      [3, 'AC-001-1', 'ac-001-1'],
      [3, 'AC-001-2', 'ac-001-2'],
      [2, 'Notes', 'notes'],
    ]);
    const twice = parseMarkdown('# A\n\n# A\n');
    expect(twice.outline.map((o) => o.id)).toEqual(['a', 'a-1']);
  });

  it('reads lists with task items and nesting', () => {
    const list = doc.blocks.find((b) => b.t === 'list')!;
    if (list.t !== 'list') throw new Error('list');
    expect(list.items.map((i) => i.checked)).toEqual([null, true, false]);
    const nested = list.items[2].c.find((b) => b.t === 'list');
    expect(nested && nested.t === 'list' && nested.items).toHaveLength(1);
  });

  it('reads a table with alignment and escaped pipes', () => {
    const table = doc.blocks.find((b) => b.t === 'table')!;
    if (table.t !== 'table') throw new Error('table');
    expect(table.align).toEqual(['left', 'right']);
    expect(table.rows).toHaveLength(1);
    expect(table.rows[0][1]).toEqual([{ t: 'text', v: '14 | 30 days' }]);
    expect(table.rows[0][0]).toEqual([{ t: 'ref', id: 'BR-001' }]);
  });

  it('keeps raw html as text, never as markup', () => {
    const raw = doc.blocks[doc.blocks.length - 1];
    expect(raw).toMatchObject({ t: 'raw', v: '<script>alert(1)</script>' });
    const code = doc.blocks.find((b) => b.t === 'code')!;
    expect(code).toMatchObject({ lang: 'py', v: 'print("<b>no</b>")' });
    expect(parseInline('a <b>bold</b> b')).toEqual([{ t: 'text', v: 'a <b>bold</b> b' }]);
  });

  it('reads emphasis, code, links, images and identifiers inside text', () => {
    expect(parseInline('**strong** and *em* and `x*y` and snake_case_word')).toEqual([
      { t: 'strong', c: [{ t: 'text', v: 'strong' }] },
      { t: 'text', v: ' and ' },
      { t: 'em', c: [{ t: 'text', v: 'em' }] },
      { t: 'text', v: ' and ' },
      { t: 'code', v: 'x*y' },
      { t: 'text', v: ' and snake_case_word' },
    ]);
    expect(parseInline('[a (b)](docs/x.md) ![chart](assets/a.png)')).toEqual([
      { t: 'link', href: 'docs/x.md', c: [{ t: 'text', v: 'a (b)' }] },
      { t: 'text', v: ' ' },
      { t: 'image', alt: 'chart', src: 'assets/a.png' },
    ]);
    expect(parseInline('See REF:FEAT-001, AC-001-2 and TASK-001-1.').filter((i) => i.t === 'ref')).toEqual([
      { t: 'ref', id: 'REF:FEAT-001' },
      { t: 'ref', id: 'AC-001-2' },
      { t: 'ref', id: 'TASK-001-1' },
    ]);
    expect(parseInline('Q-1 and XFEAT-001')).toEqual([{ t: 'text', v: 'Q-1 and XFEAT-001' }]);
  });
});

describe('the lines marked for a target', () => {
  it('marks a whole section when the target is a heading', () => {
    expect(hitRange(doc, 12)).toEqual([12, 14]);
    expect(hitRange(doc, 8)).toEqual([8, doc.lines]);
  });

  it('marks one list item, or the block that holds the line', () => {
    const list = doc.blocks.find((b) => b.t === 'list')!;
    expect(hitRange(doc, list.line + 1)).toEqual([list.line + 1, list.line + 1]);
    expect(hitRange(doc, 13)).toEqual([13, 13]);
    expect(hitRange(doc, 0)).toBeNull();
    expect(hitRange(doc, 999)).toBeNull();
  });
});

describe('where a link may lead', () => {
  it('follows http, https and mail links, and nothing else with a scheme', () => {
    expect(resolveLink('https://example.test/a', '')).toEqual({ kind: 'external', href: 'https://example.test/a' });
    expect(resolveLink('mailto:a@b.test', '')).toMatchObject({ kind: 'external' });
    for (const bad of ['javascript:alert(1)', 'JavaScript:alert(1)', 'data:text/html,x', 'file:///etc/passwd', 'vbscript:x']) expect(resolveLink(bad, ''), bad).toEqual({ kind: 'none' });
  });

  it('draws a diagram embedded in a story and opens it as a file', () => {
    expect(imageUrl('REF', '02-drafts', '../diagrams/FEAT-001.flow.svg')).toBe('./doc/REF/diagrams/FEAT-001.flow.svg');
    expect(resolveLink('../diagrams/FEAT-001.flow.svg', '02-drafts')).toEqual({ kind: 'doc', path: 'diagrams/FEAT-001.flow.svg', fragment: '' });
    expect(imageUrl('REF', '02-drafts', '../../outside.svg')).toBeNull();
    expect(imageUrl('REF', '02-drafts', 'https://example.test/a.svg')).toBeNull();
  });

  it('resolves a relative document against the file, staying inside the project', () => {
    expect(resolveLink('../records/CR-001.md#why', '02-drafts')).toEqual({ kind: 'doc', path: 'records/CR-001.md', fragment: 'why' });
    expect(resolveLink('../../x.md', '02-drafts')).toEqual({ kind: 'none' });
    expect(resolveLink('/etc/passwd.md', '')).toEqual({ kind: 'none' });
    expect(resolveLink('..\\x.md', 'a')).toEqual({ kind: 'none' });
    expect(resolveLink('run.py', '')).toEqual({ kind: 'none' });
    expect(resolveLink('%zz.md', '')).toEqual({ kind: 'none' });
    expect(resolveLink('#notes', '')).toEqual({ kind: 'anchor', id: 'notes' });
    expect(resolvePath('a/b', '../c.md')).toBe('a/c.md');
  });

  it('loads only relative images of the project, from the document server', () => {
    expect(imageUrl('REF', '02-drafts', '../assets/ASSET 1.png')).toBe('./doc/REF/assets/ASSET%201.png');
    expect(imageUrl('REF', '', 'https://x.test/a.png')).toBeNull();
    expect(imageUrl('REF', '', '//x.test/a.png')).toBeNull();
    expect(imageUrl('REF', '', 'a.md')).toBeNull();
    expect(imageUrl('REF', 'a', '../../b.png')).toBeNull();
  });
});
