// Where a link in a document may lead. Only a few schemes are followed, and a relative link must
// stay inside the project's own folder, so a document cannot point the console at anything else.

export const DOC_SUFFIXES = ['.md', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.txt', '.url'];
export const IMAGE_SUFFIXES = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'];
const FOLLOWED = new Set(['http', 'https', 'mailto']);

export type Target =
  | { kind: 'anchor'; id: string }
  | { kind: 'external'; href: string }
  | { kind: 'doc'; path: string; fragment: string }
  | { kind: 'none' };

export const suffixOf = (path: string): string => {
  const dot = path.lastIndexOf('.');
  return dot < 0 ? '' : path.slice(dot).toLowerCase();
};

export const previewable = (path: string | null | undefined): path is string => !!path && DOC_SUFFIXES.includes(suffixOf(path));
export const isImage = (path: string): boolean => IMAGE_SUFFIXES.includes(suffixOf(path));

/** Resolve a relative path against the folder of the file that holds it; null when it leaves the project. */
export function resolvePath(dir: string, relative: string): string | null {
  const out: string[] = dir ? dir.split('/').filter(Boolean) : [];
  for (const part of relative.split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..') {
      if (!out.length) return null;
      out.pop();
    } else out.push(part);
  }
  return out.length ? out.join('/') : null;
}

export const dirOf = (path: string): string => (path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '');

export function resolveLink(href: string, dir: string): Target {
  const value = href.trim();
  if (value.startsWith('#')) return value.length > 1 ? { kind: 'anchor', id: decodeURIComponent(value.slice(1)) } : { kind: 'none' };
  const scheme = /^([a-zA-Z][a-zA-Z0-9+.-]*):/.exec(value);
  if (scheme) return FOLLOWED.has(scheme[1].toLowerCase()) ? { kind: 'external', href: value } : { kind: 'none' };
  if (value.startsWith('//') || value.startsWith('/') || value.includes('\\')) return { kind: 'none' };
  const [pathAndQuery, fragment = ''] = value.split('#');
  let decoded: string;
  try {
    decoded = decodeURIComponent(pathAndQuery.split('?')[0]);
  } catch {
    return { kind: 'none' };
  }
  const path = resolvePath(dir, decoded);
  return path && previewable(path) ? { kind: 'doc', path, fragment } : { kind: 'none' };
}

/** The address the document server answers for one file of one project. */
export const docUrl = (scope: string, path: string): string => `./doc/${encodeURIComponent(scope)}/${path.split('/').map(encodeURIComponent).join('/')}`;

/** A relative image in a document, as an address the document server answers; null for anything else. */
export function imageUrl(scope: string, dir: string, src: string): string | null {
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:|^\/|\\/.test(src.trim())) return null;
  let decoded: string;
  try {
    decoded = decodeURIComponent(src.split('#')[0].split('?')[0]);
  } catch {
    return null;
  }
  const path = resolvePath(dir, decoded);
  return path && isImage(path) ? docUrl(scope, path) : null;
}
