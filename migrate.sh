#!/bin/sh
# Specwright migrate: replace an older install with the files of this release.
#
#   sh migrate.sh [--dry-run] [--yes] [--no-backup] [--flow-auto] <target dir>
#
# The target kind is detected:
#   skills dir   a folder holding installed sw-* skills (~/.claude/skills, .claude/skills,
#                .agents/skills, ...) or an empty/new folder. Every Specwright sw-* folder is
#                removed (also skills that no longer ship) and the fresh sw-* folders are copied.
#   kit checkout a clone of the kit (has skills/sw-start or .claude-plugin/plugin.json).
#                skills/, commands/, hooks/, .claude-plugin/, templates/ are replaced; top-level
#                kit files are overwritten; new tests are added; nothing else is touched.
#   workspace    a spec workspace (project.yaml or workspace.yaml). Nothing is deleted:
#                AGENTS.md is refreshed with the new standing rules; --flow-auto also sets
#                governance.flow to auto.
#
# Old files are moved to .specwright-backup-<target name>-<time>/ beside the target unless
# --no-backup.
# In a skills destination, sw-* is reserved: matching files, folders and links are replaced.
# Exit codes: 0 done (or dry run), 1 refused or aborted, 2 usage.
set -eu

SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DRY=0; YES=0; BACKUP=1; FLOW=0; TARGET=""

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --yes|-y) YES=1 ;;
    --no-backup) BACKUP=0 ;;
    --flow-auto) FLOW=1 ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) [ -z "$TARGET" ] || usage; TARGET=$1 ;;
  esac
  shift
done
[ -n "$TARGET" ] || usage
[ -d "$SRC/skills/sw-start" ] || { echo "error: run migrate.sh from the new kit folder (skills/sw-start missing in $SRC)" >&2; exit 1; }

mkdir -p "$TARGET" 2>/dev/null || true
[ -d "$TARGET" ] || { echo "error: cannot use $TARGET" >&2; exit 1; }
TARGET=$(CDPATH= cd -- "$TARGET" && pwd)
case "$TARGET" in
  /|"$HOME") echo "error: refusing to migrate into $TARGET; name the skills folder itself" >&2; exit 1 ;;
esac
[ "$TARGET" != "$SRC" ] || { echo "error: target is the source folder" >&2; exit 1; }
case "$SRC/" in "$TARGET/"*) echo "error: target contains the source folder" >&2; exit 1 ;; esac

NEW_VERSION=$(sed -n 's/^KIT_VERSION = "\(.*\)"/\1/p' "$SRC/skills/_shared/scripts/kitlib/schema.py")
STAMP=$(date +%Y%m%d-%H%M%S)
# Beside the target, so agents never discover backed-up skills as live ones.
BACKDIR="$(dirname -- "$TARGET")/.specwright-backup-$(basename -- "$TARGET")-$STAMP"
PLAN=""

say() { printf '%s\n' "$*"; }
plan() { PLAN="$PLAN
$*"; }

move_out() {  # remove one path, keeping a backup copy unless --no-backup
  if [ "$BACKUP" -eq 1 ]; then
    rel=${1#"$TARGET"/}
    mkdir -p "$BACKDIR/$(dirname -- "$rel")"
    mv -- "$1" "$BACKDIR/$rel"
  else
    rm -rf -- "$1"
  fi
}

copy_in() {  # copy one path from the source, overwriting
  rm -rf -- "$2"
  mkdir -p "$(dirname -- "$2")"
  cp -R -- "$1" "$2"
  find "$2" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
}

# ---- detect the kind --------------------------------------------------------------------------
RULES_DIR="$TARGET"
if [ -f "$TARGET/project.yaml" ] || [ -f "$TARGET/workspace.yaml" ]; then
  KIND=workspace
  # Embedded layout: the rules live at the repository root, one level above .specwright/.
  [ "$(basename -- "$TARGET")" = ".specwright" ] && [ -f "$(dirname -- "$TARGET")/AGENTS.md" ] \
    && RULES_DIR=$(dirname -- "$TARGET")
elif [ -f "$TARGET/.specwright/project.yaml" ] || [ -f "$TARGET/.specwright/workspace.yaml" ]; then
  KIND=workspace
  TARGET="$TARGET/.specwright"
elif [ -d "$TARGET/skills/sw-start" ] || { [ -f "$TARGET/.claude-plugin/plugin.json" ] && grep -q '"specwright"' "$TARGET/.claude-plugin/plugin.json"; }; then
  KIND=kit
else
  KIND=skills
fi

case "$KIND" in
  skills)
    OLD=""
    for d in "$TARGET"/sw-*; do
      [ -e "$d" ] || [ -L "$d" ] || continue
      if [ ! -L "$d" ] && [ -d "$d" ]; then
        real=$(CDPATH= cd -- "$d" && pwd -P)
        [ "$real" != "$SRC/skills/$(basename "$d")" ] || { echo "error: target contains skill sources" >&2; exit 1; }
      fi
      OLD="$OLD $d"
      plan "remove  $(basename "$d")"
    done
    if [ -z "$OLD" ] && [ -n "$(find "$TARGET" -mindepth 1 -maxdepth 1 \( -type f -o -name .git \) -print -quit)" ]; then
      echo "error: $TARGET holds files but no sw-* skills; it does not look like a skills folder" >&2
      exit 1
    fi
    for d in "$SRC"/skills/sw-*; do
      plan "install $(basename "$d") ($NEW_VERSION)"
    done
    plan "replace sw-* command entries in $(dirname -- "$TARGET")/commands"
    ;;
  kit)
    for p in skills commands hooks .claude-plugin templates; do
      [ -e "$SRC/$p" ] || continue
      [ -e "$TARGET/$p" ] && plan "replace $p/" || plan "add     $p/"
    done
    for f in AGENTS.md README.md Makefile LICENSE NOTICE migrate.sh "$SRC"/CHANGES-*.md; do
      f=$(basename "$f"); [ -f "$SRC/$f" ] && plan "write   $f"
    done
    for f in "$SRC"/tests/test_*.py; do
      [ -f "$f" ] && plan "write   tests/$(basename "$f")"
    done
    ;;
  workspace)
    plan "refresh $RULES_DIR/AGENTS.md (standing rules of $NEW_VERSION); nothing is deleted"
    [ "$FLOW" -eq 1 ] && plan "set     governance.flow = auto"
    ;;
