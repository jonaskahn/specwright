export interface NavItem {
  route: string;
  label: string;
  icon: string;
  group: string;
}

export const NAV: NavItem[] = [
  { route: 'overview', label: 'Overview', icon: 'overview', group: 'Workspace' },
  { route: 'projects', label: 'Projects', icon: 'projects', group: 'Workspace' },
  { route: 'metrics', label: 'Metrics', icon: 'metrics', group: 'Workspace' },
  { route: 'features', label: 'Features', icon: 'features', group: 'Specs' },
  { route: 'tasks', label: 'Tasks', icon: 'tasks', group: 'Specs' },
  { route: 'board', label: 'Board', icon: 'board', group: 'Specs' },
  { route: 'graph', label: 'Graph', icon: 'graph', group: 'Knowledge' },
  { route: 'query', label: 'Query', icon: 'query', group: 'Knowledge' },
  { route: 'records', label: 'Records', icon: 'records', group: 'Governance' },
  { route: 'sources', label: 'Sources', icon: 'sources', group: 'Governance' },
  { route: 'quality', label: 'Quality', icon: 'quality', group: 'Governance' },
  { route: 'registry', label: 'Registry', icon: 'registry', group: 'Governance' },
];

export const GROUPS = ['Workspace', 'Specs', 'Knowledge', 'Governance'];
