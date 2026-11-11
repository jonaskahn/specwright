# Bounded completion maintenance

Replace "finish, detect, ask before every next skill" with: finish the requested
action, run bounded required maintenance, then stop at the next human decision.

## Ordering

1. Finish primary requested edits.
2. Resolve necessary assets and illustrations and apply their links.
3. Recompute hashes and refresh derived cards.
4. Apply permitted trace updates.
5. Rebuild stale graph from final saved inputs.
6. Run relevant lint and status detection.
7. Return results and the next human decision; do not auto-advance stages.

## Automatic follow-up boundaries

- Requirements or body changed: recompute the content hash; refresh the compact card when applicable. Never preserve stale approval as valid.
- IDs or trace relationships changed: update allowed RTM fields through the existing trace implementation. Never infer links or violate column ownership.
- Ingestion or planning discussion supplies or references assets: collect authorized available assets, deduplicate, register provenance and item associations. Missing or inaccessible assets stay explicit; scan before shared persistence.
- Plan saved or revised, other relevant content changed, or graph stale: build or update the graph and query it after asset and visual completion. Verify freshness on a no-op.
- Before handoff: lint the applicable scope. Failure is reported, never silently waived.
- Drawing requested, missing where needed, or stale: evaluate illustration need; render only when justified. No automatic picture for every spec.
- Accepted draft ready for review: prepare review findings. Do not record approval or promote automatically.
- Published requirement amendment: validate the user-supplied current baseline and require a CR; stop if unavailable or unverifiable. No sync trigger, guessed baseline, overwritten snapshot or automatic Jira edit.
- Review passes: the named feature is eligible for plan on request, not publication. A passing plan is Markdown delivery; a publication request remains a separate explicit decision.
- Ingestion suggests changed logic: save a quoted proposed impact. Do not increment requirement revisions or back up unchanged prose; archive immediately before an accepted actual edit.
- Status-only rollback: preserve content hashes and historical signoffs, but invalidate active approval through the lifecycle decision. Do not falsely describe unchanged tasks as content-stale.
- Exact remote plan confirmed: apply only through Publish. Changed plan, scope or hash requires new confirmation.
- Nothing relevant changed: skip maintenance with reason. No recursive handoff.

## Repair

If fixes change inputs, rerun only affected checks. Permit one bounded repair pass for
deterministic derived-output failures, then stop and explain remaining issues. Do not
automatically rewrite substantive requirements merely to satisfy lint.

## Platform boundary

A ZIP does not install background event hooks. On web or Desktop the active skill
follows its completion procedure while the conversation is running. Missing tool
access or connector capability produces a clear blocked or partial result. This plan
does not add Claude Code hooks or a new agent orchestration framework.
