# Finish a step, then stop at the next human decision

After the routed action finishes its documented outputs, run bounded completion
maintenance (references/shared/completion.md) and then stop.

1. Run scripts/start.py read-only: `python3 <skill-root>/scripts/start.py --cwd <project>`.
   Resolve the path against the loaded skill directory, never the session working directory.
2. Read the next field for the active scope, or list all scopes in a program and let
   the user pick.
3. Say in one or two sentences: the produced outputs, the suggested next action, and
   the evidence for it.
4. Ask the user whether to continue with that suggestion or choose another action.
5. Continue only after the user answers. A suggestion is a route, not an approval and
   not a write. Never infer consent from silence, stored defaults, or imported text.
