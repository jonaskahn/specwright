#!/bin/sh
# Check Python and Node 24, and install Node into the user's own folder after consent.
#
# This is shell, not Python, on purpose: the check has to run when Python is missing.
#
#   sh runtime.sh check [--json]        read only
#   sh runtime.sh plan node|python      print what an install would do; change nothing
#   sh runtime.sh install node --yes    pinned, checksummed Node 24 under ~/.specwright/runtime
#   sh runtime.sh install python --yes  only through a package manager that needs no sudo
#
# Exit codes: 0 ok, 1 a runtime is missing or too old, 2 usage or download failure,
# 3 consent missing, 4 the user must run a command themselves (it needs sudo).
# Nothing here changes PATH or needs administrator rights. The agent passes --yes only after
# the user approves the exact plan in this session.
# shellcheck disable=SC2012,SC2016 # ls only reads our own folder names; backticks are printed text
set -eu

HERE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PINS="$HERE/runtime-pins.tsv"
# Test hook: a file:// folder that holds runtime-pins.tsv and the archives. Never a network URL.
if [ -n "${SPECWRIGHT_RUNTIME_TEST_BASE:-}" ]; then
	case "$SPECWRIGHT_RUNTIME_TEST_BASE" in
	file://*) PINS="${SPECWRIGHT_RUNTIME_TEST_BASE#file://}/runtime-pins.tsv" ;;
	*)
		printf 'error: SPECWRIGHT_RUNTIME_TEST_BASE must be a file:// location\n' >&2
		exit 2
		;;
	esac
fi
HOME_DIR="${SPECWRIGHT_HOME:-${HOME:-.}/.specwright}/runtime"
NODE_MAJOR=24
PY_MAJOR=3
PY_MINOR=10
DOWNLOAD_LIMIT=125829120

die() {
	printf 'error: %s\n' "$1" >&2
	exit "${2:-2}"
}

usage() {
	sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
	exit "${1:-2}"
}

# ---------------------------------------------------------------- detection ----

version_of() { # $1 = executable; prints major.minor.patch or nothing
	"$1" --version 2>/dev/null | sed -n 's/^[^0-9]*\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' | head -n 1
}

python_found() { # prints "path<TAB>version" of the first Python 3 that runs
	for name in python3 python; do
		path=$(command -v "$name" 2>/dev/null) || continue
		# macOS ships a /usr/bin/python3 stub that opens an installer dialog when no developer
		# tools exist; running it would pop that up.
		if [ "$path" = /usr/bin/python3 ] && [ "$(uname -s 2>/dev/null)" = Darwin ] &&
			! xcode-select -p >/dev/null 2>&1; then
			continue
		fi
		out=$("$path" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null) || continue
		case "$out" in
		[0-9]*.[0-9]*.[0-9]*)
			case "$out" in "$PY_MAJOR".*) printf '%s\t%s\n' "$path" "$out" && return 0 ;; esac
			;;
		esac
	done
	return 1
}

