# Graph model

## Nodes

Hierarchy: program, scope, epic, feat, ac, task. Analysis: idea, bo, stk, risk, br, nfr, fr. Evidence: src, snapshot, q,
dec, cr. Artifacts: plan, tasks-file, feature-file, diagram, asset. External: jira:KEY. Code: code paths named by
Touches.

STORY is the BA/PO word for FEAT; there is no STORY node.

Feature shards carry a lifecycle projection: station, condition, available actions,
blockers, planning and publication summaries. Registry-reserved features are nodes
before story creation. Accepted-split DEC records declare their epic membership.
Lifecycle DEC predecessor chains survive cache rebuilds; no station field is edited.
Schema version 2 verifies both input inventory and content digest, including same-size
changes. Missing/incompatible/stale boards cannot be used for automatic routing.
Use the board query for structured per-feature output.

## Relations

member_of (feat to epic), realizes (to bo), governed_by (to br, nfr, fr), sourced_from, shaped_from, has_ac, has_task,
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

_meta/graph/ holds manifest.json, KNOWLEDGE-MAP.md, maps/, index.tsv, edges-out.tsv, edges-in.tsv and shards/. A program
root has a merged copy. Everything is generated and committed. After a merge conflict in these files, run build.
