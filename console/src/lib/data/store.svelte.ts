import { empty, loadAll, type Loaded } from './loader';
import { computeMetrics } from './metrics';
import { graphIndex, inScope, rows } from './selectors';
import { applyPrefs, loadPrefs, savePref, type Prefs } from '../prefs';
import { parseHash, type Route } from '../router';

class App {
  loaded = $state<Loaded>(empty('loading'));
  scope = $state('*');
  route = $state<Route>(parseHash(location.hash));
  prefs = $state<Prefs>(loadPrefs());
  menuOpen = $state(false);
  paletteOpen = $state(false);
  today = new Date();

  scopes = $derived(rows.scopes(this.loaded));
  features = $derived(inScope(rows.features(this.loaded), this.scope));
  tasks = $derived(inScope(rows.tasks(this.loaded), this.scope));
  records = $derived(inScope(rows.records(this.loaded), this.scope));
  sources = $derived(inScope(rows.sources(this.loaded), this.scope));
  registry = $derived(inScope(rows.registry(this.loaded), this.scope));
  results = $derived(inScope(rows.results(this.loaded), this.scope));
  findings = $derived(inScope(rows.findings(this.loaded), this.scope));
  graph = $derived(graphIndex(this.loaded));
  metrics = $derived(computeMetrics(this.loaded, this.scope, this.today));

  async reload(): Promise<void> {
    this.loaded = empty('loading');
    this.loaded = await loadAll();
    const scopes = rows.scopes(this.loaded);
    if (this.scope !== '*' && !scopes.some((s) => s.scope === this.scope)) this.scope = '*';
  }

  /** Change the query part of the address (table filters, the preview) without leaving the page. */
  setQuery(changes: Record<string, string | null>, push = false): void {
    const [path, search = ''] = location.hash.replace(/^#/, '').split('?');
    const query = new URLSearchParams(search);
    for (const [name, value] of Object.entries(changes)) {
      if (value === null || value === '') query.delete(name);
      else query.set(name, value);
    }
    const text = query.toString();
    const next = `#${path || '/overview'}${text ? `?${text}` : ''}`;
    if (next === location.hash) return;
    const url = location.pathname + location.search + next;
    if (push) history.pushState(null, '', url);
    else history.replaceState(null, '', url);
    this.route = parseHash(location.hash);
  }

  setPref<K extends keyof Prefs>(name: K, value: Prefs[K]): void {
    this.prefs[name] = value;
    savePref(name, value as string | boolean | number);
    applyPrefs(this.prefs);
  }
}

export const app = new App();

export function startApp(): void {
  applyPrefs(app.prefs);
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => applyPrefs(app.prefs));
  addEventListener('hashchange', () => {
    app.route = parseHash(location.hash);
    app.menuOpen = false;
  });
  void app.reload();
}
