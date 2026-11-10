# Publish workflow

Publish exports, prepares a three-way dry-run and applies exactly one reviewed,
gated change after fresh typed confirmation. It is the only operation that may write
to Jira or Confluence.

## Steps

1. Resolve scope before any write. Read references/domain/publish-protocol.md and the
   ready-to-publish draft. Run scripts/publish.py plan with --feat <ID> and the
   resolved --scope.
2. Stop on any precondition failure: not ready-to-publish, absent or stale sign-off,
   unclean publish lint report, or workflow transitions enabled.
3. Validate referenced assets and visuals before the final dry-run. Do not introduce
   new visuals after approval or confirmation; required changes return to authoring or
   review and invalidate the old gate and plan.
4. Present the full dry-run and the exact confirmation token. Require fresh typed
   confirmation of the form `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`. A stored answer
   never authorizes a Jira write.
5. Only after confirmation, execute the plan through the Jira write capability, bound
   to the confirmed plan hash. Never delete remote artifacts or force workflow
   transitions without both manifest permission and separate human confirmation.
6. After every remote operation succeeds, update the registry Jira key, the RTM Jira
   column and the card status to published.

## Amendment baseline

For a published requirement, compare against an independently obtained current
snapshot supplied through normal ingestion. If its currency cannot be verified, stop
the comparison and explain the missing baseline. There is no sync trigger here.
