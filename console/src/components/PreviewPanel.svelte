<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { docUrl, isImage, previewable, suffixOf } from '../lib/markdown/links';
  import type { OutlineEntry } from '../lib/markdown/parse';
  import { clampWidth } from '../lib/prefs';
  import { preview } from '../lib/preview.svelte';
  import { href } from '../lib/router';
  import { wordLook } from '../lib/status';
  import { kindWords, stationWords } from '../lib/vocabulary';
  import Icon from './Icon.svelte';
  import Markdown from './Markdown.svelte';
  import NodeLinks from './NodeLinks.svelte';
  import Pill from './Pill.svelte';

  type Body = { kind: 'idle' } | { kind: 'loading' } | { kind: 'text'; text: string } | { kind: 'error'; reason: string };

  const t = $derived(preview.current);
  const node = $derived(t?.key ? app.graph.node(t.key) : undefined);
  const feature = $derived(t?.key ? app.features.find((f) => f.id === t.key) : undefined);
  /** The feature an item belongs to: itself, or the one that has it as a criterion or task. */
  const owner = $derived.by(() => {
    if (!t?.key) return null;
    if (feature) return feature.id;
    const parent = app.graph.neighbors(t.key, 'in', 'has_ac')[0] ?? app.graph.neighbors(t.key, 'in', 'has_task')[0];
    return parent?.other ?? null;
  });
  const suffix = $derived(t?.path ? suffixOf(t.path) : '');
  const readable = $derived(t?.scope && t.path && previewable(t.path) ? { scope: t.scope, path: t.path } : null);
  const raw = $derived(readable && preview.docs !== 'off' ? docUrl(readable.scope, readable.path) : null);

  let tab = $state<'content' | 'links' | 'details'>('content');
  let body = $state<Body>({ kind: 'idle' });
  let outline = $state<OutlineEntry[]>([]);
  let head = $state<HTMLElement | null>(null);
  let scroller = $state<HTMLElement | null>(null);
  let returnTo: HTMLElement | null = null;

  $effect(() => {
    void (t?.key ?? t?.path);
    tab = 'content';
    outline = [];
  });

  $effect(() => {
    const file = readable;
    if (!file || !['.md', '.txt', '.url'].includes(suffixOf(file.path))) {
      body = { kind: 'idle' };
      return;
    }
    let live = true;
    body = { kind: 'loading' };
    void preview.text(file.scope, file.path).then((r) => {
      if (live) body = r.ok ? { kind: 'text', text: r.text } : { kind: 'error', reason: r.reason };
    });
    return () => {
      live = false;
    };
  });

  $effect(() => {
    if (t) {
      if (!returnTo && document.activeElement instanceof HTMLElement) returnTo = document.activeElement;
      head?.focus({ preventScroll: true });
    } else if (returnTo) {
      returnTo.focus({ preventScroll: true });
      returnTo = null;
    }
  });

  function key(e: KeyboardEvent) {
    if (e.key === 'Escape' && t && !app.paletteOpen) preview.close();
  }

  function grip(e: PointerEvent) {
    const handle = e.currentTarget as HTMLElement;
    handle.setPointerCapture(e.pointerId);
    const move = (m: PointerEvent) => (app.prefs.previewWidth = clampWidth(innerWidth - m.clientX));
    const up = () => {
      handle.removeEventListener('pointermove', move);
      handle.removeEventListener('pointerup', up);
      app.setPref('previewWidth', app.prefs.previewWidth);
    };
    handle.addEventListener('pointermove', move);
    handle.addEventListener('pointerup', up);
  }

  function nudge(e: KeyboardEvent) {
    const step = e.key === 'ArrowLeft' ? 40 : e.key === 'ArrowRight' ? -40 : 0;
    if (!step) return;
    e.preventDefault();
    app.setPref('previewWidth', clampWidth((app.prefs.previewWidth || innerWidth / 2) + step));
  }

  const reasons: Record<string, string> = { missing: 'This file is not on disk any more.', failed: 'The file could not be read.', off: 'File contents need the console server.' };
  const quiet = (text: string) => text.replace(/-/g, ' ');
  function jump(entry: OutlineEntry) {
    scroller?.querySelector(`[id="md-${entry.id}"]`)?.scrollIntoView({ block: 'start' });
  }
</script>

<svelte:window onkeydown={key} />

