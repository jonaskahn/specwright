import { FORMAT, FORMAT_VERSION, OWNERS, type DataIndex, type DataKinds, type KindName } from '../../../contract/types';

export type Status = 'loading' | 'ready' | 'nodata' | 'outofsync' | 'error';

export interface Loaded {
  status: Status;
  message: string;
  index: DataIndex | null;
  data: Partial<DataKinds>;
  /** Kinds with no file, and the skill that owns each. */
  missing: Record<string, string>;
  invalid: string[];
  /** Kinds built from older inputs than the rest. */
  stale: string[];
}

export function empty(status: Status, message = ''): Loaded {
  return { status, message, index: null, data: {}, missing: {}, invalid: [], stale: [] };
}

async function sha256(text: string): Promise<string | null> {
  if (!globalThis.crypto?.subtle) return null; // plain http on a non-local host
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return 'sha256:' + [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export type Fetcher = (url: string) => Promise<{ ok: boolean; status: number; text(): Promise<string> }>;

const defaultFetch: Fetcher = (url) => fetch(url, { cache: 'no-store' });

export async function loadAll(base = './data/', get: Fetcher = defaultFetch): Promise<Loaded> {
  let response;
  try {
    response = await get(`${base}index.json`);
  } catch (error) {
    return empty('error', `Could not reach the data: ${(error as Error).message}`);
  }
  if (!response.ok) {
    return empty(
      'nodata',
      response.status === 404
        ? 'No data files yet. Run a Specwright skill that exports data, then reload.'
        : `The data answered with status ${response.status}.`,
    );
  }
  let index: DataIndex;
  try {
    index = JSON.parse(await response.text()) as DataIndex;
  } catch {
    return empty('error', 'index.json is not valid JSON.');
  }
  if (index.format !== FORMAT || index.formatVersion !== FORMAT_VERSION) {
    return {
      ...empty('outofsync', `The data is format ${index.format} ${index.formatVersion}; this console reads ${FORMAT} ${FORMAT_VERSION}. Run sw-view prepare again.`),
      index,
    };
  }
  const out: Loaded = { ...empty('ready'), index };
  const digests: Record<string, string | null> = {};
  for (const kind of Object.keys(OWNERS) as KindName[]) {
    const entry = index.files[`${kind}.json`];
    if (!entry) {
      out.missing[kind] = OWNERS[kind];
      continue;
    }
    try {
      const res = await get(`${base}${kind}.json`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const text = await res.text();
      const actual = await sha256(text);
      if (actual !== null && actual !== entry.sha256) throw new Error('checksum differs from index.json');
      const doc = JSON.parse(text);
      if (doc.format !== FORMAT || doc.formatVersion !== FORMAT_VERSION || doc.kind !== kind) throw new Error('not this kind');
      (out.data as Record<string, unknown>)[kind] = doc;
      digests[kind] = doc.inputsDigest;
    } catch {
      out.invalid.push(kind);
    }
  }
  // The newest inputs win by majority; a file built from different inputs is stale.
  const counts = new Map<string, number>();
  for (const d of Object.values(digests)) if (d) counts.set(d, (counts.get(d) ?? 0) + 1);
  const common = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
  out.stale = Object.entries(digests)
    .filter(([, d]) => d && common && d !== common)
    .map(([kind]) => kind);
  if (Object.keys(out.data).length === 0) {
    return { ...out, status: 'nodata', message: 'The data folder is empty. Run the skills that own each file.' };
  }
  return out;
}
