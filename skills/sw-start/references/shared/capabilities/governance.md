# Governance capability

Shared checks for approval, destination resolution, dry-run comparison and
write-confirmation. Shared access does not confer approval-recording or remote-write
authority; only Review and Publish may call their mutating entrypoints.

## Checks

- Approval evidence verification: references/domain/approval-evidence.md and
  references/domain/review-checklist.md; the Review operation owns the mutating call.
- Destination resolution: Markdown, Jira or both must be explicit before a push or
  publish without a named destination. A stored answer never authorizes a Jira write.
- Dry-run comparison: scripts/publish.py plan prints the three-way dry-run; the
  Publish operation owns the apply call.
- Exact-plan confirmation: a remote plan requires fresh typed confirmation of the
  exact plan in the current session. Changed plan, scope or hash requires new
  confirmation.
- Write audit: every remote write is recorded in the append-only write log.
