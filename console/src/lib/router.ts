// Hash routes: #/features/REF:FEAT-001?scope=REF. The query bar's text lives in the hash too.

export interface Route {
  name: string;
  param: string | null;
  query: URLSearchParams;
}

export function parseHash(hash: string): Route {
  const [path, search = ''] = hash.replace(/^#\/?/, '').split('?');
  const [name, ...rest] = path.split('/');
  return {
    name: name || 'overview',
    param: rest.length ? decodeURIComponent(rest.join('/')) : null,
    query: new URLSearchParams(search),
  };
}

export function href(name: string, param?: string | null, query?: Record<string, string>): string {
  const q = query && Object.keys(query).length ? '?' + new URLSearchParams(query).toString() : '';
  return `#/${name}${param ? '/' + encodeURIComponent(param) : ''}${q}`;
}
