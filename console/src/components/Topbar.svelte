<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import logo from '../assets/logo.svg';
  import Appearance from './Appearance.svelte';
  import Icon from './Icon.svelte';
  import { NAV } from './nav';
  const here = $derived(NAV.find((n) => n.route === app.route.name));
</script>

<header class="topbar">
  <button class="btn icon-only ghost menu-btn" type="button" aria-label="Menu" onclick={() => (app.menuOpen = !app.menuOpen)}><Icon name="menu" /></button>
  <a class="brand" href={href('overview')} aria-label="Specwright"><img src={logo} alt="" width="28" height="28" /></a>
  <nav class="crumbs" aria-label="Breadcrumb">
    <ol>
      <li><a href={href('overview')}>Specwright</a></li>
      {#if here}<li>{here.group}</li>{/if}
      <li aria-current="page">{here?.label ?? 'Not found'}{app.route.param ? ` · ${app.route.param}` : ''}</li>
    </ol>
  </nav>
  <div class="topright">
    <button class="btn" type="button" aria-label="Open command palette" onclick={() => (app.paletteOpen = true)}>
      <Icon name="query" /><span class="hide-sm">Search</span><span class="kbd hide-sm">⌘K</span>
    </button>
    <button class="btn icon-only" type="button" aria-label="Reload data" title="Reload data" onclick={() => app.reload()}><Icon name="refresh" /></button>
    <Appearance />
  </div>
</header>
