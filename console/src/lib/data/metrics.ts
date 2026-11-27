import { plural } from '../format';
import type { Loaded } from './loader';
import { inScope, rows } from './selectors';

/** The recorded task progress words, in the order a pipeline reads. */
export const PROGRESS_ORDER = ['done', 'in-progress', 'blocked', 'planned', 'not-started'] as const;

export interface Attention {
  /** The story's identifier, or the task's for a blocked task. */
  id: string;
  kind: 'feature' | 'task';
  /** Words, already pluralised: "blocked", "lint failing", "2 open questions". */
  reason: string;
}

export interface Metrics {
  features: number;
  acs: number;
  tasks: number;
  epics: number;
  records: number;
  openQuestions: number;
  openChanges: number;
  lintPass: number;
  lintFail: number;
  /** One list of what needs a person: stories first, then blocked tasks. */
  attention: Attention[];
  /** Active tasks by recorded progress, in pipeline order. */
  progress: { progress: (typeof PROGRESS_ORDER)[number]; count: number }[];
  blockedTasks: number;
}

const RETIRED = ['superseded', 'withdrawn'];

export function computeMetrics(d: Loaded, scope: string): Metrics {
  const feats = inScope(rows.features(d), scope).filter((f) => !RETIRED.includes(f.state));
  const tasks = inScope(rows.tasks(d), scope).filter((t) => t.status === 'active');
  const open = new Set(feats.flatMap((f) => f.openQuestions));
  const changes = new Set(feats.flatMap((f) => f.openChanges));
  const lint = feats.map((f) => f.lint);
  const blockedTasks = tasks.filter((t) => t.progress === 'blocked');

  const attention: Attention[] = [];
  for (const f of feats) {
    if (f.condition === 'blocked') attention.push({ id: f.id, kind: 'feature', reason: 'blocked' });
    else if (/fail/i.test(f.lint ?? '')) attention.push({ id: f.id, kind: 'feature', reason: 'lint failing' });
    else if (f.openQuestions.length) attention.push({ id: f.id, kind: 'feature', reason: plural(f.openQuestions.length, 'open question') });
    else if (f.openChanges.length) attention.push({ id: f.id, kind: 'feature', reason: plural(f.openChanges.length, 'open change request') });
  }
  for (const t of blockedTasks) attention.push({ id: t.id, kind: 'task', reason: 'task blocked' });

  const epics = (d.data.graph?.nodes ?? []).filter((n) => n.kind === 'epic' && (scope === '*' || n.scope === scope) && !RETIRED.includes(n.status ?? '')).length;

  return {
    features: feats.length,
    acs: feats.reduce((n, f) => n + f.acCount, 0),
    tasks: tasks.length,
    epics,
    records: inScope(rows.records(d), scope).length,
    openQuestions: open.size,
    openChanges: changes.size,
    lintPass: lint.filter((l) => l && /pass/i.test(l)).length,
    lintFail: lint.filter((l) => l && /fail/i.test(l)).length,
    attention,
    progress: PROGRESS_ORDER.map((progress) => ({ progress, count: tasks.filter((t) => t.progress === progress).length })),
    blockedTasks: blockedTasks.length,
  };
}
