<script lang="ts">
  import { app } from '../lib/data/store.svelte';
  import { ACCENTS, DENSITIES, THEMES } from '../lib/prefs';
  import Icon from './Icon.svelte';
  let open = $state(false);
  const swatch = (name: string) => `var(--accent-${name})`;
</script>

<div class="pop-host">
  <button class="btn icon-only" type="button" aria-label="Appearance" title="Appearance" aria-expanded={open} onclick={() => (open = !open)}>
    <Icon name="appearance" />
  </button>
  {#if open}
    <div class="menu" role="dialog" aria-label="Appearance">
      <div class="field">
        <span class="label">Theme</span>
        <div class="seg" role="group" aria-label="Theme">
          {#each THEMES as t (t)}
            <button type="button" aria-pressed={app.prefs.theme === t} onclick={() => app.setPref('theme', t)}>{t[0].toUpperCase() + t.slice(1)}</button>
          {/each}
        </div>
      </div>
      <div class="field">
        <span class="label">Accent</span>
        <div class="row-flex wrap">
          {#each ACCENTS as a (a)}
            <button class="swatch" type="button" aria-label={a} aria-pressed={app.prefs.accent === a} style:--sw={swatch(a)} onclick={() => app.setPref('accent', a)}></button>
          {/each}
        </div>
      </div>
      <div class="field">
        <span class="label">Density</span>
        <div class="seg" role="group" aria-label="Density">
          {#each DENSITIES as d (d)}
            <button type="button" aria-pressed={app.prefs.density === d} onclick={() => app.setPref('density', d)}>{d[0].toUpperCase() + d.slice(1)}</button>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>