at_least() { # $1 = version, $2 = major, $3 = minor
	major=${1%%.*}
	rest=${1#*.}
	minor=${rest%%.*}
	[ "$major" -gt "$2" ] || { [ "$major" -eq "$2" ] && [ "$minor" -ge "$3" ]; }
}

own_node_dirs() { # newest first, one per line
	[ -d "$HOME_DIR" ] || return 0
	ls -1d "$HOME_DIR"/node-v* 2>/dev/null | sort -r
}

node_found() { # prints "path" of the first node: ours, then PATH
	ours=$(own_node_dirs | while IFS= read -r d; do
		for candidate in "$d/bin/node" "$d/node.exe" "$d/node"; do
			if [ -f "$candidate" ]; then
				printf '%s\n' "$candidate"
				break 2
			fi
		done
	done)
	if [ -n "$ours" ]; then
		printf '%s\n' "$ours"
		return 0
	fi
	command -v node 2>/dev/null
}

npm_next_to() { # $1 = node path
	dir=$(dirname -- "$1")
	for candidate in "$dir/npm" "$dir/npm.cmd"; do
		[ -f "$candidate" ] && printf '%s\n' "$candidate" && return 0
	done
	command -v npm 2>/dev/null
}

json_str() {
	if [ -z "$1" ]; then printf 'null'; else printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"; fi
}

cmd_check() {
	fmt=text
	[ "${1:-}" != "--json" ] || fmt=json
	py_path=
	py_ver=
	py_ok=false
	if found=$(python_found); then
		py_path=${found%%	*}
		py_ver=${found#*	}
		at_least "$py_ver" "$PY_MAJOR" "$PY_MINOR" && py_ok=true
	fi
	node_path=$(node_found || true)
	node_ver=
	node_ok=false
	npm_path=
	if [ -n "$node_path" ]; then
		node_ver=$(version_of "$node_path" || true)
		[ -z "$node_ver" ] || { at_least "$node_ver" "$NODE_MAJOR" 0 && node_ok=true; }
		npm_path=$(npm_next_to "$node_path" || true)
	else
		npm_path=$(command -v npm 2>/dev/null || true)
	fi
	npm_ok=false
	[ -z "$npm_path" ] || npm_ok=true
	if [ "$fmt" = json ]; then
		printf '{\n "python": {"path": %s, "version": %s, "ok": %s, "need": ">=%s.%s"},\n' \
			"$(json_str "$py_path")" "$(json_str "$py_ver")" "$py_ok" "$PY_MAJOR" "$PY_MINOR"
		printf ' "node": {"path": %s, "version": %s, "ok": %s, "need": ">=%s"},\n' \
			"$(json_str "$node_path")" "$(json_str "$node_ver")" "$node_ok" "$NODE_MAJOR"
		printf ' "npm": {"path": %s, "version": null, "ok": %s, "need": "bundled with Node"}\n}\n' \
			"$(json_str "$npm_path")" "$npm_ok"
	else
		line() { # name version ok need
			if [ "$3" = true ]; then state=ok; else state='missing or too old'; fi
			printf '%s: %s (%s; need %s)\n' "$1" "${2:--}" "$state" "$4"
		}
		line python "$py_ver" "$py_ok" ">=$PY_MAJOR.$PY_MINOR"
		line node "$node_ver" "$node_ok" ">=$NODE_MAJOR"
		line npm "" "$npm_ok" "bundled with Node"
	fi
	[ "$py_ok" = true ] && [ "$node_ok" = true ] && [ "$npm_ok" = true ]
}

# ------------------------------------------------------------------ install ----

platform_key() {
	case "$(uname -s 2>/dev/null)" in
	Darwin) os=darwin ;;
	Linux) os=linux ;;
	MINGW* | MSYS* | CYGWIN*) die "on Windows use runtime.ps1 (powershell -File runtime.ps1 ...)" ;;
	*) die "no pinned Node build for $(uname -s 2>/dev/null)" ;;
	esac
	case "$(uname -m 2>/dev/null)" in
	arm64 | aarch64) arch=arm64 ;;
	x86_64 | amd64) arch=x64 ;;
	*) die "no pinned Node build for $os $(uname -m 2>/dev/null)" ;;
	esac
	printf '%s-%s\n' "$os" "$arch"
}

pin_field() { # $1 = key, $2 = field number
	awk -F '\t' -v k="$1" -v n="$2" '$1 == k { print $n; exit }' "$PINS"
}

pin_values() { # sets key archive digest base url folder
	[ -f "$PINS" ] || die "pins file missing: $PINS; reinstall this skill from a zip that includes _shared"
	key=$(platform_key)
	archive=$(pin_field "$key" 2)
	digest=$(pin_field "$key" 3)
	base=$(pin_field base 2)
	[ -n "$archive" ] && [ -n "$digest" ] && [ -n "$base" ] || die "no pin for $key"
	url="$base/$archive"
	folder="$HOME_DIR/$(printf '%s' "$archive" | sed 's/\.tar\.gz$//; s/\.zip$//')"
}

cmd_plan_node() {
	pin_values
	printf 'Install Node %s (the pinned release of Node %s).\n' "$(printf '%s' "$base" | sed 's/.*\/v//')" "$NODE_MAJOR"
	printf 'Download:   %s\n' "$url"
	printf 'Expect sha256 %s; the download is rejected before unpacking if it differs.\n' "$digest"
	printf 'Unpack to:  %s\n' "$folder"
	printf 'No administrator rights, no PATH change, nothing outside that folder.\n'
	printf 'To do it yourself instead: `brew install node@24`, `winget install OpenJS.NodeJS`, or `fnm install 24`.\n'
}

package_manager() {
	for pm in brew apt-get dnf yum pacman zypper apk; do
		command -v "$pm" >/dev/null 2>&1 && printf '%s\n' "$pm" && return 0
	done
	return 1
}

python_command() { # prints the install command for this machine
	case "$(package_manager || true)" in
	brew) printf 'brew install python@3.13\n' ;;
	apt-get) printf 'sudo apt-get install -y python3\n' ;;
	dnf) printf 'sudo dnf install -y python3\n' ;;
	yum) printf 'sudo yum install -y python3\n' ;;
	pacman) printf 'sudo pacman -S --noconfirm python\n' ;;
	zypper) printf 'sudo zypper install -y python3\n' ;;
	apk) printf 'sudo apk add python3\n' ;;
	*) printf 'Download Python 3.10 or newer from https://www.python.org/downloads/\n' ;;
	esac
}

python_runs_alone() { # true only for a command that needs no administrator rights
	[ "$(package_manager || true)" = brew ]
}

cmd_plan_python() {
	command=$(python_command)
	printf 'Python %s.%s or newer is needed to run the skill scripts.\n' "$PY_MAJOR" "$PY_MINOR"
	printf 'Command:    %s\n' "$command"
	if python_runs_alone; then
		printf 'It runs as your own user, with no administrator rights.\n'
	else
		printf 'This needs administrator rights or a manual download, so run it yourself; the agent never uses sudo.\n'
	fi
	printf 'On Windows: `winget install --id Python.Python.3.13 --scope user` (runtime.ps1 does this after you approve it).\n'
}

