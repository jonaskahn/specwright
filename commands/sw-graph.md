---
name: sw-graph
description: Builds and queries the derived knowledge graph that links every epic, feature, acceptance criterion, task, business rule, record, diagram, Jira key and code path of a project or program. Use when asked to map the specs, find what links to BR-001, trace an AC up to its epic, show what FEAT-001 touches, rebuild or check the graph, or give an agent the files to read for an item. Do NOT use for editing requirements (use sw-spec), RTM column ownership (use sw-trace) or Jira writes (use sw-publish).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-graph/SKILL.md`. Treat this invocation as `/sw-graph` and keep all runtime references anchored to that skill directory.
