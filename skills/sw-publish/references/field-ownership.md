# field ownership

Only convert fields this skill owns; everything else is preserved byte for byte.

## Owned fields

- `description` — converted from the draft body (`adf.md_to_adf`).
- `summary` — taken from the draft front matter `jira_summary`.
- `labels` — merged, never replaced: the draft labels plus `specwright`,
  `feat:<id>` and `proj:<scope>`.

Foreign fields, labels and links stay untouched. `jira_parent`, `jira_issuetype`,
`jira_priority` and any other remote fields are never invented or overwritten.

## Local index ownership

After a successful remote write, sw-publish updates exactly:

- the registry `Jira key`, `Label`, `Entity property`, `Last published draft hash` and
  `State` columns for the feature;
- the RTM `Jira [sw-publish]` column;
- the card `status` to `published`, `home` to `jira`, and the `links` home URL.

Registry column ownership is enforced in `lib/kitlib/rtm.py`; sw-publish may not set
the `BO`, `BR/NFR` or `Story draft` columns, which belong to sw-spec.
