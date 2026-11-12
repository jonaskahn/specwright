// Every kind, relation and link detail the screens show, in plain words. The data and the query
// language keep their short tokens (feat, has_ac); nothing a person reads should.

interface Words {
  one: string;
  many: string;
}

const KINDS: Record<string, Words> = {
  program: { one: 'Program', many: 'Programs' },
  scope: { one: 'Project', many: 'Projects' },
  project: { one: 'Project', many: 'Projects' },
  epic: { one: 'Epic', many: 'Epics' },
  feat: { one: 'Feature', many: 'Features' },
  ac: { one: 'Acceptance criterion', many: 'Acceptance criteria' },
  task: { one: 'Task', many: 'Tasks' },
  idea: { one: 'Idea', many: 'Ideas' },
  bo: { one: 'Business objective', many: 'Business objectives' },
  stk: { one: 'Stakeholder', many: 'Stakeholders' },
  risk: { one: 'Risk', many: 'Risks' },
  br: { one: 'Business rule', many: 'Business rules' },
  nfr: { one: 'Non-functional requirement', many: 'Non-functional requirements' },
  fr: { one: 'Functional requirement', many: 'Functional requirements' },
  src: { one: 'Source', many: 'Sources' },
  snapshot: { one: 'Snapshot', many: 'Snapshots' },
  'snapshot-file': { one: 'Snapshot file', many: 'Snapshot files' },
  q: { one: 'Question', many: 'Questions' },
  dec: { one: 'Decision', many: 'Decisions' },
  cr: { one: 'Change request', many: 'Change requests' },
  amendment: { one: 'Amendment', many: 'Amendments' },
  cand: { one: 'Candidate', many: 'Candidates' },
  plan: { one: 'Plan', many: 'Plans' },
  'tasks-file': { one: 'Task file', many: 'Task files' },
  'feature-file': { one: 'Feature file', many: 'Feature files' },
  diagram: { one: 'Diagram', many: 'Diagrams' },
  asset: { one: 'Asset', many: 'Assets' },
  jira: { one: 'Jira issue', many: 'Jira issues' },
  code: { one: 'Code file', many: 'Code files' },
};

/** `ac` becomes "Acceptance criterion" (or "Acceptance criteria" with `many`). */
export function kindWords(kind: string, many = false): string {
  const found = KINDS[kind];
  if (found) return many ? found.many : found.one;
  const text = kind.replace(/[-_]/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1) + (many ? 's' : '');
}

export const knownKinds = (): string[] => Object.keys(KINDS);

/** [read from the source item, read from the target item] */
const RELATIONS: Record<string, [string, string]> = {
  member_of: ['belongs to epic', 'contains feature'],
  realizes: ['serves business objective', 'is served by'],
  governed_by: ['is governed by', 'governs'],
  sourced_from: ['is sourced from', 'is the source of'],
  shaped_from: ['was shaped from idea', 'was shaped into'],
  source_parent: ['is a page under', 'has page'],
  has_ac: ['has acceptance criterion', 'is an acceptance criterion of'],
  has_task: ['has task', 'is a task of'],
  implements: ['implements', 'is implemented by'],
  touches: ['changes code in', 'is changed by task'],
  affects: ['affects', 'is affected by'],
  supersedes: ['supersedes', 'is superseded by'],
  illustrates: ['illustrates', 'is illustrated by'],
  exercises: ['tests', 'is tested by'],
  derives_from: ['is derived from', 'is the basis of'],
  supports: ['supports', 'is supported by'],
  uses_asset: ['uses asset', 'is used by'],
  published_as: ['is published as Jira issue', 'is the published form of'],
  last_snapshot: ['was last captured in snapshot', 'is the latest snapshot of'],
  external_parent: ['sits under Jira issue', 'is the parent of'],
  mentions: ['mentions', 'is mentioned by'],
};

export const knownRelations = (): string[] => Object.keys(RELATIONS);

/** A relation as a sentence part. `side` is 'out' when the item is the source of the link. */
export function relationWords(rel: string, side: 'out' | 'in' = 'out'): string {
  const found = RELATIONS[rel];
  if (found) return found[side === 'out' ? 0 : 1];
  return rel.replace(/_/g, ' ');
}

const CLASSES: Record<string, string> = {
  declared: 'Written on purpose in a file',
  structural: 'Part of its parent file',
  registry: 'Listed in the identifier registry',
  mentioned: 'Only named in passing text',
};

export function classWords(cls: string): string {
  return CLASSES[cls] ?? cls.replace(/-/g, ' ');
}

const RESOLUTIONS: Record<string, string> = {
  resolved: 'Found',
  unresolved: 'Not defined anywhere',
  withdrawn: 'Withdrawn',
  'scope-not-loaded': 'Its project is not loaded',
  external: 'Outside the workspace',
  exists: 'File exists',
  missing: 'File is missing',
  'no-code-root': 'No code folder is set',
  'unsafe-path': 'Path was refused as unsafe',
};

export function resolutionWords(res: string | null): string {
  if (!res) return 'Not checked';
  return RESOLUTIONS[res] ?? res.replace(/-/g, ' ');
}

const STATIONS: Record<string, string> = {
  shape: 'Shape',
  spec: 'Specification',
  review: 'Review',
  plan: 'Plan',
  publish: 'Publish',
  dev: 'Development',
  inactive: 'Inactive',
};

export function stationWords(station: string | null): string {
  if (!station) return 'No station';
  return STATIONS[station] ?? station.charAt(0).toUpperCase() + station.slice(1).replace(/-/g, ' ');
}
