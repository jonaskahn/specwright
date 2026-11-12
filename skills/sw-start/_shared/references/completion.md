# Bounded completion maintenance

Finish the requested action, run the maintenance below, then report. Never advance a
stage without the user's confirmation: under `flow: guided` one plain yes to "Continue to
<next station>?" is that confirmation for a local station (`governance.md`); under
`flow: step` stop at the next human decision. Never recurse into a handoff unasked.

## Order

1. Finish the primary requested edits.
2. Resolve needed assets and illustrations; apply their links.
3. Recompute hashes; refresh derived cards.
4. Apply permitted trace updates.
5. Rebuild a stale graph from the final saved inputs.
6. Run the relevant lint and status detection.
7. Refresh the data files you own (`data-format.md`), after the graph and lint.
8. Report results and the next human decision.

## Triggers

| Change | Follow-up |
| --- | --- |
| Requirements or body | Recompute hash; refresh the card. Never keep stale approval valid. |
| IDs or trace relations | Update allowed RTM fields through the trace implementation. Never infer links or break column ownership. |
| Assets supplied or referenced | Collect authorized assets; deduplicate; register provenance and associations. Missing assets stay explicit. Scan before shared persistence. |
| Plan saved or revised; other content changed; graph stale | Build or update the graph and query it after asset and visual work. Verify freshness on a no-op. |
| Spec, plan, source, record or registry content changed | Refresh only the data files your skill owns, with `data.py export <kind> --as <skill>`. Never write another skill's file. |
| Before any hand-off | Lint the applicable scope. Report a failure; never waive it silently. |
| Drawing requested, missing or stale | Run illustration_check.py and report the chip. Render only when the chip says a picture is needed. |
| Accepted draft ready for review | Prepare findings. Record approval only through sw-review: the owner's accept, or a verified sign-off under required. |
| Published requirement amendment | Validate the user-supplied current baseline and require a CR; if unverifiable, stop. No sync, guessed baseline, overwritten snapshot or Jira edit. |
| Review passes | The feature is accepted and eligible for plan, and for publication on request. A passing plan is Markdown delivery; publication stays a separate explicit decision. |
| Ingestion suggests changed logic | Save a quoted proposed impact. Back up the artifact only immediately before an accepted real edit; no revision increment before then. |
| Status-only rollback | Keep content hashes and historical sign-offs; invalidate active approval through the lifecycle decision. Do not call unchanged tasks content-stale. |
| Exact remote plan confirmed | Apply only through sw-publish. A changed plan, scope or hash needs new confirmation; a plain yes counts only for the exact dry-run just shown. |
| Nothing relevant changed | Skip maintenance and state why. |

## Repair

If fixes change inputs, rerun only the affected checks. Allow one bounded repair pass for
deterministic derived-output failures, then stop and explain what remains. Never rewrite
substantive requirements just to satisfy lint.

Without tool or connector access, return a clear blocked or partial result.
