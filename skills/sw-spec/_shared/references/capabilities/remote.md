# Remote capabilities

Skills name remote tools by capability, not by product. Before the first call, say which session
tool provides the capability. Never improvise credentials and never print a token.

| Capability | Meaning | Used by | When absent |
| --- | --- | --- | --- |
| `jira-read` | Read one Jira issue: fields, update timestamp, links. | sw-ingest, sw-spec, sw-publish | Ask for pasted issue data; mark unread fields UNKNOWN. |
| `jira-search` | Search issues by JQL or label, only when a read is not enough. | sw-ingest, sw-spec, sw-publish | Ask for a pasted list. |
| `wiki-read` | Read a Confluence page or page tree. | sw-ingest | Ask for an export; mark unread fields UNKNOWN. |
| `jira-write` | Execute a confirmed publish plan. | sw-publish only | Stop after the dry-run; write nothing. |

## Fallback readers

When no session tool supplies a read, a read-only adapter ships with the skill. Check that its
environment variables are set (names only; never print the values):

- Jira: `SPECWRIGHT_JIRA_SITE`, `SPECWRIGHT_JIRA_EMAIL`, `SPECWRIGHT_JIRA_TOKEN`. Read one issue with
  `python3 _shared/scripts/kitlib/jira_rest.py <KEY>` (exit 0 read, 2 not configured, 3 remote failure).
- Wiki: `SPECWRIGHT_WIKI_SITE`, `SPECWRIGHT_WIKI_EMAIL`, `SPECWRIGHT_WIKI_TOKEN`. Read a tree with
  sw-ingest's `scripts/wiki_pull.py` (exit 4 means the pull is incomplete).

If a variable is unset, the adapter is not available: ask for pasted data instead. There is no
shipped command that writes to Jira; `jira-write` exists only as a session tool.
