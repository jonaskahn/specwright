# Knowledge capability

Builds and queries the derived knowledge graph that links epics, features, criteria,
tasks, rules, records, diagrams, Jira keys and code paths. This is the shared
replacement for the old sw-graph skill.

## Triggers

Every saved plan creation or revision runs the shared graph completion step
automatically. Also rebuild after other relevant content changes or when the graph is
stale. A verified no-change completion may skip a physical graph rewrite. A failed
update is reported as incomplete maintenance, not a successful refresh.

## Steps

1. Persist the requested plan and any collected assets or relationships first.
2. Evaluate drawing needs and save any justified diagram and links.
3. Refresh hashes, cards and trace data as applicable, then build or update graph
   nodes and edges with scripts/graph.py build.
4. Query the graph with scripts/graph.py map, show, neighbors, up, down, path,
   impact or context to confirm the saved plan and supported relationships are
   represented. Never invent dependencies from inference alone.

## Usage

Start with scripts/graph.py map and read the map. Pick the smallest query that
answers the question. When the first output line says stale or missing, run build
before trusting an answer; use --strict in automation.
