# Remote capabilities

Skills name remote tools by capability, not by product. Before the first call, say which session
tool provides the capability. Never improvise credentials and never print a token.

| Capability | Meaning | Used by | When absent |
| --- | --- | --- | --- |
| `jira-read` | Read one Jira issue: fields, update timestamp, links. | sw-ingest, sw-spec, sw-publish | Ask for pasted issue data; mark unread fields UNKNOWN. |
| `jira-search` | Search issues by JQL or label, only when a read is not enough. | sw-ingest, sw-spec, sw-publish | Ask for a pasted list. |
| `wiki-read` | Read a Confluence page or page tree. | sw-ingest | Ask for an export; mark unread fields UNKNOWN. |
| `jira-write` | Execute a confirmed publish plan. | sw-publish only | Stop after the dry-run; write nothing. |

## No shipped fallback for Jira

No Jira reader or writer ships inside the skills. A Specwright source checkout holds a reference
REST adapter, but it is an integration seam, not part of an installed skill, and production use is
a separate decision. When no session tool supplies `jira-read`, ask for pasted issue data. When no
session tool supplies `jira-write`, nothing can be written: stop after the dry-run.

## Wiki fallback

sw-ingest ships a read-only wiki puller (its `wiki_pull` script). It needs `SPECWRIGHT_WIKI_SITE`,
`SPECWRIGHT_WIKI_EMAIL` and `SPECWRIGHT_WIKI_TOKEN`; check that they are set (names only, never the
values). Exit 4 means the pull is incomplete: never import it as whole. If they are unset, ask for an
export instead.
