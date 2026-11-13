import { describe, expect, it } from 'vitest';
import { plainOf } from '../src/lib/markdown/criteria';
import { parseMarkdown } from '../src/lib/markdown/parse';
import { findTasks } from '../src/lib/markdown/tasks';

const TASKS = `---
feat: FEAT-002
status: ready
---

## Tasks

### TASK-002-1 — [backend] Validate the activation link

Traces to: AC-002-1, AC-002-7
Visuals: diagrams/invite-flow.svg
Depends on: None
Done when: Opening a valid link for "anna@example.com" returns the address.
Stop and ask if: the validity period is needed.

### TASK-002-3 — [backend] Keep the account Invited [P]

Traces to: AC-002-6
Depends on: TASK-002-1
Done when: Closing the popup saves nothing.

### TASK-002-4 — [mobile] Build the popup

- Traces to: AC-002-1
- Done when: the popup shows the label.

### TASK-002-9 — Unlabelled work

Just some words, no labels.

## Notes

Later text.
`;

const find = () => findTasks(parseMarkdown(TASKS))!;
const text = (t: ReturnType<typeof find>['items'][number], k: keyof typeof t.fields) => plainOf(t.fields[k] ?? []);

describe('tasks are read from a plan', () => {
  it('lists each task heading with its layer, title and parallel mark', () => {
    const s = find();
    expect(s.items.map((t) => [t.id, t.layer, t.title, t.parallel])).toEqual([
      ['TASK-002-1', 'backend', 'Validate the activation link', false],
      ['TASK-002-3', 'backend', 'Keep the account Invited', true],
      ['TASK-002-4', 'mobile', 'Build the popup', false],
      ['TASK-002-9', null, 'Unlabelled work', false],
    ]);
    expect(s.after[0]).toMatchObject({ t: 'heading' });
  });

  it('splits the labelled lines Markdown joined into one paragraph', () => {
    const [first] = find().items;
    expect(text(first, 'traces')).toBe('AC-002-1, AC-002-7');
    expect(text(first, 'visuals')).toBe('diagrams/invite-flow.svg');
    expect(text(first, 'depends')).toBe('None');
    expect(text(first, 'done')).toBe('Opening a valid link for "anna@example.com" returns the address.');
    expect(text(first, 'stop')).toBe('the validity period is needed.');
    expect(first.rest).toEqual([]);
  });

  it('reads labels written as list items', () => {
    const third = find().items[2];
    expect(text(third, 'traces')).toBe('AC-002-1');
    expect(text(third, 'done')).toBe('the popup shows the label.');
  });

  it('keeps a task without labels as it was written', () => {
    const last = find().items[3];
    expect(last.fields).toEqual({});
    expect(last.rest).toHaveLength(1);
  });

  it('is null for a file with no task headings', () => {
    expect(findTasks(parseMarkdown('## Tasks\n\nNothing yet.\n'))).toBeNull();
    expect(findTasks(parseMarkdown('## Approach\n\nText.\n'))).toBeNull();
  });
});
