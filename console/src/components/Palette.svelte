<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { preview } from '../lib/preview.svelte';
  import { COMMANDS } from '../lib/query/parse';
  import { href } from '../lib/router';
  import Icon from './Icon.svelte';
  import { NAV } from './nav';

  interface Entry { label: string; sub: string; to: string; icon: string; key?: string }
  let dialog: HTMLDialogElement | undefined = $state();
  let input: HTMLInputElement | undefined = $state();
  let text = $state('');
  let at = $state(0);

  const entries = $derived.by<Entry[]>(() => {
    const needle = text.trim().toLowerCase();
    const out: Entry[] = [];
    const first = needle.split(/\s+/)[0];
    if (needle && (COMMANDS as readonly string[]).includes(first)) {
      out.push({ label: `Run: ${text.trim()}`, sub: 'query', to: href('query', null, { q: text.trim() }), icon: 'query' });
    }
    for (const n of NAV) if (!needle || n.label.toLowerCase().includes(needle)) out.push({ label: n.label, sub: n.group, to: href(n.route), icon: n.icon });
    if (needle.length >= 2) {
      for (const f of app.features) {
        if ((f.id + ' ' + f.title).toLowerCase().includes(needle)) out.push({ label: f.id, sub: f.title, to: href('features', f.id), icon: 'features', key: f.id });
      }
      let more = 0;
      for (const node of app.graph.nodes.values()) {
        if (more >= 12) break;
        if (node.kind !== 'feat' && (node.key + ' ' + node.title).toLowerCase().includes(needle)) {
          out.push({ label: node.key, sub: node.title, to: href('graph', node.key), icon: 'graph', key: node.key });
          more++;
        }
      }
      out.push({ label: `Search the graph for “${text.trim()}”`, sub: 'query', to: href('query', null, { q: `find ${text.trim()}` }), icon: 'query' });
    }
    return out.slice(0, 40);
  });

  $effect(() => {
    if (!dialog) return;
    if (app.paletteOpen && !dialog.open) {
      dialog.showModal();
      text = '';
      at = 0;
      queueMicrotask(() => input?.focus());
    } else if (!app.paletteOpen && dialog.open) dialog.close();
  });

  /** Enter opens the page; Shift+Enter reads the item in the preview, where the user already is. */
  function go(entry: Entry | undefined, read = false) {
    if (!entry) return;
    app.paletteOpen = false;
    if (read && entry.key) preview.openKey(entry.key);
    else location.hash = entry.to;
  }
  function key(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') { at = Math.min(at + 1, entries.length - 1); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { at = Math.max(at - 1, 0); e.preventDefault(); }
    else if (e.key === 'Enter') { go(entries[at], e.shiftKey); e.preventDefault(); }
  }
  function global(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { app.paletteOpen = !app.paletteOpen; e.preventDefault(); }
  }
</script>

<svelte:window onkeydown={global} />
<dialog class="palette-dialog" bind:this={dialog} aria-label="Command palette" onclose={() => (app.paletteOpen = false)} onclick={(e) => e.target === dialog && (app.paletteOpen = false)}>
  <div class="palette">
    <div class="q">
      <Icon name="query" />
      <input bind:this={input} bind:value={text} oninput={() => (at = 0)} onkeydown={key} aria-label="Search" placeholder="Jump to a screen or feature, or type a query" />
      <span class="kbd">Esc</span>
    </div>
    <div class="g" role="listbox">
      {#each entries as entry, i (entry.to + entry.label)}
        <div class="mi" role="option" tabindex="-1" aria-selected={i === at} onclick={() => go(entry)} onkeydown={(e) => e.key === 'Enter' && go(entry)} onmouseenter={() => (at = i)}>
          <Icon name={entry.icon} /><span>{entry.label}</span><span class="sub muted">{entry.sub}</span>
        </div>
      {:else}
        <p class="hint">No match. Try <code>find refund</code> or <code>path REF:FEAT-001 REF:FEAT-002</code>.</p>
      {/each}
    </div>
  </div>
</dialog>
