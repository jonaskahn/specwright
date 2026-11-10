# Shared context

Specwright turns a software idea into implementation-ready work through one installed
skill and four primary actions. A story (BA/PO word) and a feature (Dev/QA word) are
the same item, written FEAT-NNN; never create a STORY identifier.

## Read order

1. Discover: the public name and description.
2. Activate: SKILL.md plus references/shared/safety.md.
3. Route: the detection script plus references/domain/routing.md.
4. Work: the selected references/workflows/ file.
5. Complete: references/shared/completion.md, then stop at the next human decision.

## Ownership

- Prepare owns workspace setup, source intake and idea shaping.
- Shape is the explicit action for an unaccepted idea.
- Specify owns requirement authoring and the explicit planning action.
- Review owns assessment and is the only operation that records human approval.
- Publish is the only operation that may write to Jira or Confluence.

## Terminology

Use FEAT for features. Keep IDs stable; withdrawn IDs remain tombstones and are never
reused. Store external key mappings in the ID registry and use qualified IDs across
projects.
