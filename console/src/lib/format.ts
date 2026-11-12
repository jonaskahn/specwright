// Small display helpers. Dates in the data are absolute (YYYY-MM-DD); ages are derived here.

const DAY = 86_400_000;

export function daysSince(date: string | null, today: Date = new Date()): number | null {
  if (!date) return null;
  const then = Date.parse(date.slice(0, 10) + 'T00:00:00Z');
  if (Number.isNaN(then)) return null;
  const now = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Math.max(0, Math.round((now - then) / DAY));
}

export function ago(days: number | null): string {
  if (days === null) return 'not set';
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 14) return `${days} days ago`;
  if (days < 70) return `${Math.round(days / 7)} weeks ago`;
  return `${Math.round(days / 30)} months ago`;
}

export function plural(count: number, one: string, many = one + 's'): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function shortKey(key: string): string {
  const at = key.indexOf(':');
  return at > 0 && /^[A-Z][A-Z0-9]*$/.test(key.slice(0, at)) ? key.slice(at + 1) : key;
}

export function percent(part: number, whole: number): number {
  return whole === 0 ? 0 : Math.round((part / whole) * 100);
}
