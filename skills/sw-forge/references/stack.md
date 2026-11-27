# Stack lock

`stack.yaml` sits beside `project.yaml` (program: also at the root, inherited; a project layer
replaces the program layer of the same name). Stories never name technology; plans, tasks and
agent prompts must use only the locked stack.

## Commands (`_shared/scripts/stack.py`)
| Do | Command |
| --- | --- |
| Propose from build files | `stack.py detect --write` (pom.xml, build.gradle, package.json, pyproject, go.mod, pubspec.yaml, *.csproj, compose, Dockerfile, *.tf, workflows) |
| Show effective profile | `stack.py show` |
| Change a value | `stack.py set backend.framework_version 3.3 --reason "<why>"` |
| Library rules | `stack.py lib allowed|forbidden|needs_approval <name> --reason "<why>"` |
| Convention | `stack.py convention "<rule>"` |
| Lock | `stack.py lock` (prints hash) → show it → on yes `stack.py lock --confirm <hash>` |
| Check tasks | `stack.py check --feat FEAT-NNN` (finish.py runs it for sw-forge) |

Fields per layer: language, version, framework, framework_version, build, test, notes, evidence.
Layers: backend, frontend, mobile, data, devops (code layers); qa, design, docs optional.

## Rules
- A locked profile changes only with `--reason`; the change unlocks it and is logged in
  `history`. Lock again after the user's yes.
- Every code-layer task carries `Stack:` with the layer line from `stack.py show`.
- A task naming a technology outside the profile, or a forbidden library, is a finding;
  finish.py stops the run on it. A needs-approval library is a stop-and-ask.
- No profile or not locked: reported once as advice; the run continues.
