# Runtimes

Specwright needs Python 3.10 or newer for every script. Only sw-view needs Node 24 or newer,
to build and show the console.

## Check first, without Python

The check is a shell script, not Python, because a Python check cannot report that Python is
missing. Run it before any other script:

```sh
sh _shared/scripts/runtime.sh check            # macOS, Linux, Git Bash
powershell -NoProfile -File _shared/scripts/runtime.ps1 check   # Windows
```

It prints Python, Node and npm with their versions (`--json` / `-Json` for a machine reading),
searching PATH and `~/.specwright/runtime/`. Exit 0 means all three are fine, 1 means one is
missing or too old. After that, Python tools such as `start.py` and `view.py doctor` report the
same facts.

## Installing

Never install anything without approval of the exact command in this session. A remembered
yes is not approval.

1. Run `runtime.sh plan node` or `runtime.sh plan python` (`runtime.ps1 plan ...` on Windows).
   It changes nothing and prints the exact steps.
2. Show the plan and ask once.
3. After a yes, run `runtime.sh install node --yes` (`install node -Yes` on Windows). The
   script refuses without it (exit 3). For Node it downloads the pinned official archive,
   checks the sha256 from `runtime-pins.tsv` before unpacking, rejects absolute or `..`
   paths, unpacks into `~/.specwright/runtime/`, needs no administrator rights and does not
   change PATH.
4. Python installs only through a package manager that needs no administrator rights (Homebrew
   on macOS, winget on Windows). On Linux the script prints the `sudo` command (exit 4) and the
   user runs it; the agent never uses sudo.
5. A no leaves everything except sw-view working. Say that and continue.

The console build also runs `npm ci` once per project. That needs the network and is part of
the same approval. It runs with `--ignore-scripts`.
