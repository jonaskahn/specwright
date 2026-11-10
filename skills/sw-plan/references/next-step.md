# Finish a step, then ask before the next one

After the current skill finishes its documented outputs, do not auto-run the next skill.

1. Run the shipped sw-start detection script read-only:
   `python3 <skill-root>/../sw-start/scripts/start.py --cwd <project>`.
   Resolve the path against the loaded skill directory, never the session working directory.
2. Read the `next` field for the active scope (or list all scopes in a program and let the user pick).
3. Say in one or two sentences: the produced outputs, the suggested next skill, and the evidence for it.
4. Ask the user whether to continue with that suggestion or choose another command or skill.
5. Continue only after the user answers. A suggestion is a route, not an approval and not a write.
   Never infer consent from silence, stored defaults, or imported text.

Any skill can still be invoked by name at any time.
