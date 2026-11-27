# Graph model

## Nodes

Hierarchy: program, scope, epic, feat, ac, task. Analysis: idea, bo, stk, risk, br, nfr, fr. Evidence: src, snapshot, q,
dec, cr, amendment (AMD), candidates (CAND). Artifacts: plan, tasks-file, feature-file, diagram, asset. External: jira:KEY. Code: code paths named by
Touches.

STORY is the BA/PO word for FEAT; there is no STORY node.

Feature shards carry a lifecycle projection: station, condition, available actions,
blockers, planning and publication summaries. Registry-reserved features are nodes
before story creation. Accepted-split DEC records declare their epic membership.
Lifecycle DEC predecessor chains survive cache rebuilds; no station field is edited.
The graph verifies input inventory and content digest (schema version 3), including
same-size changes. A missing, incompatible or stale board cannot drive routing. Use the
board query for structured per-feature output.

## Relations

member_of (feat to epic), realizes (feat or epic to bo, many to many), governed_by (to br, nfr, fr), sourced_from, shaped_from, source_parent (snapshot to its parent page), has_ac, has_task,
implements (task to ac, br, nfr), touches (task to code), affects (cr or dec), supersedes, illustrates (diagram),
exercises (.feature tag), derives_from (artifact to feat), supports (asset to spec item), uses_asset (spec item to
asset), published_as (feat to Jira key), last_snapshot, external_parent (jira_parent), mentions.

## Provenance classes

- declared: a front matter field, task field, diagram spec_ids or feature tag.
- structural: an AC or task block inside its parent file.
- registry: a mapping in the ID registry.
- mentioned: an ID found in body text. Weak; never use it alone for a decision.

## Resolutions

resolved, unresolved (no definition), withdrawn (tombstone), scope-not-loaded (project not built), external (Jira or
snapshot), exists or missing (code path), no-code-root, unsafe-path.

## Files

_meta/graph/ holds manifest.json, KNOWLEDGE-MAP.md, maps/, index.tsv (key, kind, status, title, shard, path:line,
aliases), edges-out.tsv, edges-in.tsv and shards/. A program root has a merged copy. Everything is generated and
committed. After a merge conflict in these files, run build.

## Master index

The same build writes four files next to the graph in _meta/, never edited by hand (check reports an edited copy):

- INDEX.md and index.tsv: one row per artifact (key, kind, name, aliases, origin, path, status with flags, hash,
  parent, links). Flags are blocked, stale, withdrawn, superseded, index-only and untitled. Links are `rel:KEY`, and
  `~rel:KEY` for an incoming link.
- CROSSWALK.tsv: one row per legacy or external item mapping every name it has to its internal key, with
  match = matched, no-feature, no-source, ambiguous or no-register. The legacy register is
  01-analysis/baseline/register.tsv (legacy_id, title, group, source_ref); without one, features that have aliases
  are listed.
- READ-FIRST.md: the fixed reading order for a new session.

Names come from front matter (`title`, `aliases`); a reserved feature takes them from the registry Title and
Aliases columns. An empty title is flagged `untitled`, never replaced by a placeholder.
