# Lifecycle

The supported workflow is:

`Prepare -> Shape -> Specify -> Plan -> Review -> Publish`

There is no sync stage. Published-content requests never trigger sync or
reconciliation. Assets, visuals, knowledge, trace, lint and status support every
stage without becoming separately installed skills.

## Stage prerequisites

- Shape runs only on an unaccepted idea; acceptance still requires a human.
- Specify runs on an accepted feature or a valid amendment with an immutable baseline.
- Plan is an explicit action inside Specify, not an automatic stage.
- Review runs on request; approval recording needs verified evidence.
- Publish runs only when the destination is explicit and the plan is confirmed.

## Transitions

Finish the requested action, run bounded required maintenance, then stop at the next
human decision. Do not auto-advance into a new business stage.
