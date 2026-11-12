<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';
  import logo from '../assets/logo.svg';
  import Icon from './Icon.svelte';
  import { GROUPS, NAV } from './nav';

  const counts: Record<string, number | undefined> = $derived({
    features: app.features.length,
    tasks: app.tasks.length,
    records: app.records.length,
    sources: app.sources.length,
  });
</script>

<aside class="sidebar" class:open={app.menuOpen} aria-label="Specwright">
  <a class="brand" href={href('overview')} aria-label="Specwright, overview">
    <img src={logo} alt="" />
    <span class="logotype">Specwright</span>
  </a>
  {#if app.scopes.length > 1}
    <div class="field scope-pick">
      <label class="sr-only" for="scope">Project</label>
      <select id="scope" class="select" value={app.scope} onchange={(e) => (app.scope = e.currentTarget.value)}>
        <option value="*">All projects</option>
        {#each app.scopes as s (s.scope)}<option value={s.scope}>{s.name}</option>{/each}
      </select>
    </div>
  {/if}
  <nav class="sidebar-nav">
    {#each GROUPS as group (group)}
      <div class="group-h">{group}</div>
      {#each NAV.filter((n) => n.group === group) as item (item.route)}
        <a class="navitem" href={href(item.route)} title={item.label} aria-current={app.route.name === item.route ? 'page' : undefined}>
          <Icon name={item.icon} /><span class="label">{item.label}</span>
          {#if counts[item.route] !== undefined}<span class="count">{counts[item.route]}</span>{/if}
        </a>
      {/each}
    {/each}
  </nav>
  <div class="sidebar-foot">
    <button class="navitem hide-sm" type="button" title="Collapse" onclick={() => app.setPref('folded', !app.prefs.folded)}>
      <Icon name="fold" /><span class="label">Collapse</span>
    </button>
  </div>
</aside>
<button class="scrim" class:open={app.menuOpen} type="button" aria-label="Close menu" onclick={() => (app.menuOpen = false)}></button>
