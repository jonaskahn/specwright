import { daysSince, percent } from '../format';
import { RUNGS } from '../status';
import type { Loaded } from './loader';
import { inScope, rows } from './selectors';

export interface Metrics {
  features: number;
  acs: number;
  tasks: number;
  byState: { state: string; count: number }[];
  byStation: { station: string; count: number }[];
  openQuestions: number;
  openChanges: number;
  idle: number;
  idleAfterDays: number;
  staleSnapshots: number;
  lintPass: number;
  lintFail: number;
  lintUnknown: number;
  findingsBySeverity: { severity: string; count: number }[];
  acsPerFeature: number;
  tasksPerFeature: number;
  noTasks: number;
  bo: { bo: string; features: number }[];
  ready: number;
  attention: { id: string; reason: string }[];
}

function tally<T>(items: T[], key: (item: T) => string | null): [string, number][] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const k = key(item);
    if (k) counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  return [...counts.entries()];
}

export function computeMetrics(d: Loaded, scope: string, today: Date = new Date()): Metrics {
  const feats = inScope(rows.features(d), scope);
  const idleAfter = d.index?.idleAfterDays ?? 14;
  const order = [...RUNGS, 'superseded', 'withdrawn'];
  const byState = tally(feats, (f) => f.state)
    .map(([state, count]) => ({ state, count }))
    .sort((a, b) => order.indexOf(a.state) - order.indexOf(b.state) || a.state.localeCompare(b.state));
  const stationOrder = ['shape', 'spec', 'review', 'plan', 'publish', 'dev'];
  const byStation = tally(feats, (f) => f.station)
    .map(([station, count]) => ({ station, count }))
    .sort((a, b) => stationOrder.indexOf(a.station) - stationOrder.indexOf(b.station));
  const idleOf = (f: (typeof feats)[number]) => daysSince(f.updated, today);
  const idleFeats = feats.filter((f) => (idleOf(f) ?? 0) >= idleAfter && !['superseded', 'withdrawn', 'ready-for-dev'].includes(f.state));
  const open = new Set(feats.flatMap((f) => f.openQuestions));
  const changes = new Set(feats.flatMap((f) => f.openChanges));
  const lint = feats.map((f) => f.lint);
  const findings = inScope(rows.findings(d), scope);
  const acs = feats.reduce((n, f) => n + f.acCount, 0);
  const tasks = feats.reduce((n, f) => n + f.taskCount, 0);
  const bo = new Map<string, number>();
  for (const f of feats) for (const b of f.bo) bo.set(b, (bo.get(b) ?? 0) + 1);
  const attention: { id: string; reason: string }[] = [];
  for (const f of feats) {
    if (f.condition === 'blocked') attention.push({ id: f.id, reason: 'blocked' });
    else if (/fail/i.test(f.lint ?? '')) attention.push({ id: f.id, reason: 'lint failing' });
    else if (f.openQuestions.length) attention.push({ id: f.id, reason: `${f.openQuestions.length} open question` + (f.openQuestions.length > 1 ? 's' : '') });
    else if (f.openChanges.length) attention.push({ id: f.id, reason: 'change request open' });
  }
  return {
    features: feats.length,
    acs,
    tasks,
    byState,
    byStation,
    openQuestions: open.size,
    openChanges: changes.size,
    idle: idleFeats.length,
    idleAfterDays: idleAfter,
    staleSnapshots: feats.filter((f) => (daysSince(f.snapshotDate, today) ?? 0) > 30).length,
    lintPass: lint.filter((l) => l && /pass/i.test(l)).length,
    lintFail: lint.filter((l) => l && /fail/i.test(l)).length,
    lintUnknown: lint.filter((l) => !l).length,
    findingsBySeverity: tally(findings, (f) => f.severity ?? 'unknown').map(([severity, count]) => ({ severity, count })),
    acsPerFeature: feats.length ? Math.round((acs / feats.length) * 10) / 10 : 0,
    tasksPerFeature: feats.length ? Math.round((tasks / feats.length) * 10) / 10 : 0,
    noTasks: feats.filter((f) => f.taskCount === 0 && !['superseded', 'withdrawn'].includes(f.state)).length,
    bo: [...bo.entries()].map(([b, features]) => ({ bo: b, features })).sort((a, b) => b.features - a.features || a.bo.localeCompare(b.bo)),
    ready: percent(feats.filter((f) => f.state === 'ready-for-dev').length, feats.length),
    attention,
  };
}
