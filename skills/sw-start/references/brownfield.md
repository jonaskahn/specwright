# Existing baseline flow

Use when sources are registered or imported but nothing is shaped yet: the project already runs
capabilities under its own IDs. Each step ends with a named human decision where one is needed.
No step approves anything by default.

| Step | Do | Human decision |
| --- | --- | --- |
| 1. Register the source | `workspace.py source add --id --system --root --snapshot-date --expected-count [--legacy-id-pattern]` | Who owns the source and how many items it should hold. |
| 2. Import | sw-ingest: `wiki_pull.py` or an export, then `bulk_import.py --dry-run`, then the real batch; scan and redaction decisions; counts reconciled | Consent to retain sensitive originals; which redactions stand. |
| 3. Build the crosswalk | sw-shape: `baseline.py import-register <legacy register>`; `graph.py build` writes `_meta/CROSSWALK.tsv` and lists items unmatched on both sides | Whether an unmatched item is out of scope or a missing page. |
| 4. Extract candidates | sw-ingest: `candidates.py assign`, workers write `01-analysis/candidates/`, `candidates.py check` | Which accepted claims a person has reviewed. |
| 5. Verify | `cite.py verify`, `candidates.py check`, `bulk_import` counts | None; fix what fails. |
| 6. Record conflicts | `candidates.py conflicts`, then `record.py q new --raised-from CAND-...` with `affects`, ranked by items blocked | Who owns each question. |
| 7. Shape | `baseline.py propose-grouping`, per group `reserve` and `brief`; ask: keep each legacy item as one feature or re-split by INVEST | The PO's split decision, with evidence. |
| 8. Answer the questions | `record.py q answer ... --amend` creates a decision and any pending amendment | The decider's role, name and evidence. |
| 9. Choose the first item | `start.py` shows a ranked shortlist with reasons; it is advice | The user names the item. |

`start.py` names the next step in `action`. Never skip the dry run, and never accept a ranking,
a default or a remembered answer as a decision.