esac

say "Specwright migrate -> $NEW_VERSION"
say "target: $TARGET ($KIND)"
[ "$KIND" = workspace ] || { [ "$BACKUP" -eq 1 ] && say "backup: $BACKDIR" || say "backup: none (--no-backup)"; }
say "plan:$PLAN"
[ "$DRY" -eq 1 ] && { say "dry run: nothing changed"; exit 0; }

if [ "$YES" -ne 1 ]; then
  if [ -t 0 ]; then
    printf 'Proceed? [y/N] '; read -r ans
    case "$ans" in y|Y|yes|YES) ;; *) say "aborted"; exit 1 ;; esac
  else
    echo "error: no terminal to confirm; rerun with --yes" >&2; exit 1
  fi
fi

# ---- apply ------------------------------------------------------------------------------------
case "$KIND" in
  skills)
    for d in "$TARGET"/sw-*; do
      [ -e "$d" ] || [ -L "$d" ] || continue
      move_out "$d"
    done
    for d in "$SRC"/skills/sw-*; do copy_in "$d" "$TARGET/$(basename "$d")"; done
    COMMANDS="$(dirname -- "$TARGET")/commands"
    for f in "$COMMANDS"/sw-*; do
      [ -e "$f" ] || [ -L "$f" ] || continue
      if [ "$BACKUP" -eq 1 ]; then
        mkdir -p "$BACKDIR/commands"
        mv -- "$f" "$BACKDIR/commands/$(basename "$f")"
      else
        rm -rf -- "$f"
      fi
    done
    mkdir -p "$COMMANDS"
    BASE=$(printf '%s' "$TARGET/" | sed 's/[\\&|]/\\&/g')
    for f in "$SRC"/commands/sw-*.md; do
      [ -f "$f" ] || continue
      sed "s|\${CLAUDE_PLUGIN_ROOT}/skills/|$BASE|g" "$f" >"$COMMANDS/$(basename "$f")"
    done
    CHECK_DIRS="$TARGET"
    ;;
  kit)
    for p in skills commands hooks .claude-plugin templates; do
      [ -e "$SRC/$p" ] || continue
      [ -e "$TARGET/$p" ] && move_out "$TARGET/$p"
      copy_in "$SRC/$p" "$TARGET/$p"
    done
    for f in AGENTS.md README.md Makefile LICENSE NOTICE migrate.sh "$SRC"/CHANGES-*.md; do
      f=$(basename "$f")
      [ -f "$SRC/$f" ] || continue
      [ -f "$TARGET/$f" ] && [ "$BACKUP" -eq 1 ] && { mkdir -p "$BACKDIR"; cp -- "$TARGET/$f" "$BACKDIR/$f"; }
      cp -- "$SRC/$f" "$TARGET/$f"
    done
    mkdir -p "$TARGET/tests"
    for f in "$SRC"/tests/test_*.py; do [ -f "$f" ] && cp -- "$f" "$TARGET/tests/"; done
    CHECK_DIRS="$TARGET/skills"
    ;;
  workspace)
    if [ -f "$RULES_DIR/AGENTS.md" ]; then
      cp -- "$RULES_DIR/AGENTS.md" "$RULES_DIR/AGENTS.md.bak-$STAMP"
      say "kept the old rules in $RULES_DIR/AGENTS.md.bak-$STAMP"
    fi
    cp -- "$SRC/skills/sw-start/assets/standing-rules.md" "$RULES_DIR/AGENTS.md"
    if [ "$FLOW" -eq 1 ]; then
      if command -v python3 >/dev/null 2>&1; then
        python3 "$SRC/skills/sw-start/scripts/workspace.py" governance set flow auto --cwd "$TARGET" \
          || say "note: flow not set (program workspace?); run: workspace.py governance set flow auto --scope <S>"
      else
        say "note: python3 not found; set flow later with workspace.py governance set flow auto"
      fi
    fi
    say "done"
    exit 0
    ;;
esac

# ---- verify -----------------------------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  python3 - "$CHECK_DIRS" "$SRC/skills/_shared/scripts" <<'PY' || { echo "error: integrity check failed; restore from the backup" >&2; exit 1; }
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from kitlib import guard
bad = 0
for d in sorted(Path(sys.argv[1]).glob("sw-*")):
    problems = guard.check(d)
    print(f"  {d.name}: {'ok' if not problems else '; '.join(problems[:3])}")
    bad += bool(problems)
sys.exit(1 if bad else 0)
PY
else
  say "note: python3 not found; integrity not verified"
fi
say "done. Existing workspaces: sh migrate.sh --flow-auto <spec root> refreshes their AGENTS.md."
