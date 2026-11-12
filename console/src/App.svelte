<script lang="ts">
  import Icon from './components/Icon.svelte';
  import Palette from './components/Palette.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import Topbar from './components/Topbar.svelte';
  import { app } from './lib/data/store.svelte';
  import { href } from './lib/router';
  import Board from './routes/Board.svelte';
  import FeatureDetail from './routes/FeatureDetail.svelte';
  import Features from './routes/Features.svelte';
  import Graph from './routes/Graph.svelte';
  import Metrics from './routes/Metrics.svelte';
  import Overview from './routes/Overview.svelte';
  import Projects from './routes/Projects.svelte';
  import Quality from './routes/Quality.svelte';
  import Query from './routes/Query.svelte';
  import Records from './routes/Records.svelte';
  import Registry from './routes/Registry.svelte';
  import Sources from './routes/Sources.svelte';
  import Tasks from './routes/Tasks.svelte';
  import Tree from './routes/Tree.svelte';

  const name = $derived(app.route.name);
  const phase = $derived(app.loaded.status);
  const fromDisk = location.protocol === 'file:';
</script>

<a class="skip" href="#main">Skip to content</a>
<div class="frame" class:folded={app.prefs.folded}>
  <Sidebar />
  <div class="stage">
    <Topbar />
    <main class="page" id="main">
      {#if fromDisk}
        <div class="banner danger"><Icon name="warn" /><div><p><strong>This page was opened from disk.</strong> Browsers block its scripts there.</p><p>Run <code>view.py serve</code> (sw-view prints the command) and open the address it shows.</p></div></div>
      {:else if phase === 'loading'}
        <div class="stack-sm" aria-busy="true" aria-label="Loading"><div class="skeleton" style:inline-size="30%" style:block-size="2rem"></div><div class="skeleton" style:block-size="6rem"></div><div class="skeleton" style:block-size="14rem"></div></div>
      {:else if phase !== 'ready'}
        <div class="empty" role="alert">
          <h3>{phase === 'outofsync' ? 'The console and the data are out of sync' : phase === 'nodata' ? 'No data yet' : 'Something went wrong'}</h3>
          <p class="muted">{app.loaded.message}</p>
          <button class="btn primary" type="button" onclick={() => app.reload()}>Reload</button>
        </div>
      {:else if name === 'overview'}<Overview />
      {:else if name === 'projects'}<Projects />
      {:else if name === 'metrics'}<Metrics />
      {:else if name === 'features'}{#if app.route.param}<FeatureDetail id={app.route.param} />{:else}<Features />{/if}
      {:else if name === 'tasks'}<Tasks />
      {:else if name === 'board'}<Board />
      {:else if name === 'tree'}<Tree />
      {:else if name === 'graph'}<Graph />
      {:else if name === 'query'}<Query />
      {:else if name === 'records'}<Records />
      {:else if name === 'sources'}<Sources />
      {:else if name === 'quality'}<Quality />
      {:else if name === 'registry'}<Registry />
      {:else}
        <div class="empty"><h3>Nothing here</h3><a class="btn" href={href('overview')}>Back to the overview</a></div>
      {/if}
    </main>
  </div>
</div>
<nav class="dock" aria-label="Primary">
  <a href={href('overview')} aria-current={name === 'overview' ? 'page' : undefined}><Icon name="overview" />Overview</a>
  <a href={href('features')} aria-current={name === 'features' ? 'page' : undefined}><Icon name="features" />Features</a>
  <a href={href('graph')} aria-current={name === 'graph' ? 'page' : undefined}><Icon name="graph" />Graph</a>
  <button type="button" onclick={() => (app.menuOpen = true)}><Icon name="menu" />Menu</button>
</nav>
<Palette />
