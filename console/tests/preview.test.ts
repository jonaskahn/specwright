import { describe, expect, it } from 'vitest';
import { loadAll } from '../src/lib/data/loader';
import { decode, encode, forFile, forKey } from '../src/lib/preview-target';
import { serve } from './golden';

describe('a program names files from the workspace root, the server from the project', async () => {
  const program = await loadAll('./data/', serve('program'));
  it('opens a project item at its path inside that project', () => {
    expect(forKey(program, 'ORD:AC-001-2')).toMatchObject({ scope: 'ORD', path: '02-drafts/FEAT-001.story.md' });
    expect(forKey(program, 'REF:EPIC-001')).toMatchObject({ scope: 'REF', path: '01-analysis/epics/EPIC-001.md' });
    expect(forKey(program, 'ORD:FEAT-001')?.path).toBe('02-drafts/FEAT-001.story.md');
  });
});

describe('what the preview opens for an item or a file', async () => {
  const trace = await loadAll('./data/', serve('trace'));

  it('opens a criterion at its line in the story', () => {
    expect(forKey(trace, 'REF:AC-001-2')).toMatchObject({ key: 'REF:AC-001-2', kind: 'ac', scope: 'REF', path: '02-drafts/FEAT-001.story.md', line: 26, title: 'Duplicate request' });
  });

  it('opens a task at its heading in the plan, and a feature at the top of its story', () => {
    expect(forKey(trace, 'REF:TASK-001-1')).toMatchObject({ path: '03-plan/FEAT-001.tasks.md', line: 8 });
    expect(forKey(trace, 'REF:FEAT-001')).toMatchObject({ path: '02-drafts/FEAT-001.story.md', line: 1 });
  });

  it('accepts an identifier written without its project when only one item matches', () => {
    expect(forKey(trace, 'AC-001-2')?.key).toBe('REF:AC-001-2');
    expect(forKey(trace, 'AC-999-9')).toBeNull();
  });

  it('keeps the choice in the address and reads it back', () => {
    const item = forKey(trace, 'REF:AC-001-2')!;
    expect(encode(item)).toEqual({ pk: 'REF:AC-001-2', p: null });
    expect(decode(new URLSearchParams(encode(item) as Record<string, string>), trace)).toEqual(item);
    const file = forFile('REF', 'records/CR-001.md', 12);
    expect(encode(file)).toEqual({ pk: null, p: 'REF/records/CR-001.md:12' });
    const query = new URLSearchParams({ p: 'REF/records/CR-001.md:12' });
    expect(decode(query, trace)).toMatchObject({ scope: 'REF', path: 'records/CR-001.md', line: 12, key: null });
    expect(encode(null)).toEqual({ pk: null, p: null });
  });

  it('refuses a file address that leaves the project or names an unreadable kind', () => {
    for (const p of ['REF/../x.md', 'REF/run.py', 'ref/a.md', 'REF/']) expect(decode(new URLSearchParams({ p }), trace), p).toBeNull();
    expect(decode(new URLSearchParams({ pk: 'REF:NOPE-001' }), trace)).toBeNull();
  });
});
