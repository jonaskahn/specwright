<script lang="ts">
  import PageHead from '../components/PageHead.svelte';
  import OwnerEmpty from '../components/OwnerEmpty.svelte';
  import { app } from '../lib/data/store.svelte';
  import { href } from '../lib/router';

  function open(scope: string) {
    app.scope = scope;
    location.hash = href('features');
  }
</script>

<PageHead title="Projects" lede="One card per project, with what it holds and its lint gate." />
{#if app.scopes.length}
  <div class="cards">
    {#each app.scopes as s (s.scope)}
      <button class="card pad" type="button" onclick={() => open(s.scope)}>
        <div class="row-flex"><h3>{s.name}</h3><span class="spacer"></span><span class="chip">{s.scope}</span></div>
        <p class="sub">{s.jiraProjectKey ? `Jira ${s.jiraProjectKey}` : 'No Jira project'}{s.gate ? ` · gate ${s.gate}` : ''}</p>
        <dl class="facts">
          <div><dt>Features</dt><dd>{s.features}</dd></div>
          <div><dt>Criteria</dt><dd>{s.acs}</dd></div>
          <div><dt>Tasks</dt><dd>{s.tasks}</dd></div>
          <div><dt>Records</dt><dd>{s.records}</dd></div>
          <div><dt>Sources</dt><dd>{s.sources}</dd></div>
        </dl>
      </button>
    {/each}
  </div>
{:else}
  <OwnerEmpty kind="scopes" what="project" />
{/if}
