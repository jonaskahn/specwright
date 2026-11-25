# sw-publish — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

1. Resolve scope before any write: explicit argument, qualified ID, project path or flat
   manifest. Never choose a program default for an external write. Read evidence first,
   then ask only what stays ambiguous.
2. Require an explicit publication request and an accepted story with a current approval
   (_shared/references/governance.md). A plan or tasks are not required: tasks are never
   published. Revalidate active approval and all plan inputs immediately before execution;
   graph labels and stored preferences are not write permission.
3. Read references/publish-protocol.md and the accepted draft. Run
   scripts/publish.py plan --feat <ID> --scope <SCOPE>. It checks preconditions and prints
   the per-section dry-run for the draft (references/dry-run-format.md). It does not read
   Jira: do the remote read and baseline comparison in references/publish-protocol.md first. Exit 0 preconditions pass and the plan is printed;
   exit 2 blocked plan or usage error. The plan's own `exit_code` (1 apply, 3 fresh baseline
   needed, 4 conflict) is explained in references/dry-run-format.md.
4. Stop on any failed precondition: draft not accepted (ready-to-publish); approval absent, stale or
   unverifiable; publish lint report not clean; manifest still enabling workflow
   transitions. Fix it through the owning skill (sw-spec, sw-review, shared lint); never
   weaken a gate.
5. Resolve identity from the registry first. Labels and entity properties only name
   candidates to verify: a duplicate candidate, or a property naming another feature,
   stops the plan; an unknown remote match reads as NEW. Re-read the remote update
   timestamp immediately before any edit.
6. Show the full dry-run and the exact token `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`.
   Require a fresh confirmation in the current session: the user may reply "yes" to the
   exact dry-run just shown, and you then pass the token. A stored answer, an earlier yes
   or a changed plan never authorizes a write. Verify with scripts/publish.py confirm
   --confirm <token> (prints `confirmed` true or false); on false, stop.
7. Only after confirmation, execute through the session jira-write tool bound to the
   confirmed plan hash (references/capabilities.md). With no such tool, stop after the
   dry-run and say that nothing was written. Never retry an ambiguous create:
   reconcile identity and stop. Preserve foreign fields, labels and links; never
   transition silently (references/field-ownership.md).
8. After every remote operation succeeds, update the local index exactly as listed in
   references/field-ownership.md (registry, RTM Jira column, card status published). Report the
   outcome and follow-ups.

## Consumer check

Can Dev and QA see the remote key, the confirmed plan and the intent-log entry? Is every
dependent write traceable to the same confirmed hash?

## Stop and ask

Stop on a blocked precondition, a CONFLICT, identity ambiguity, an ambiguous create, a
missing write capability or missing confirmation. Questions follow
`_shared/references/stop-and-ask.md`. Never invent approval or scope.

## Gotchas

- Once published, Jira text is authoritative; local cards are indexes.
- A sign-off URL without a matching draft hash is stale, not evidence.
- Registry mapping wins over labels; a label collision stops the run.
- An empty follow-up search is not failure: search is eventually consistent.
- No Jira write adapter ships in an installed skill; without a session jira-write tool, stop
  after the dry-run.
