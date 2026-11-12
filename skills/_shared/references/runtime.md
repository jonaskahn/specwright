# Runtimes

Specwright needs Python 3.10 or newer for every script. Only sw-view needs Node 24 or newer,
to build and show the console. Check both with `scripts/runtime.py check`.

## Installing Node

Never install anything without approval of the exact command in this session. A remembered
yes is not approval.

1. Run `runtime.py plan node`. It changes nothing and prints the pinned download, its sha256,
   the folder it unpacks to (`~/.specwright/runtime/`) and commands the user can run
   themselves (`brew`, `winget`, `fnm`).
2. Show the plan and ask once.
3. After a yes, run `runtime.py install node --yes`. The script refuses without `--yes`,
   checks the download against the pinned sha256 before it unpacks, needs no administrator
   rights and does not change PATH.
4. A no leaves everything except sw-view working. Say that and continue.

If Python is missing nothing runs: ask before using the system package manager.

The console build also runs `npm ci` once per project. That needs the network and is part of
the same approval. It runs with `--ignore-scripts`.
