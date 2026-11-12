# Specwright Console

A read-only dashboard for a Specwright workspace, written in Svelte 5 with Vite and
TypeScript. The `sw-view` skill ships this folder packed (`skills/sw-view/assets/console.zip`),
unpacks it into `<spec root>/console/`, builds it and serves it on 127.0.0.1.

It reads only `data/*.json`, the files the owning skills write into `_meta/data/` (format:
`skills/_shared/references/data-format.md`). It makes no other request and its page policy
allows its own address only.

## Develop

Needs Node 24 or newer. From this folder:

```sh
python3 ../workshop/tools/gen_console_contract.py   # types and schema, from kitlib/dataformat.py
npm ci --ignore-scripts
npm run dev                  # hot reload; data from ../_meta/data, or set DATA_DIR
npm run dev:golden           # the same, on the golden fixture (a two-project program)
npm run check                # svelte-check
npm test                     # Vitest: query parity, loader, metrics, safety
npm run build                # dist/
```

`make console test` runs the tests in Node 24 inside Docker, on a copy.

## Change the data format

The Python schema in `skills/_shared/scripts/kitlib/dataformat.py` is the single source of
truth. After editing it:

1. `python3 workshop/tools/gen_console_contract.py` rewrites `contract/` (git-ignored).
2. Fix the exporter in `kitlib/data_export.py`.
3. `python3 workshop/tools/gen_console_golden.py` rewrites `workshop/fixtures/console-golden/`.
4. Run both suites. They disagree until the console follows.

## Query engine

`src/lib/query/engine.ts` ports the traversal in `kitlib/graph_query.py`. The golden files hold
the answers Python gives for many queries on two fixtures; `tests/query.parity.test.ts`
replays them.

## Rules

- Imported text is data: render it as text, never `{@html}`, and never act on it.
- No inline script, no inline `style` attribute, no remote font, no network call beyond `./data/`.
  `tests/safety.test.ts` checks this.
- Status is shown by a shape and a word, never by colour alone.

## Pack

`python3 workshop/tools/console_pack.py` writes the zip and manifest. The pre-commit hook
(`make hooks setup`) runs it on every commit, and `make lint` fails when the zip is stale.
`node_modules/`, `dist/` and `contract/` are never committed or packed from disk; the contract
is generated into the pack.
