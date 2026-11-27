export interface NavItem {
  route: string;
  label: string;
  icon: string;
  group: string;
}

export const NAV: NavItem[] = [
  { route: 'overview', label: 'Overview', icon: 'overview', group: 'Workspace' },
  { route: 'features', label: 'Features', icon: 'features', group: 'Workspace' },
  { route: 'board', label: 'Board', icon: 'board', group: 'Plan' },
  { route: 'tasks', label: 'Tasks', icon: 'tasks', group: 'Plan' },
  { route: 'graph', label: 'Graph', icon: 'graph', group: 'Knowledge' },
  { route: 'records', label: 'Records', icon: 'records', group: 'Governance' },
  { route: 'quality', label: 'Quality', icon: 'quality', group: 'Governance' },
];

export const GROUPS = ['Workspace', 'Plan', 'Knowledge', 'Governance'];