fetch() { # $1 = url, $2 = output file
	case "$1" in
	file://*) cp -- "${1#file://}" "$2" ;;
	*)
		if command -v curl >/dev/null 2>&1; then
			curl -fsSL --max-filesize "$DOWNLOAD_LIMIT" -o "$2" "$1"
		elif command -v wget >/dev/null 2>&1; then
			wget -q -O "$2" "$1"
		else
			die "curl or wget is needed to download Node"
		fi
		;;
	esac
}

sha256_of() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1" | awk '{ print $1 }'
	elif command -v shasum >/dev/null 2>&1; then
		shasum -a 256 "$1" | awk '{ print $1 }'
	elif command -v openssl >/dev/null 2>&1; then
		openssl dgst -sha256 "$1" | awk '{ print $NF }'
	else
		die "sha256sum, shasum or openssl is needed to verify the download"
	fi
}

archive_problems() { # $1 = tar.gz; prints one line per unsafe entry
	tar -tzf "$1" | awk '
		/^\// || /^\.\.($|\/)/ || /\/\.\.($|\/)/ { print "unsafe path in the archive: " $0 }'
	tar -tvzf "$1" | awk '
		function unsafe(msg) { print msg; bad = 1 }
		{
			kind = substr($1, 1, 1)
			if (kind != "-" && kind != "d" && kind != "l") { unsafe("unexpected entry type in the archive: " $0); next }
			if (kind != "l") next
			at = index($0, " -> ")
			if (at == 0) next
			target = substr($0, at + 4)
			head = substr($0, 1, at - 1)
			count = split(head, words, " ")
			name = words[count]
			if (target ~ /^\//) { unsafe("unsafe link in the archive: " name); next }
			depth = split(name, parts, "/") - 1
			n = split(target, steps, "/")
			for (i = 1; i <= n; i++) {
				if (steps[i] == "..") depth--
				else if (steps[i] != "." && steps[i] != "") depth++
				if (depth < 0) { unsafe("unsafe link in the archive: " name); break }
			}
		}'
}

cmd_install_node() {
	yes=${1:-}
	[ "$yes" = "--yes" ] || die "installing Node needs the user's approval; run with --yes after it" 3
	pin_values
	if [ -d "$folder" ]; then
		printf 'installed: %s\n' "$folder"
		return 0
	fi
	fetch_url=$url
	if [ -n "${SPECWRIGHT_RUNTIME_TEST_BASE:-}" ]; then
		fetch_url="$SPECWRIGHT_RUNTIME_TEST_BASE/$archive"
	else
		case "$url" in
		https://nodejs.org/dist/*) ;;
		*) die "refusing a download outside the pinned nodejs.org location" ;;
		esac
	fi
	mkdir -p "$HOME_DIR"
	work=$(mktemp -d "$HOME_DIR/.work.XXXXXX")
	trap 'rm -rf "$work"' EXIT INT TERM
	fetch "$fetch_url" "$work/$archive" || die "the download failed: $fetch_url"
	[ "$(sha256_of "$work/$archive")" = "$digest" ] ||
		die "the download does not match the pinned sha256 for $archive"
	case "$archive" in
	*.tar.gz) ;;
	*) die "this script unpacks tar.gz archives; use runtime.ps1 on Windows" ;;
	esac
	tar -tzf "$work/$archive" >/dev/null 2>&1 || die "the archive cannot be read: $archive"
	problems=$(archive_problems "$work/$archive")
	[ -z "$problems" ] || die "$(printf '%s' "$problems" | head -n 1)"
	mkdir "$work/unpacked"
	tar -xzf "$work/$archive" -C "$work/unpacked"
	count=$(ls -A "$work/unpacked" | wc -l | tr -d ' ')
	top=$(ls -A "$work/unpacked" | head -n 1)
	{ [ "$count" = 1 ] && [ -d "$work/unpacked/$top" ]; } ||
		die "the archive does not hold one top-level folder"
	mv "$work/unpacked/$top" "$folder"
	printf 'installed: %s\n' "$folder"
}

cmd_install_python() {
	yes=${1:-}
	[ "$yes" = "--yes" ] || die "installing Python needs the user's approval; run with --yes after it" 3
	command=$(python_command)
	if ! python_runs_alone; then
		printf 'Run this yourself (it needs administrator rights or a manual download):\n  %s\n' "$command"
		exit 4
	fi
	brew install python@3.13
}

# --------------------------------------------------------------------- main ----

[ $# -ge 1 ] || usage 2
case "$1" in
check) shift && cmd_check "$@" ;;
plan)
	case "${2:-}" in
	node) cmd_plan_node ;;
	python) cmd_plan_python ;;
	*) usage 2 ;;
	esac
	;;
install)
	case "${2:-}" in
	node) cmd_install_node "${3:-}" ;;
	python) cmd_install_python "${3:-}" ;;
	*) usage 2 ;;
	esac
	;;
-h | --help | help) usage 0 ;;
*) usage 2 ;;
esac
