# Sources and research limits

Accessed 2026-11-10. These are references, not bundled material. Implementations,
templates and instructions in Specwright were independently authored.

## Portable skills and distribution

- [Agent Skills specification](https://agentskills.io/specification) and the
  [Vercel skills CLI](https://github.com/vercel-labs/skills): standard
  `skills/<name>/SKILL.md` discovery and `npx skills add` installation. Specwright ships
  self-contained skill folders so generic installers can copy one folder without a
  sibling runtime.
- [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces):
  `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` expose the same
  eleven skills through the marketplace route. Host-specific command placeholders stay in
  `commands/`; skills remain host-neutral.
- [Agent Skills specification](https://agentskills.io/specification): required name and
  description; optional license, compatibility, metadata and experimental allowed-tools.
  Specwright uses only portable name and description. Names match folders; descriptions
  remain under 1024 characters, with a tighter 900-character budget here.
- [Authoring guidance](https://agentskills.io/skill-creation/best-practices): progressive
  disclosure and concise entrypoints. Trigger data here is authored, not a measured score.
- [Codex skills](https://developers.openai.com/codex/skills),
  [Copilot skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills),
  [Cursor skills](https://cursor.com/docs/skills),
  [Gemini skills](https://geminicli.com/docs/cli/skills/), and
  [Claude Code skills](https://code.claude.com/docs/en/skills). Discovery support changes
  by client version. Project-scope `.agents/skills` plus `.claude/skills` is the intended
  layout; Copilot documentation inspected chiefly described its cloud agent. Generic
  installation routes defer lifecycle, update and removal to the skills CLI.

## Jira and Confluence

- [Rovo MCP capabilities](https://developer.atlassian.com/cloud/rovo-mcp/guides/supported-tools/):
  reads, search and writes are separate capabilities; tool names and availability vary
  with scopes, gateways and discovery. Destructive groups are not required by Specwright.
- [Jira issue search](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/):
  use enhanced `/rest/api/3/search/jql` and its next-page token, not legacy search.
  Approximate count is a POST and an estimate, not an exact completeness check. Search
  is eventually consistent; reconcile known issue IDs after ambiguous writes where possible.
- [Rate limits](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/):
  handle Retry-After and bounded backoff on reads. Limits differ by authentication
  and endpoint; do not hard-code a throughput promise or automatically retry creates.
- [Entity properties](https://developer.atlassian.com/cloud/jira/platform/jira-entity-properties/):
  REST-set properties need app-provided indexing for JQL. They are mutable and not private.
- [Attachments](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/):
  multipart field `file`, header `X-Atlassian-Token: no-check`; size and permission
  errors require human review, not blind retries.
- [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/):
  a document has type `doc`, version 1 and content. The converter supports a deliberately
  closed subset; other nodes retain warnings and visible placeholders.
- [Confluence pages](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/):
  request a body representation explicitly. Version number is the page drift key.
  Include macros are not followed recursively.

Reported historical MCP pagination and Confluence ADF-version bugs were already fixed
upstream when inspected. Pagination guards remain useful, but those bugs are not
presented as current platform defects. Absence of Jira ETag support was not proven;
timestamp rechecks reduce races but do not establish atomic concurrency control.

## BA methods

- [EARS](https://alistairmavin.com/ears/): ubiquitous, state-driven, event-driven,
  optional-feature, unwanted-behaviour and combined sentence patterns.
- [Gherkin](https://cucumber.io/docs/gherkin/reference/): context, event and observable
  outcome. Specwright uses plain Given/When/Then prose, not a Cucumber runtime.
- [Bill Wake: INVEST](https://xp123.com/invest-in-good-stories-and-smart-tasks/):
  independent, negotiable, valuable, estimable, small and testable. These include
  human judgments that a structural linter cannot certify.
- [MoSCoW](https://www.agilebusiness.org/dsdm-project-framework/moscow-prioritisation.html):
  Must, Should, Could and Won't have this time. Priority labels are not vague prose.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/): name applicable criteria and review methods;
  merely naming AA does not prove conformance.
- [BABOK](https://www.iiba.org/career-resources/a-business-analysis-professionals-foundation-for-success/babok/)
  and [ISO quality models](https://iso25000.com/index.php/en/iso-25000-standards/iso-25010)
  are background references only. Paid text and unverified edition details are not
  reproduced or claimed as validated coverage. NFR defaults are discussion prompts.

## Prior art inspected

Thanks to [agentic-sdlc-kit](https://github.com/zeeshanhanif/agentic-sdlc-kit),
[diagram-design](https://github.com/cathrynlavery/diagram-design),
[knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins),
[Claude-Cortex](https://github.com/NickCrew/Claude-Cortex),
[Rune](https://github.com/rune-kit/rune),
[claude-sdlc](https://github.com/lantisprime/claude-sdlc),
[agent-sdlc](https://github.com/smarzban/agent-sdlc), and
[agent-skills](https://github.com/mwillbanks/agent-skills). See NOTICE.

Useful ideas were stable IDs, one-owner trace columns, mechanical gates, read-before-ask,
human evidence, capability-based integration and per-type diagram conventions. We do
not distribute their prose, templates or code. In particular the diagram implementation
uses new offline theme-aware templates rather than upstream fonts or CSS.

## Diagram-design comparison

The installed cathrynlavery/diagram-design catalog informed type coverage,
semantic-before-layout selection and static-first review. Specwright's renderer,
contracts, templates, palette and instructions are independently implemented.
Its web fonts, import tools, motion controller and source code are not bundled.
Forty-five primary types group close variants, including marimekko under treemap.
Source-ID chips, exact value tables, offline Python rendering and approval-safe
handoffs are Specwright-specific. Full client/embedding and accessibility review
remain manual; automated geometry checks are not semantic certification.

## Drawing look

The diagram theme follows the visual rules of the maintainer's Kumo Cockpit design notes (neutral cool palette, soft cards, one brand tint, shape-coded status). Only token values and rules were used; no logo, font, CSS or markup was copied.