{#if t}
  <aside class="preview" aria-label="Preview">
    <button class="preview-grip" type="button" aria-label="Resize the preview (arrow keys)" onpointerdown={grip} onkeydown={nudge}></button>
    <header class="preview-head">
      <div class="preview-title" bind:this={head} tabindex="-1">
        <p class="sub">
          {t.kind ? kindWords(t.kind) : 'File'}{#if t.key} · <span class="mono">{t.key}</span>{/if}
        </p>
        <h2>{t.title}</h2>
      </div>
      <div class="row-flex">
        <button class="btn icon-only ghost" type="button" aria-pressed={app.prefs.previewPinned} aria-label={app.prefs.previewPinned ? 'Float over the page' : 'Dock beside the page'} title={app.prefs.previewPinned ? 'Float over the page' : 'Dock beside the page'} onclick={() => app.setPref('previewPinned', !app.prefs.previewPinned)}><Icon name="fold" /></button>
        <button class="btn icon-only ghost" type="button" aria-label="Close preview" title="Close (Esc)" onclick={() => preview.close()}><Icon name="close" /></button>
      </div>
      <div class="preview-meta row-flex wrap">
        {#if node}<Pill look={wordLook(node.status)} />{/if}
        {#if t.scope && app.scopes.length > 1}<span class="chip">{t.scope}</span>{/if}
        {#if t.path}<span class="sub mono">{t.path}{t.line > 1 ? `:${t.line}` : ''}</span>{/if}
      </div>
      <div class="row-flex wrap">
        {#if owner}<a class="btn" href={href('features', owner)}>Open feature</a>{/if}
        {#if t.key}<a class="btn" href={href('graph', t.key)}>Show in graph</a>{/if}
        {#if raw}<a class="btn" href={raw} target="_blank" rel="noopener noreferrer">Open the file</a>{/if}
      </div>
      <div class="seg" role="group" aria-label="Preview sections">
        <button type="button" aria-pressed={tab === 'content'} onclick={() => (tab = 'content')}>Content</button>
        {#if t.key}<button type="button" aria-pressed={tab === 'links'} onclick={() => (tab = 'links')}>Connections</button>{/if}
        {#if node || feature}<button type="button" aria-pressed={tab === 'details'} onclick={() => (tab = 'details')}>Details</button>{/if}
      </div>
    </header>

    <div class="preview-body" bind:this={scroller}>
      {#if tab === 'content'}
        {#if !readable}
          <div class="empty"><h3>No file to show</h3><p class="muted">{t.path ? 'Only Markdown, PDF and images open here.' : 'This item is not stored in a file of its own.'}</p></div>
        {:else if preview.docs === 'off'}
          <div class="banner warn"><Icon name="warn" /><div><p><strong>{reasons.off}</strong></p><p>Start the console with <code>view.py serve</code> to read files here. The details and connections still work.</p></div></div>
        {:else if suffix === '.pdf'}
          <iframe class="preview-pdf" src={docUrl(readable.scope, readable.path)} title={t.title}></iframe>
        {:else if isImage(readable.path)}
          <img class="preview-img" src={docUrl(readable.scope, readable.path)} alt={t.title} />
        {:else if body.kind === 'loading'}
          <div class="stack-sm" aria-busy="true"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>
        {:else if body.kind === 'error'}
          <div class="empty"><h3>{reasons[body.reason] ?? reasons.failed}</h3></div>
        {:else if body.kind === 'text'}
          {#if outline.length > 2}
            <details class="preview-toc">
              <summary>On this page</summary>
              <ul>
                {#each outline as entry, n (n)}<li class={`l${entry.level}`}><button type="button" onclick={() => jump(entry)}>{entry.text}</button></li>{/each}
              </ul>
            </details>
          {/if}
          {#if suffix === '.md'}
            <Markdown text={body.text} scope={readable.scope} path={readable.path} line={t.line} bind:outline />
          {:else}
            <pre class="md-code">{body.text}</pre>
          {/if}
        {/if}
      {:else if tab === 'links' && t.key}
        {#if node}<NodeLinks nodeKey={t.key} onpick={(k) => preview.openKey(k)} />{:else}<p class="muted">This item has no links in the graph.</p>{/if}
      {:else}
        <dl class="preview-facts">
          {#if node}
            <dt>Kind</dt><dd>{kindWords(node.kind)}</dd>
            <dt>Status</dt><dd><Pill look={wordLook(node.status)} /></dd>
            {#if node.station}<dt>Station</dt><dd>{stationWords(node.station)}{node.condition ? ` · ${quiet(node.condition)}` : ''}</dd>{/if}
            {#if node.jira}<dt>Jira</dt><dd>{node.jira}</dd>{/if}
            {#if node.aliases.length}<dt>Aliases</dt><dd>{node.aliases.join(', ')}</dd>{/if}
          {/if}
          {#if feature}
            {#if feature.lint}<dt>Lint</dt><dd>{feature.lint}</dd>{/if}
            {#if feature.signoff}<dt>Sign-off</dt><dd>{feature.signoff}</dd>{/if}
            <dt>Criteria</dt><dd>{feature.acCount}</dd>
            <dt>Tasks</dt><dd>{feature.taskCount}</dd>
            {#if feature.next}<dt>Next</dt><dd>{feature.next}{feature.turn ? ` · ${feature.turn}'s turn` : ''}</dd>{/if}
            {#if feature.updated}<dt>Updated</dt><dd>{feature.updated}</dd>{/if}
            {#if feature.blockers.length}<dt>Blocked by</dt><dd>{feature.blockers.join('; ')}</dd>{/if}
            {#if feature.openQuestions.length}<dt>Open questions</dt><dd>{feature.openQuestions.join(', ')}</dd>{/if}
            {#if feature.openChanges.length}<dt>Open changes</dt><dd>{feature.openChanges.join(', ')}</dd>{/if}
          {/if}
        </dl>
      {/if}
    </div>
  </aside>
{/if}
