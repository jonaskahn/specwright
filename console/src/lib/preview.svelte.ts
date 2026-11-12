import { app } from './data/store.svelte';
import { docUrl } from './markdown/links';
import { decode, encode, forKey, type PreviewTarget } from './preview-target';

type Text = { ok: true; text: string } | { ok: false; reason: 'off' | 'missing' | 'failed' };

/**
 * The preview panel's state. The address is the source of truth, so the panel survives a reload
 * and the browser's Back button closes it. File contents come from the console's own server, and
 * only when it was started with `view.py serve`.
 */
class Preview {
  /** Whether the server answers for documents: unknown until the first probe. */
  docs = $state<'unknown' | 'on' | 'off'>('unknown');
  current = $derived(app.loaded.status === 'ready' ? decode(app.route.query, app.loaded) : null);
  private cache = new Map<string, Text>();

  open(target: PreviewTarget): void {
    app.setQuery(encode(target), true);
  }

  openKey(key: string): void {
    const target = forKey(app.loaded, key);
    if (target) this.open(target);
  }

  close(): void {
    app.setQuery(encode(null));
  }

  async probe(): Promise<void> {
    try {
      const res = await fetch('./doc/', { cache: 'no-store' });
      this.docs = res.ok ? 'on' : 'off';
    } catch {
      this.docs = 'off';
    }
  }

  forget(): void {
    this.cache.clear();
  }

  /** The text of a Markdown or plain-text document. */
  async text(scope: string, path: string): Promise<Text> {
    const key = `${scope}/${path}`;
    const known = this.cache.get(key);
    if (known) return known;
    if (this.docs === 'off') return { ok: false, reason: 'off' };
    let result: Text;
    try {
      const res = await fetch(docUrl(scope, path), { cache: 'no-store' });
      result = res.ok ? { ok: true, text: await res.text() } : { ok: false, reason: res.status === 404 ? 'missing' : 'failed' };
    } catch {
      result = { ok: false, reason: 'failed' };
    }
    if (result.ok) this.cache.set(key, result);
    return result;
  }
}

export const preview = new Preview();
