# Bounded completion maintenance

`_shared/scripts/finish.py` runs these steps in order; read this file only to understand or
repair one of them.

Bounded means the steps below once per station, plus at most one repair pass (see Repair).
Maintenance itself never does the next station's work; the hand-off in step 9 does, by
`handoff.md`: under `flow: auto` the next skill starts at once with no question, under
`flow: guided` after one plain yes, under `flow: step` when the user names it. A blocker or a
human decision always stops the chain.

## Order

1. Finish the primary requested edits.
2. Resolve needed assets and illustrations; apply their links.
3. Recompute hashes; refresh derived cards.
4. Apply permitted trace updates.
5. Rebuild a stale graph from the final saved inputs.
6. Run `_shared/scripts/sw_lint.py --root <project> --gate <draft|review|publish>` for the gate that
   matches the station (exit 0 clean; 10, 20 or 30 means blocking findings) and, where shipped,
   `_shared/scripts/status.py`.
7. Refresh the data files you own (`data-format.md`), after the graph and lint.
8. Checkpoint: `checkpoint.py commit` once, after every write of the station (`checkpoint.md`):
   the project's spec files are committed and, when a remote is set up, pushed. Report its line
   with the results.
9. Hand off: `_shared/scripts/handoff.py next --cwd <project> --done <skill>` (`handoff.md`).
   Print its one-line `say`; on `continue` start the next skill now; on `stop` or `done`
   report the results gathered since the last stop and the human decision.

## Triggers

| Change | Follow-up |
| --- | --- |
| Requirements or body | Recompute hash; refresh the card. Never keep stale approval valid. |
| IDs or trace relations | Update allowed RTM fields through the trace implementation. Never infer links or break column ownership. |
| Assets supplied or referenced | Collect authorized assets; deduplicate; register provenance and associations. Missing assets stay explicit. Scan before shared persistence. |
| Plan saved or revised; other content changed; graph stale | Build or update the graph and query it after asset and visual work. Verify freshness on a no-op. |
| Spec, plan, source, record or registry content changed | Refresh only the data files your skill owns, with `data.py export <kind> --as <skill>`. Never write another skill's file. |
| Before any hand-off | Lint the applicable scope. Report a failure; never waive it silently. |
| Drawing requested, missing or stale | Ask sw-spec for its illustration_check script (`illustration_check.py FEAT-NNN`; only sw-spec ships it) and report the chip. Render only when the chip says a picture is needed. |
| Accepted draft ready for review | Prepare findings. Record approval only through sw-review: the owner's accept, or a verified sign-off under required. |
| Published requirement amendment | Validate the user-supplied current baseline and require a CR; if unverifiable, stop. No sync, guessed baseline, overwritten snapshot or Jira edit. |
| Review passes | The feature is accepted and eligible for plan, and for publication on request. A passing plan is Markdown delivery; publication stays a separate explicit decision. |
| Ingestion suggests changed logic | Save a quoted proposed impact. Back up the artifact only immediately before an accepted real edit; no revision increment before then. |
| Status-only rollback | Keep content hashes and historical sign-offs; invalidate active approval through the lifecycle decision. Do not call unchanged tasks content-stale. |
| Exact remote plan confirmed | Apply only through sw-publish. A changed plan, scope or hash needs new confirmation; a plain yes counts only for the exact dry-run just shown. |
| Command finished | One git checkpoint, last, by the lead only. Not a station change and not approval. Then the hand-off. |
| Nothing relevant changed | Skip maintenance and state why; the checkpoint reports `nothing`. |

## Repair

If fixes change inputs, rerun only the affected checks. Allow one bounded repair pass for
deterministic derived-output failures, then stop and explain what remains. Never rewrite
substantive requirements just to satisfy lint.

Without tool or connector access, return a clear blocked or partial result.
