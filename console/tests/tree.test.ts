import { describe, expect, it } from 'vitest';
import { loadAll } from '../src/lib/data/loader';
import { buildTree, type TreeNode } from '../src/lib/data/selectors';
import { serve } from './golden';

const walk = (node: TreeNode): string[] => [node.key, ...node.children.flatMap(walk)];
const find = (node: TreeNode, key: string): TreeNode | undefined => (node.key === key ? node : node.children.map((c) => find(c, key)).find(Boolean));

describe('the tree follows the chain', async () => {
  const trace = await loadAll('./data/', serve('trace'));
  const [project] = buildTree(trace, '*');

  it('nests a task under the criterion it implements', () => {
    const criterion = find(project, 'REF:AC-001-1');
    expect(criterion?.children.map((c) => c.key)).toEqual(['REF:TASK-001-1', 'REF:TASK-001-2']);
    expect(find(project, 'REF:AC-001-2')?.children.map((c) => c.key)).toEqual(['REF:TASK-001-2']);
  });

  it('puts a task that implements no criterion in a group that says so', () => {
    const group = find(project, 'gap:task:REF:FEAT-001');
    expect(group?.kind).toBe('gap');
    expect(group?.title).toBe('Tasks not tied to an acceptance criterion');
    expect(group?.children.map((c) => c.key)).toEqual(['REF:TASK-001-3']);
  });

  it('puts a feature that is in no epic in a group that says so, since epics exist', () => {
    expect(find(project, 'REF:EPIC-001')?.children.map((c) => c.key)).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
    const group = find(project, 'gap:epic:REF');
    expect(group?.title).toBe('Features in no epic yet');
    expect(group?.children.map((c) => c.key)).toEqual(['REF:FEAT-003']);
  });

  it('shows every feature, criterion and task once under its place', () => {
    const keys = walk(project);
    for (const key of ['REF:FEAT-001', 'REF:FEAT-002', 'REF:FEAT-003', 'REF:AC-003-2', 'REF:TASK-003-1']) expect(keys, key).toContain(key);
  });

  it('lists features directly when the project has no epic', async () => {
    const flat = await loadAll('./data/', serve('flat'));
    const [root] = buildTree(flat, '*');
    expect(root.children.map((c) => c.key)).toEqual(['REF:FEAT-001', 'REF:FEAT-002']);
  });
});
