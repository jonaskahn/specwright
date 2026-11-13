import { describe, expect, it } from 'vitest';
import { columns, findCriteria, hoist, plainOf, tagOf, valuesOf, type Criterion } from '../src/lib/markdown/criteria';
import { parseInline, parseMarkdown } from '../src/lib/markdown/parse';

const STORY = `---
id: FEAT-002
---
## Goal

As an invited person, I want an account.

## Acceptance criteria

### AC-002-1 — Activate with valid values

- **Given** the account "anna@example.com" is "Invited"
- **When** the invitee enters "Anna" and taps Save
- **Then** the profile holds "Anna"
- **And** the account is Active.

### AC-002-2 — Email is shown and cannot be edited

- **Given** the Activation popup is open for "anna@example.com"
- **When** the popup is displayed
- **Then** "anna@example.com" is shown as a label that cannot be edited.

### AC-002-3 — Blank first name is refused

- **Given** the Activation popup is open
- **When** the invitee leaves First Name blank and taps Save
- **Then** the inline error "Required" is shown and nothing is saved.

### AC-002-4 — Mismatched confirmation is refused

- **Given** the Activation popup is open
- **When** the invitee enters different passwords
- **Then** the inline error is shown.

### AC-002-5 — Short password is refused

- **Given** the Activation popup is open
- **When** the invitee enters "Ab1de"
- **Then** an inline error is shown.

## Business rules

- A rule.
`;

const section = () => findCriteria(parseMarkdown(STORY))!;

describe('criteria are read from the story', () => {
  it('finds the section, its criteria and the text around it', () => {
    const s = section();
    expect(s.items.map((c) => c.id)).toEqual(['AC-002-1', 'AC-002-2', 'AC-002-3', 'AC-002-4', 'AC-002-5']);
    expect(s.items[0].title).toBe('Activate with valid values');
    expect(s.before.some((b) => b.t === 'heading' && b.level === 2)).toBe(true);
    expect(s.after[0]).toMatchObject({ t: 'heading' });
  });

  it('reads bold bullets as steps and drops the closing full stop', () => {
    const [first] = section().items;
    expect(first.steps.map((s) => s.kw)).toEqual(['Given', 'When', 'Then', 'And']);
    expect(plainOf(first.steps[3].c)).toBe('the account is Active');
    expect(first.rest).toEqual([]);
  });

  it('reads plain lines that Markdown joined into one paragraph', () => {
    const doc = parseMarkdown('## Acceptance criteria\n\n### AC-001-1 — Return\nGiven a parcel\nWhen the buyer asks, Then a request is made.\n');
    const [c] = findCriteria(doc)!.items;
    expect(c.steps.map((s) => [s.kw, plainOf(s.c)])).toEqual([
      ['Given', 'a parcel'],
      ['When', 'the buyer asks'],
      ['Then', 'a request is made'],
    ]);
  });

  it('keeps a criterion that is not written in steps as it was', () => {
    const doc = parseMarkdown('## Acceptance criteria\n\n### AC-001-1 — Prose\nThe page loads fast.\n\n### AC-001-2 — Steps\n- **When** it runs\n- **Then** it ends\n');
    const items = findCriteria(doc)!.items;
    expect(items[0].steps).toEqual([]);
    expect(items[0].rest).toHaveLength(1);
    expect(items[0].tag).toBe('other');
    expect(items[1].steps).toHaveLength(2);
  });

  it('is null for a story with no criteria', () => {
    expect(findCriteria(parseMarkdown('## Goal\n\nText.\n'))).toBeNull();
    expect(findCriteria(parseMarkdown('## Acceptance criteria\n\nNone yet.\n'))).toBeNull();
  });
});

describe('the kind of a criterion', () => {
  it('reaches all four kinds', () => {
    const kinds = section().items.map((c) => c.tag);
    expect(kinds).toEqual(['happy', 'ui', 'validation', 'validation', 'validation']);
    expect(findCriteria(parseMarkdown('## Acceptance criteria\n\n### AC-001-1 — Prose\nNo steps.\n'))!.items[0].tag).toBe('other');
  });

  it('judges the title and the outcome, not the setup', () => {
    const then = (text: string) => [{ kw: 'Then' as const, c: parseInline(text) }];
    expect(tagOf('Reminder after 3 days', then('a reminder is sent'))).toBe('happy');
    expect(tagOf('Request the amount', then('nothing is saved'))).toBe('validation');
    expect(tagOf('Duplicate request')).toBe('validation');
    expect(tagOf('Valid input', [{ kw: 'When', c: parseInline('the popup is displayed') }])).toBe('ui');
    expect(tagOf('Closing the popup', then('the popup closes'))).toBe('happy');
  });
});

describe('a shared Given becomes the background', () => {
  it('shows it once and names the criteria it applies to', () => {
    const s = section();
    expect(s.background?.ids).toEqual(['AC-002-3', 'AC-002-4', 'AC-002-5']);
    expect(plainOf(s.background!.step.c)).toBe('the Activation popup is open');
    const [, , three] = s.items;
    expect(three.background).toBe(true);
    expect(three.steps.map((x) => x.kw)).toEqual(['When', 'Then']);
    expect(s.items[0].background).toBe(false);
    expect(s.items[0].steps[0].kw).toBe('Given');
  });

  it('needs three criteria and the same words', () => {
    const make = (given: string): Criterion => ({ id: given, title: '', line: 1, end: 1, steps: [{ kw: 'Given', c: parseInline(given) }], rest: [], tag: 'happy', background: false });
    expect(hoist([make('a'), make('a')]).background).toBeNull();
    expect(hoist([make('a'), make('a'), make('b')]).background).toBeNull();
    expect(hoist([make('A  b'), make('a b'), make('a b')]).background?.ids).toHaveLength(3);
  });
});

describe('values and columns', () => {
  it('picks out quoted values, straight or curly, and leaves a lone quote alone', () => {
    const pieces = valuesOf(parseInline('enters "Anna" and “Meyer” then 5" wide'));
    expect(pieces.filter((p) => p.t === 'value').map((p) => p.t === 'value' && p.v)).toEqual(['"Anna"', '“Meyer”']);
    expect(valuesOf(parseInline('say "unfinished'))).toEqual([{ t: 'inline', item: { t: 'text', v: 'say "unfinished' } }]);
  });

  it('keeps references and links as they are', () => {
    expect(valuesOf(parseInline('see SRC-0058 for "x"')).some((p) => p.t === 'inline' && p.item.t === 'ref')).toBe(true);
  });

  it('puts And and But lines in the column of the step before', () => {
    const [first] = section().items;
    const cols = columns(first.steps);
    expect([cols.given.length, cols.when.length, cols.then.length]).toEqual([1, 1, 2]);
  });
});
