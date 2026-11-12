# Field ownership

Convert only fields this skill owns; preserve everything else byte for byte.

## Owned Jira fields

| Field | Source |
| --- | --- |
| `description` | Draft body, converted by `adf.md_to_adf`. |
| `summary` | Draft front matter `jira_summary`. |
| `labels` | Merged, never replaced: draft labels plus `specwright`, `feat:<id>`, `proj:<scope>`. |

Foreign fields, labels and links stay untouched. Never invent or overwrite `jira_parent`,
`jira_issuetype`, `jira_priority` or any other remote field.

## Local index writes

After every remote write succeeds, update exactly:

- registry columns `Jira key`, `Label`, `Entity property`, `Last published draft hash`, `State` for the feature;
- RTM column `Jira [sw-publish]`, written with `../_shared/scripts/trace.py set <id> --column "Jira [sw-publish]" --value <key> --as sw-publish`;
- card `status: published`, `home: jira`, and the `links` home URL.

Column ownership is enforced in `../_shared/scripts/kitlib/rtm.py` (rules:
`../_shared/references/rtm-contract.md`). sw-publish may not set the BO, BR/NFR or Story
draft columns; those belong to sw-spec.
