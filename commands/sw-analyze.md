---
name: sw-analyze
description: Analyses an existing system or feature, wherever it lives (code in this repo or beside it, tests, docs, Jira, another system) and compares what it should do with what it does today, criterion by criterion, as a gap table (done, partial, missing, divergent, unknown). Adopts a project mid-life: detects code roots, writes a light inventory of candidate features, and recovers a feature's current behaviour with code citations. Use when asked to analyse, understand, audit or take over an existing feature or codebase, to find what is missing in a partly built feature, before changing or fixing existing behaviour, or to check whether a change is really shipped. Do NOT use to write stories (use sw-spec) or to import documents (use sw-ingest).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-analyze/SKILL.md`. Treat the arguments as the feature or area to analyse. Keep all runtime references anchored to that skill directory.
