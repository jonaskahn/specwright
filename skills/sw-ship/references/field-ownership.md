# Field ownership

Convert only fields this skill owns; preserve everything else byte for byte.

## Owned Jira fields

| Field | Source |
| --- | --- |
| `description` | Draft body, converted by `adf.md_to_adf`. |
| `summary` | Draft front matter `title` (at most 100 characters). |
| `labels` | Merged, never replaced: existing labels plus `specwright`, `feat:<id>`, `proj:<scope>`. |
| `parent` | The epic's Jira key from the registry, planned by `levels_plan`. |
| `issuetype` | Derived from the level (`Epic`, `Story`, `Sub-task`), overridable in `publish.issue_types`. |
| `priority` | Derived from story `priority` (`must` High, `should` Medium, `could` Low), overridable in `publish.priority_map`. |

These three are derived at publish and are not story keys. Foreign fields, labels and links stay
untouched. Do not store `jira_summary`, `jira_parent`, `jira_issuetype` or `jira_priority` on the story.

## Local index writes

After every remote write succeeds, update exactly:

- registry columns `Jira key`, `Label`, `Entity property`, `Last published draft hash`, `State` for the feature;
- RTM column `Jira [sw-ship]`, written with `_shared/scripts/trace.py set <id> --column Jira --value <key> --as sw-ship` (name the column without its owner tag);
- card `status: published`, `home: jira`, and the `links` home URL.

Column ownership is enforced in `_shared/scripts/kitlib/rtm.py` (rules:
`_shared/references/rtm-contract.md`). sw-ship may not set the BO, BR/NFR or Story
draft columns; those belong to sw-craft.
