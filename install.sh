#!/bin/sh
# Specwright installer: all seven skills, into the agents you choose.
#
#   curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --project
#   curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --agent cursor --agent claude-code -y
#
# No Node and no Python. Agent directories match `npx skills add`
# (vercel-labs/skills agents.ts). Every public skill is installed; there is
# no skill picker. The agent table below is the copy this script ships with.
set -eu

REPO="${SPECWRIGHT_REPO:-jonaskahn/specwright}"
REF="${SPECWRIGHT_REF:-main}"
SKILLS="sw-start sw-shape sw-ingest sw-spec sw-plan sw-review sw-publish"
INNER=76
TERMINAL=0
[ ! -t 1 ] || TERMINAL=1

# ---------------------------------------------------------------- output ----

ESC="$(printf '\033')"
if [ -n "${NO_COLOR:-}" ] || [ "$TERMINAL" = 0 ]; then
	COLOR=0
else
	COLOR=1
fi

if [ "$COLOR" = 1 ]; then
	# Phosphor green, the terminal kind. Dark screens get the bright tint; light
	# screens get a deeper one. SPECWRIGHT_THEME=light|dark overrides.
	_mode="either"
	if [ -n "${SPECWRIGHT_THEME:-}" ]; then
		_mode="$SPECWRIGHT_THEME"
	elif [ "$(uname -s 2>/dev/null)" = "Darwin" ]; then
		if defaults read -g AppleInterfaceStyle >/dev/null 2>&1; then
			_mode="dark"
		else
			_mode="light"
		fi
	elif command -v gsettings >/dev/null 2>&1; then
		_scheme="$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null || true)"
		case "$_scheme" in
		*dark*) _mode="dark" ;;
		"") _mode="either" ;;
		*) _mode="light" ;;
		esac
	fi
	case "$_mode" in
	dark)
		BRIGHT="$(printf '\033[38;2;57;255;70m')"
		LIGHT="$(printf '\033[38;2;40;220;64m')"
		MID="$(printf '\033[38;2;32;190;56m')"
		NOTE="$(printf '\033[38;2;150;255;160m')"
		SPEC="$(printf '\033[38;2;255;112;122m')"
		DANGER="$(printf '\033[38;2;184;140;128m')"
		;;
	light)
		BRIGHT="$(printf '\033[38;2;0;136;48m')"
		LIGHT="$(printf '\033[38;2;0;124;44m')"
		MID="$(printf '\033[38;2;0;112;40m')"
		NOTE="$(printf '\033[38;2;0;148;52m')"
		SPEC="$(printf '\033[38;2;204;42;74m')"
		DANGER="$(printf '\033[38;2;148;96;84m')"
		;;
	*)
		BRIGHT="$(printf '\033[38;2;0;160;56m')"
		LIGHT="$(printf '\033[38;2;0;148;52m')"
		MID="$(printf '\033[38;2;0;136;48m')"
		NOTE="$(printf '\033[38;2;0;172;60m')"
		SPEC="$(printf '\033[38;2;220;64;88m')"
		DANGER="$(printf '\033[38;2;160;112;100m')"
		;;
	esac
	DARK="$MID"
	OFF="$(printf '\033[0m')"
	BOLD="$(printf '\033[1m')"
else
	OFF=""; BRIGHT=""; LIGHT=""; MID=""; DARK=""; NOTE=""; SPEC=""; DANGER=""; BOLD=""
fi

UTF8=0
_probe="█"
if [ "$TERMINAL" = 1 ] && [ "${#_probe}" -eq 1 ]; then UTF8=1; fi

DASHES=""
_i=0
while [ "$_i" -lt "$INNER" ]; do DASHES="${DASHES}─"; _i=$((_i + 1)); done

FRAME=0
FIRST_SECTION=1
TMP_DIR=""

vislen() {
	_s="$(printf '%s' "$1" | sed "s/${ESC}\\[[0-9;]*m//g")"
	printf '%s' "${#_s}"
}

clip() {
	_rest="$1"
	_out=""
	_vis=0
	while [ -n "$_rest" ] && [ "$_vis" -lt $((INNER - 1)) ]; do
		case "$_rest" in
		"${ESC}"*)
			_out="$_out${_rest%%m*}m"
			_rest="${_rest#*m}"
			;;
		*)
			_head="${_rest#?}"
			_out="$_out${_rest%"$_head"}"
			_rest="$_head"
			_vis=$((_vis + 1))
			;;
		esac
	done
	printf '%s…' "$_out"
}

framed() {
	[ "$FRAME" = 1 ] || { printf '%s' "$1"; return 0; }
	_len="$(vislen "$1")"
	if [ "$_len" -gt "$INNER" ]; then _text="$(clip "$1")"; else _text="$1"; fi
	_len="$(vislen "$_text")"
	_pad=$((INNER - _len))
	[ "$_pad" -ge 0 ] || _pad=0
	printf '%s%s%*s%s' "${BRIGHT}│${OFF}" "$_text" "$_pad" '' "${BRIGHT}│${OFF}"
}

row() { printf '%s\n' "$(framed "$1")"; }
row_tty() { framed "$1" >/dev/tty; printf '\n' >/dev/tty; }
hline() { printf '%s%s%s\n' "${BRIGHT}$1${OFF}" "${BRIGHT}${DASHES}${OFF}" "${BRIGHT}$2${OFF}"; }

center_row() {
	_len="$(vislen "$1")"
	_left=$(((INNER - _len) / 2))
	[ "$_left" -ge 0 ] || _left=0
	row "$(printf '%*s%s' "$_left" '' "$1")"
}

clear_line() {
	if [ "$UTF8" = 1 ]; then
		printf '\r%s' "${ESC}[2K"
	fi
	return 0
}

step() {
	if [ "$UTF8" = 1 ]; then
		printf '%s' "$(framed "  ${BRIGHT}▶${OFF} $*")"
	else
		printf '  %s>%s %s\n' "$BRIGHT" "$OFF" "$*"
	fi
}

lead() { row "  ${BRIGHT}▶${OFF} $*"; }
done_() { clear_line; row "  ${BRIGHT}✓${OFF} $*"; }
note() { clear_line; row "  ${NOTE}·${OFF} ${NOTE}$*${OFF}"; }

section() {
	if [ "$FIRST_SECTION" = 1 ]; then FIRST_SECTION=0; else hline '├' '┤'; fi
	row ""
	row "  ${BOLD}$1${OFF}"
	row ""
}

screen_open() {
	if [ "$UTF8" = 0 ]; then
		printf '\n  SPECWRIGHT INSTALLER\n  %s skills  %s\n\n' "$REF" "$OS"
		return 0
	fi
	FRAME=1
	hline '┌' '┐'
	row ''
	center_row "${SPEC}███████╗██████╗ ███████╗ ██████╗${OFF}"
	center_row "${SPEC}██╔════╝██╔══██╗██╔════╝██╔════╝${OFF}"
	center_row "${SPEC}███████╗██████╔╝█████╗  ██║     ${OFF}"
	center_row "${SPEC}╚════██║██╔═══╝ ██╔══╝  ██║     ${OFF}"
	center_row "${SPEC}███████║██║     ███████╗╚██████╗${OFF}"
	center_row "${SPEC}╚══════╝╚═╝     ╚══════╝ ╚═════╝${OFF}"
	center_row "${BRIGHT}█ █ █ █▀█ █ ▄█▀ █ █ ▀█▀${OFF}"
	center_row "${BRIGHT}█▄█▄█ █▀▄ █ ▀▄█ █▀█  █ ${OFF}"
	row ''
	center_row "${BRIGHT}I N S T A L L E R${OFF}"
	row ''
	center_row "${LIGHT}seven skills · ${REF}${OFF}"
	center_row "${LIGHT}$(printf '%s' "$OS" | tr '[:lower:]' '[:upper:]')${OFF}"
	row ''
	hline '├' '┤'
}

screen_close() {
	[ "$FRAME" = 1 ] || return 0
	FRAME=0
	hline '└' '┘'
}

box_row() {
	_len="$(vislen "$1")"
	_pad=$((INNER - _len))
	[ "$_pad" -ge 0 ] || _pad=0
	printf '%s%s%*s%s\n' "${DANGER}│${OFF}" "$1" "$_pad" '' "${DANGER}│${OFF}" >&2
}

error_box() {
	_title="$1"
	shift
	if [ "$UTF8" = 0 ]; then
		printf '  %s!%s %s\n' "$BRIGHT" "$OFF" "$_title" >&2
		for line in "$@"; do printf '    %s\n' "$line" >&2; done
		return 0
	fi
	FRAME=0
	printf '\n' >&2
	printf '%s%s%s\n' "${DANGER}┌${OFF}" "${DANGER}${DASHES}${OFF}" "${DANGER}┐${OFF}" >&2
	box_row ""
	box_row "  ${DANGER}!${OFF} ${BOLD}$_title${OFF}"
	box_row ""
	for line in "$@"; do box_row "    $line"; done
	box_row ""
	printf '%s%s%s\n' "${DANGER}└${OFF}" "${DANGER}${DASHES}${OFF}" "${DANGER}┘${OFF}" >&2
}

die() {
	clear_line
	screen_close
	error_box "$@"
	exit 1
}

have() { command -v "$1" >/dev/null 2>&1; }

cleanup() {
	[ -n "$TMP_DIR" ] && rm -rf "$TMP_DIR"
	return 0
}
trap cleanup EXIT INT TERM

# --------------------------------------------------------------- options ----

SCOPE="global"
SCOPE_SET=0
ASSUME_YES="${SPECWRIGHT_INSTALL_YES:-0}"
TARGET="${SPECWRIGHT_TARGET:-}"
AGENT_ARGS=""
LIST_ONLY=0
INTERACTIVE=0
OS=""
STAT_BSD=0

usage() {
	cat <<EOF
Specwright installer

Usage: install.sh [options]

  --agent <id>      install for this agent (repeatable, or comma-separated)
  -g, --global      install for all projects (the default)
  --project         install into this project only
  --target <path>   project directory used when you pass --project
  -y, --yes         use the selected settings without prompting
  --list-agents     print agent ids and skill directories, then exit
  --help            this text

Every public skill is installed: ${SKILLS}.

Environment: SPECWRIGHT_REPO, SPECWRIGHT_REF, SPECWRIGHT_URL, SPECWRIGHT_ROOT,
SPECWRIGHT_TARGET, SPECWRIGHT_INSTALL_YES, NO_COLOR.
EOF
}

while [ $# -gt 0 ]; do
	case "$1" in
	--agent)
		AGENT_ARGS="$AGENT_ARGS ${2:?--agent needs a value}"
		shift 2
		;;
	--agent=*) AGENT_ARGS="$AGENT_ARGS ${1#*=}"; shift ;;
	-g | --global) SCOPE="global"; SCOPE_SET=1; shift ;;
	--project) SCOPE="project"; SCOPE_SET=1; shift ;;
	--target) TARGET="${2:?--target needs a value}"; shift 2 ;;
	--target=*) TARGET="${1#*=}"; shift ;;
	-y | --yes) ASSUME_YES=1; shift ;;
	--list-agents) LIST_ONLY=1; shift ;;
	-h | --help) usage; exit 0 ;;
	*) die "unknown option: $1" "run install.sh --help" ;;
	esac
done

if [ "$TERMINAL" = 1 ] && [ "$ASSUME_YES" = 0 ] && ( : </dev/tty ) 2>/dev/null; then
	INTERACTIVE=1
fi

ask() {
	if [ "$UTF8" = 1 ] && [ "$FRAME" = 1 ]; then
		printf '%s  %s▶%s %s ' "${BRIGHT}│${OFF}" "$BRIGHT" "$OFF" "$1" >/dev/tty
		IFS= read -r answer </dev/tty || die "Setup canceled: the terminal input closed."
		printf '%s' "${ESC}[1A${ESC}[2K" >/dev/tty
		row_tty "  ${BRIGHT}▶${OFF} $1 ${answer:-$2}"
	else
		printf '  %s> %s%s ' "$BRIGHT" "$1" "$OFF" >/dev/tty
		IFS= read -r answer </dev/tty || die "Setup canceled: the terminal input closed."
	fi
	[ -n "$answer" ] || answer="$2"
	printf '%s' "$answer"
}

# ------------------------------------------------------------- selections --

MENU_TTY_STATE=""
MENU_PICK=1

menu_enter() {
	[ "$INTERACTIVE" = 1 ] && [ "$UTF8" = 1 ] || return 1
	MENU_TTY_STATE="$(stty -g </dev/tty 2>/dev/null || true)"
	[ -n "$MENU_TTY_STATE" ] || return 1
	stty -echo -icanon min 1 time 0 </dev/tty 2>/dev/null || return 1
	trap 'stty "$MENU_TTY_STATE" </dev/tty 2>/dev/null || true; cleanup; exit 130' INT TERM HUP
}

menu_leave() {
	if [ -n "$MENU_TTY_STATE" ]; then
		stty "$MENU_TTY_STATE" </dev/tty 2>/dev/null || true
		MENU_TTY_STATE=""
	fi
	trap cleanup EXIT INT TERM
}

read_key() {
	_code="$(dd if=/dev/tty bs=1 count=1 2>/dev/null | od -An -tu1 | tr -d ' ')"
	[ -n "$_code" ] || return 1
	printf '%s' "$_code"
}

read_key_timed() {
	stty min 0 time 1 </dev/tty 2>/dev/null || true
	_code="$(dd if=/dev/tty bs=1 count=1 2>/dev/null | od -An -tu1 | tr -d ' ')"
	stty min 1 time 0 </dev/tty 2>/dev/null || true
	printf '%s' "$_code"
}

MENU_HEIGHT=3

menu_rewind() {
	[ "$1" -gt 0 ] && printf '%s[%dA' "$ESC" "$1" >/dev/tty
}

menu_row() {
	_line="  "
	_i=1
	for _item in "$@"; do
		if [ "$_i" = "$MENU_PICK" ]; then
			_line="$_line ${MENU_REV}[ $_item ]${MENU_OFF}"
		else
			_line="$_line ${MID}[$_item]${OFF}"
		fi
		_i=$((_i + 1))
	done
	row_tty "$_line"
}

menu_draw() {
	_prompt="$1"
	shift
	row_tty "  ${BRIGHT}▶${OFF} $_prompt"
	menu_row "$@"
	row_tty "  ${MID}←/→ to move · Enter to pick · q to cancel${OFF}"
}

menu_settle() {
	menu_rewind "$MENU_HEIGHT"
	printf '\r%s[2K%s\n' "$ESC" "$(framed "$1")" >/dev/tty
	_i=1
	while [ "$_i" -lt "$MENU_HEIGHT" ]; do
		printf '\r%s[M' "$ESC" >/dev/tty
		_i=$((_i + 1))
	done
}

menu_done() {
	menu_settle "  ${BRIGHT}▶${OFF} $MENU_PROMPT ${BOLD}${MENU_ANSWER}${OFF}"
}

menu_stop() {
	menu_settle "  ${MID}▶ $MENU_PROMPT (canceled)${OFF}"
	menu_leave
}

menu_select() {
	MENU_PROMPT="$1"
	MENU_PICK="$2"
	shift 2
	_count=$#
	[ "$MENU_PICK" -ge 1 ] || MENU_PICK=1
	[ "$MENU_PICK" -le "$_count" ] || MENU_PICK="$_count"
	if [ "$COLOR" = 1 ]; then
		MENU_REV="$(printf '\033[7m')"
		MENU_OFF="$(printf '\033[0m')"
	else
		MENU_REV=""
		MENU_OFF=""
	fi

	if ! menu_enter; then
		printf '  %s>%s %s\n' "$BRIGHT" "$OFF" "$MENU_PROMPT" >/dev/tty
		_i=1
		for _item in "$@"; do
			printf '    [%s] %s\n' "$_i" "$_item" >/dev/tty
			_i=$((_i + 1))
		done
		printf '  %s>%s Choose 1-%s: ' "$BRIGHT" "$OFF" "$_count" >/dev/tty
		IFS= read -r _answer </dev/tty || return 1
		case "$_answer" in
		'') ;;
		*[!0-9]*) return 1 ;;
		*)
			[ "$_answer" -ge 1 ] && [ "$_answer" -le "$_count" ] || return 1
			MENU_PICK="$_answer"
			;;
		esac
	else
		while :; do
			menu_draw "$MENU_PROMPT" "$@"
			_key="$(read_key)" || { menu_stop; return 1; }
			case "$_key" in
			10 | 13 | 32) break ;;
			113 | 81) menu_stop; return 1 ;;
			104 | 107) [ "$MENU_PICK" -gt 1 ] && MENU_PICK=$((MENU_PICK - 1)) ;;
			106 | 108) [ "$MENU_PICK" -lt "$_count" ] && MENU_PICK=$((MENU_PICK + 1)) ;;
			27)
				_code="$(read_key_timed)"
				if [ "$_code" = 91 ] || [ "$_code" = 79 ]; then
					_code="$(read_key_timed)"
					case "$_code" in
					65 | 68) [ "$MENU_PICK" -gt 1 ] && MENU_PICK=$((MENU_PICK - 1)) ;;
					66 | 67) [ "$MENU_PICK" -lt "$_count" ] && MENU_PICK=$((MENU_PICK + 1)) ;;
					esac
				else
					menu_stop
					return 1
				fi
				;;
			esac
			if [ "$_key" -ge 49 ] && [ "$_key" -le 57 ]; then
				_digit=$((_key - 48))
				[ "$_digit" -le "$_count" ] && MENU_PICK="$_digit"
			fi
			menu_rewind "$MENU_HEIGHT"
		done
		_i=1
		for _item in "$@"; do
			[ "$_i" = "$MENU_PICK" ] && MENU_ANSWER="$_item"
			_i=$((_i + 1))
		done
		menu_done
		menu_leave
	fi

	_i=1
	for _item in "$@"; do
		[ "$_i" = "$MENU_PICK" ] && printf '%s' "$_item"
		_i=$((_i + 1))
	done
}

# --------------------------------------------------------------- agents ----
#
# id|name|project|global|detect
# global: - | home:PATH | env:VAR:home:FALLBACK | xdg:PATH | openclaw | reasonix
# detect: ;-separated home:|env:|xdg:|cwd:|abs:|app:|appdata:|flatpak:|pkg:  or -

agent_table() {
	cat <<'EOF'
aider-desk|AiderDesk|.aider-desk/skills|home:.aider-desk/skills|home:.aider-desk
amp|Amp|.agents/skills|xdg:agents/skills|xdg:amp
antigravity|Antigravity|.agents/skills|home:.gemini/config/skills|home:.gemini/antigravity
antigravity-cli|Antigravity CLI|.agents/skills|home:.gemini/config/skills|home:.gemini/antigravity-cli
astrbot|AstrBot|data/skills|home:.astrbot/data/skills|home:.astrbot;cwd:data/skills
autohand-code|Autohand Code CLI|.autohand/skills|env:AUTOHAND_HOME:home:.autohand/skills|env:AUTOHAND_HOME;home:.autohand
augment|Augment|.augment/skills|home:.augment/skills|home:.augment
bob|IBM Bob|.bob/skills|home:.bob/skills|home:.bob
claude-code|Claude Code|.claude/skills|env:CLAUDE_CONFIG_DIR:home:.claude/skills|env:CLAUDE_CONFIG_DIR;home:.claude
openclaw|OpenClaw|skills|openclaw|home:.openclaw;home:.clawdbot;home:.moltbot
cline|Cline|.agents/skills|home:.agents/skills|home:.cline
codearts-agent|CodeArts Agent|.codeartsdoer/skills|home:.codeartsdoer/skills|home:.codeartsdoer
codebuddy|CodeBuddy|.codebuddy/skills|home:.codebuddy/skills|home:.codebuddy;cwd:.codebuddy
codemaker|Codemaker|.codemaker/skills|home:.codemaker/skills|home:.codemaker
codestudio|Code Studio|.codestudio/skills|home:.codestudio/skills|home:.codestudio
codex|Codex|.agents/skills|home:.agents/skills|env:CODEX_HOME;home:.codex;abs:/etc/codex
command-code|Command Code|.commandcode/skills|home:.commandcode/skills|home:.commandcode
continue|Continue|.continue/skills|home:.continue/skills|home:.continue;cwd:.continue
cortex|Cortex Code|.cortex/skills|home:.snowflake/cortex/skills|home:.snowflake/cortex
crush|Crush|.crush/skills|xdg:crush/skills|xdg:crush
cursor|Cursor|.agents/skills|home:.cursor/skills|home:.cursor
deepagents|Deep Agents|.agents/skills|home:.deepagents/agent/skills|home:.deepagents
devin|Devin for Terminal|.devin/skills|xdg:devin/skills|xdg:devin
dexto|Dexto|.agents/skills|home:.agents/skills|home:.dexto
droid|Droid|.agents/skills|home:.factory/skills|home:.factory
eve|Eve|agent/skills|-|pkg:eve
firebender|Firebender|.agents/skills|home:.firebender/skills|home:.firebender
forgecode|ForgeCode|.forge/skills|home:.forge/skills|home:.forge
fx|fx|.agents/skills|home:.agents/skills|home:.fx
gemini-cli|Gemini CLI|.agents/skills|home:.gemini/skills|home:.gemini
github-copilot|GitHub Copilot|.agents/skills|home:.copilot/skills|home:.copilot
goose|Goose|.goose/skills|xdg:goose/skills|xdg:goose
grok|Grok Build|.grok/skills|env:GROK_HOME:home:.grok/skills|env:GROK_HOME;home:.grok
hermes-agent|Hermes Agent|.hermes/skills|env:HERMES_HOME:home:.hermes/skills|env:HERMES_HOME;home:.hermes
inference-sh|inference.sh|.inferencesh/skills|home:.inferencesh/skills|home:.inferencesh
jazz|Jazz|.jazz/skills|home:.jazz/skills|home:.jazz;cwd:.jazz
junie|Junie|.junie/skills|home:.junie/skills|home:.junie
iflow-cli|iFlow CLI|.iflow/skills|home:.iflow/skills|home:.iflow
kilo|Kilo Code|.agents/skills|home:.kilo/skills|home:.kilo;home:.kilocode
kimchi|Kimchi|.kimchi/skills|xdg:kimchi/harness/skills|xdg:kimchi
kimi-code-cli|Kimi Code CLI|.agents/skills|home:.agents/skills|home:.kimi-code;home:.kimi
kiro-cli|Kiro CLI|.kiro/skills|home:.kiro/skills|home:.kiro
kode|Kode|.kode/skills|home:.kode/skills|home:.kode
lingma|Lingma|.lingma/skills|home:.lingma/skills|home:.lingma
loaf|Loaf|.agents/skills|home:.agents/skills|home:.loaf
mcpjam|MCPJam|.mcpjam/skills|home:.mcpjam/skills|home:.mcpjam
minimax-code|MiniMax Code|.minimax/skills|home:.minimax/skills|home:.minimax;app:/Applications/MiniMax Code.app
mistral-vibe|Mistral Vibe|.vibe/skills|env:VIBE_HOME:home:.vibe/skills|env:VIBE_HOME;home:.vibe
moxby|Moxby|.moxby/skills|home:.moxby/skills|home:.moxby
mux|Mux|.mux/skills|home:.mux/skills|home:.mux
opencode|OpenCode|.agents/skills|xdg:opencode/skills|xdg:opencode
openhands|OpenHands|.openhands/skills|home:.openhands/skills|home:.openhands
ona|Ona|.ona/skills|home:.ona/skills|home:.ona
pi|Pi|.agents/skills|home:.agents/skills|home:.pi/agent
posit-assistant|Posit Assistant|.posit/assistant/skills|home:.posit/assistant/skills|home:.posit/assistant;home:.positai
qoder|Qoder|.qoder/skills|home:.qoder/skills|home:.qoder
qoder-cn|Qoder CN|.qoder/skills|home:.qoder-cn/skills|home:.qoder-cn
qwen-code|Qwen Code|.qwen/skills|home:.qwen/skills|home:.qwen
replit|Replit|.agents/skills|xdg:agents/skills|cwd:.replit
reasonix|Reasonix|.reasonix/skills|reasonix|env:REASONIX_HOME;home:.reasonix
rovodev|Rovo Dev|.rovodev/skills|home:.rovodev/skills|home:.rovodev
roo|Roo Code|.roo/skills|home:.roo/skills|home:.roo
sarvam-code|Sarvam Code|.agents/skills|home:.agents/skills|env:SARVAM_HOME;home:.sarvam
tabnine-cli|Tabnine CLI|.tabnine/agent/skills|home:.tabnine/agent/skills|home:.tabnine
terramind|Terramind|.terramind/skills|home:.terramind/skills|home:.terramind
tinycloud|Tinycloud|.tinycloud/skills|home:.tinycloud/skills|home:.tinycloud
trae|Trae|.trae/skills|home:.trae/skills|home:.trae
trae-cn|Trae CN|.trae/skills|home:.trae-cn/skills|home:.trae-cn
warp|Warp|.agents/skills|home:.agents/skills|home:.warp
windsurf|Windsurf|.windsurf/skills|home:.codeium/windsurf/skills|home:.codeium/windsurf
zed|Zed|.agents/skills|home:.agents/skills|xdg:zed;appdata:Zed;flatpak:zed
zcode|ZCode|.zcode/skills|home:.zcode/skills|home:.zcode;app:/Applications/ZCode.app
zencoder|Zencoder|.zencoder/skills|home:.zencoder/skills|home:.zencoder
zenflow|Zenflow|.zencoder/skills|home:.zencoder/skills|home:.zencoder
neovate|Neovate|.neovate/skills|home:.neovate/skills|home:.neovate
pochi|Pochi|.pochi/skills|home:.pochi/skills|home:.pochi
promptscript|PromptScript|.agents/skills|-|cwd:.promptscript;cwd:promptscript.yaml
adal|AdaL|.adal/skills|home:.adal/skills|home:.adal
universal|Universal|.agents/skills|xdg:agents/skills|-
EOF
}

agent_row() {
	agent_table | while IFS='|' read -r id name project global detect; do
		if [ "$id" = "$1" ]; then
			printf '%s|%s|%s|%s|%s\n' "$id" "$name" "$project" "$global" "$detect"
			break
		fi
	done
}

agent_field() {
	printf '%s\n' "$1" | cut -d'|' -f"$2"
}

xdg_config() {
	if [ -n "${XDG_CONFIG_HOME:-}" ]; then
		printf '%s' "$XDG_CONFIG_HOME"
	else
		printf '%s' "$HOME/.config"
	fi
}

env_path() {
	case "$1" in
	AUTOHAND_HOME) printf '%s' "${AUTOHAND_HOME:-}" ;;
	CLAUDE_CONFIG_DIR) printf '%s' "${CLAUDE_CONFIG_DIR:-}" ;;
	CODEX_HOME) printf '%s' "${CODEX_HOME:-}" ;;
	GROK_HOME) printf '%s' "${GROK_HOME:-}" ;;
	HERMES_HOME) printf '%s' "${HERMES_HOME:-}" ;;
	VIBE_HOME) printf '%s' "${VIBE_HOME:-}" ;;
	SARVAM_HOME) printf '%s' "${SARVAM_HOME:-}" ;;
	REASONIX_HOME) printf '%s' "${REASONIX_HOME:-}" ;;
	*) return 1 ;;
	esac
}

marker_exists() {
	case "$1" in
	home:*) [ -e "$HOME/${1#home:}" ] ;;
	env:*)
		_val="$(env_path "${1#env:}")" || return 1
		[ -n "$_val" ] && [ -e "$_val" ]
		;;
	xdg:*) [ -e "$(xdg_config)/${1#xdg:}" ] ;;
	cwd:*) [ -e "$TARGET/${1#cwd:}" ] ;;
	abs:*) [ -e "${1#abs:}" ] ;;
	app:*) [ -e "${1#app:}" ] ;;
	appdata:*)
		[ -n "${APPDATA:-}" ] && [ -e "$APPDATA/${1#appdata:}" ]
		;;
	flatpak:*)
		[ -n "${FLATPAK_XDG_CONFIG_HOME:-}" ] && [ -e "$FLATPAK_XDG_CONFIG_HOME/${1#flatpak:}" ]
		;;
	pkg:*)
		_name="${1#pkg:}"
		[ -d "$TARGET/agent" ] && [ -f "$TARGET/package.json" ] &&
			grep -q "\"$_name\"" "$TARGET/package.json"
		;;
	*) return 1 ;;
	esac
}

project_marker() {
	case "$1" in
	.agents/skills | skills) return 1 ;;
	esac
	_parent="${1%/*}"
	case "$_parent" in
	.*) [ -e "$TARGET/$_parent" ] ;;
	*) return 1 ;;
	esac
}

agent_detected() {
	_row="$(agent_row "$1")"
	[ -n "$_row" ] || return 1
	_project="$(agent_field "$_row" 3)"
	_detect="$(agent_field "$_row" 5)"
	[ "$_detect" = "-" ] && return 1
	_old="$IFS"
	IFS=';'
	for _mark in $_detect; do
		[ -n "$_mark" ] || continue
		if marker_exists "$_mark"; then
			IFS="$_old"
			return 0
		fi
	done
	IFS="$_old"
	project_marker "$_project"
}

expand_global() {
	case "$1" in
	-) return 1 ;;
	home:*) printf '%s\n' "$HOME/${1#home:}" ;;
	env:*)
		_rest="${1#env:}"
		_var="${_rest%%:*}"
		_fallback="${_rest#*:}"
		_val="$(env_path "$_var")" || _val=""
		if [ -n "$_val" ]; then
			printf '%s\n' "$_val/skills"
		else
			expand_global "$_fallback"
		fi
		;;
	xdg:*) printf '%s\n' "$(xdg_config)/${1#xdg:}" ;;
	openclaw)
		if [ -d "$HOME/.openclaw" ]; then
			printf '%s\n' "$HOME/.openclaw/skills"
		elif [ -d "$HOME/.clawdbot" ]; then
			printf '%s\n' "$HOME/.clawdbot/skills"
		elif [ -d "$HOME/.moltbot" ]; then
			printf '%s\n' "$HOME/.moltbot/skills"
		else
			printf '%s\n' "$HOME/.openclaw/skills"
		fi
		;;
	reasonix)
		if [ -n "${REASONIX_HOME:-}" ]; then
			printf '%s\n' "$REASONIX_HOME/skills"
		else
			printf '%s\n' "$HOME/.reasonix/skills"
		fi
		;;
	*) die "bad agent path: $1" ;;
	esac
}

known_agent() {
	[ -n "$(agent_row "$1")" ]
}

print_agents() {
	agent_table | while IFS='|' read -r id name project global detect; do
		printf '%s\t%s\t%s\n' "$id" "$project" "$global"
	done
}

# --------------------------------------------------------------- source ----

is_root() {
	[ -f "$1/skills/sw-start/SKILL.md" ] && [ -f "$1/skills/sw-publish/SKILL.md" ]
}

find_root_from() {
	_dir="$1"
	_i=0
	while [ "$_i" -lt 8 ]; do
		if is_root "$_dir"; then
			printf '%s\n' "$_dir"
			return 0
		fi
		_parent="$(dirname "$_dir")"
		[ "$_parent" = "$_dir" ] && break
		_dir="$_parent"
		_i=$((_i + 1))
	done
	return 1
}

fetch_archive() {
	have tar || die "tar is required to install Specwright" "Install tar, then run this installer again."
	have curl || have wget || die "curl or wget is required" "Install curl, then run this installer again."
	_url="${SPECWRIGHT_URL:-https://github.com/$REPO/archive/refs/heads/$REF.tar.gz}"
	step "Downloading $REPO@$REF"
	mkdir -p "$TMP_DIR/unpack"
	if have curl; then
		curl -fsSL --retry 2 --connect-timeout 20 -o "$TMP_DIR/src.tar.gz" "$_url" ||
			die "download failed" "$_url"
	else
		wget -q -O "$TMP_DIR/src.tar.gz" "$_url" || die "download failed" "$_url"
	fi
	done_ "Downloaded $REPO@$REF"
	lead "Unpacking the source archive"
	tar -xzf "$TMP_DIR/src.tar.gz" -C "$TMP_DIR/unpack" || die "could not unpack the source archive"
	_hit="$(find "$TMP_DIR/unpack" -type f -path '*/skills/sw-start/SKILL.md' | head -n 1)"
	[ -n "$_hit" ] || die "the archive has no skills/sw-start/SKILL.md"
	_root="$(dirname "$(dirname "$(dirname "$_hit")")")"
	is_root "$_root" || die "the archive is not a Specwright checkout"
	done_ "Unpacked $REPO@$REF"
	printf '%s\n' "$_root" >"$TMP_DIR/skill-root"
}

require_skills() {
	for _skill in $SKILLS; do
		[ -f "$1/skills/$_skill/SKILL.md" ] || die "missing skill: $_skill" "$1/skills/$_skill"
	done
}

# --------------------------------------------------------------- install ----

detect_platform() {
	_kernel="$(uname -s 2>/dev/null || echo unknown)"
	case "$_kernel" in
	Darwin) OS="darwin" ;;
	Linux) OS="linux" ;;
	*)
		die "unsupported system: $_kernel" \
			"This installer runs on macOS and Linux. On Windows, run install.ps1 in PowerShell."
		;;
	esac
	_try="$(stat -f %d / 2>/dev/null || true)"
	case "$_try" in
	'' | *[!0-9]*) STAT_BSD=0 ;;
	*) STAT_BSD=1 ;;
	esac
}

resolve_target() {
	if [ -z "$TARGET" ]; then
		TARGET="$PWD"
	fi
	case "$TARGET" in
	"~"*) TARGET="$HOME${TARGET#\~}" ;;
	esac
	[ -d "$TARGET" ] || die "project directory does not exist" "$TARGET"
	TARGET="$(cd "$TARGET" && pwd)"
}

collect_detected() {
	: >"$TMP_DIR/detected"
	agent_table | while IFS='|' read -r id name project global detect; do
		if agent_detected "$id"; then
			printf '%s\n' "$id"
		fi
	done >"$TMP_DIR/detected"
}

append_agent() {
	known_agent "$1" || die "unknown agent: $1" "run install.sh --list-agents"
	if [ -s "$TMP_DIR/selected" ] && grep -qx "$1" "$TMP_DIR/selected"; then
		return 0
	fi
	printf '%s\n' "$1" >>"$TMP_DIR/selected"
}

split_agents() {
	_old="$IFS"
	IFS=', '
	set -f
	for _tok in $1; do
		[ -n "$_tok" ] || continue
		append_agent "$_tok"
	done
	set +f
	IFS="$_old"
}

load_agent_args() {
	: >"$TMP_DIR/selected"
	[ -n "$AGENT_ARGS" ] || return 0
	for _part in $AGENT_ARGS; do
		split_agents "$_part"
	done
}

choose_from_detected() {
	_n=0
	while IFS= read -r _id; do
		_n=$((_n + 1))
		row "    ${_n}  ${_id}"
	done <"$TMP_DIR/detected"
	row ""
	_answer="$(ask "Numbers or ids (* for all)" "")"
	[ -n "$_answer" ] || return 1
	if [ "$_answer" = "*" ] || [ "$_answer" = "all" ]; then
		cp "$TMP_DIR/detected" "$TMP_DIR/selected"
		return 0
	fi
	: >"$TMP_DIR/selected"
	_old="$IFS"
	IFS=', '
	set -f
	for _tok in $_answer; do
		[ -n "$_tok" ] || continue
		case "$_tok" in
		*[!0-9]*)
			append_agent "$_tok"
			;;
		*)
			_id="$(sed -n "${_tok}p" "$TMP_DIR/detected")"
			[ -n "$_id" ] || die "no detected agent numbered $_tok"
			append_agent "$_id"
			;;
		esac
	done
	set +f
	IFS="$_old"
	[ -s "$TMP_DIR/selected" ]
}

show_agent_ids() {
	_line="  "
	while IFS='|' read -r id name project global detect; do
		_next="$_line$id "
		if [ "$(vislen "$_next")" -gt $((INNER - 2)) ]; then
			row "$_line"
			_line="  $id "
		else
			_line="$_next"
		fi
	done <<EOF
$(agent_table)
EOF
	[ -z "$_line" ] || row "$_line"
}

enter_ids() {
	while :; do
		note "Comma-separated ids such as cursor, claude-code. Enter list to see every id."
		_answer="$(ask "Agent ids" "")"
		[ -n "$_answer" ] || return 1
		if [ "$_answer" = "list" ]; then
			show_agent_ids
			continue
		fi
		: >"$TMP_DIR/selected"
		split_agents "$_answer"
		[ -s "$TMP_DIR/selected" ] && return 0
		note "No ids in that line."
	done
}

options_screen() {
	section "Make it yours"
	row "  All seven skills install together. Pick a scope and the agents."
	row "  ${MID}Project: $TARGET${OFF}"
	row ""

	if [ "$SCOPE_SET" = 1 ]; then
		note "Scope: $SCOPE"
	else
		_default=1
		[ "$SCOPE" = "project" ] && _default=2
		menu_select "Where should the skills go?" "$_default" "All projects" "This project" >/dev/null || {
			note "Setup canceled. Nothing was changed."
			exit 0
		}
		if [ "$MENU_PICK" = 2 ]; then SCOPE="project"; else SCOPE="global"; fi
	fi

	if [ -s "$TMP_DIR/selected" ]; then
		note "Agents: $(tr '\n' ' ' <"$TMP_DIR/selected")"
	else
		_count="$(wc -l <"$TMP_DIR/detected" | tr -d ' ')"
		if [ "$_count" -gt 0 ]; then
			menu_select "Which agents?" 1 "All detected ($_count)" "Choose…" "Enter ids…" >/dev/null || {
				note "Setup canceled. Nothing was changed."
				exit 0
			}
			case "$MENU_PICK" in
			1) cp "$TMP_DIR/detected" "$TMP_DIR/selected" ;;
			2) choose_from_detected || { note "Setup canceled. Nothing was changed."; exit 0; } ;;
			3) enter_ids || { note "Setup canceled. Nothing was changed."; exit 0; } ;;
			esac
		else
			menu_select "No agents detected. Install where?" 1 "Universal" "Enter ids…" >/dev/null || {
				note "Setup canceled. Nothing was changed."
				exit 0
			}
			case "$MENU_PICK" in
			1) printf '%s\n' universal >"$TMP_DIR/selected" ;;
			2) enter_ids || { note "Setup canceled. Nothing was changed."; exit 0; } ;;
			esac
		fi
	fi

	note "Skills: $SKILLS"
	menu_select "Ready to install?" 1 "Install" "Cancel" >/dev/null || {
		note "Setup canceled. Nothing was changed."
		exit 0
	}
	if [ "$MENU_PICK" = 2 ]; then
		note "Setup canceled. Nothing was changed."
		exit 0
	fi
}

apply_defaults() {
	section "Use your selected settings"
	note "Running without prompts. Use --help to see setup options."
	if [ ! -s "$TMP_DIR/selected" ]; then
		if [ -s "$TMP_DIR/detected" ]; then
			cp "$TMP_DIR/detected" "$TMP_DIR/selected"
			note "Agents: every detected agent"
		else
			printf '%s\n' universal >"$TMP_DIR/selected"
			note "No agents detected; installing for universal"
		fi
	else
		note "Agents: $(tr '\n' ' ' <"$TMP_DIR/selected")"
	fi
	note "Scope: $SCOPE"
}

resolve_dests() {
	: >"$TMP_DIR/dests.raw"
	while IFS= read -r _id; do
		_row="$(agent_row "$_id")"
		_project="$(agent_field "$_row" 3)"
		_global="$(agent_field "$_row" 4)"
		if [ "$SCOPE" = "global" ]; then
			if ! _dest="$(expand_global "$_global")"; then
				note "$_id is project-only; skipped"
				continue
			fi
		else
			_dest="$TARGET/$_project"
		fi
		_dest="${_dest%/}"
		printf '%s\n' "$_dest" >>"$TMP_DIR/dests.raw"
	done <"$TMP_DIR/selected"
	sort -u "$TMP_DIR/dests.raw" >"$TMP_DIR/dests"
	[ -s "$TMP_DIR/dests" ] || die "no install location for the selected agents" \
		"Project-only agents cannot take a global install." \
		"Pick another agent, or rerun with --project."
}

is_ours() {
	# is_ours <skill> <path>; true for a Specwright skill folder or a link to one
	_skill="$1"
	_path="$2"
	if [ -L "$_path" ] && [ ! -e "$_path" ]; then
		return 0
	fi
	_dir="$_path"
	if [ -L "$_path" ]; then
		_dir="$(cd "$_path" && pwd -P)" || return 1
	fi
	[ -f "$_dir/SKILL.md" ] || return 1
	grep -q "^name: ${_skill}$" "$_dir/SKILL.md"
}

replace_existing() {
	: >"$TMP_DIR/old"
	while IFS= read -r _dest; do
		for _skill in $SKILLS; do
			_path="$_dest/$_skill"
			[ -e "$_path" ] || [ -L "$_path" ] || continue
			if ! is_ours "$_skill" "$_path"; then
				die "refusing to replace a folder that is not a Specwright skill" \
					"$_path" \
					"That folder has no matching name: $_skill in SKILL.md."
			fi
			if [ -d "$_path" ] && [ ! -L "$_path" ]; then
				_real="$(cd "$_path" && pwd -P)"
				case "$_real" in
				"$SKILL_ROOT"/skills/"$_skill")
					die "refusing to delete the skill source" "$_path"
					;;
				esac
			fi
			printf '%s\n' "$_path" >>"$TMP_DIR/old"
		done
	done <"$TMP_DIR/dests"
	[ -s "$TMP_DIR/old" ] || return 0
	_n="$(wc -l <"$TMP_DIR/old" | tr -d ' ')"
	note "Replacing $_n existing Specwright skill folder(s)"
	while IFS= read -r _path; do
		rm -rf "$_path"
	done <"$TMP_DIR/old"
	done_ "Removed the previous install"
}

devof() {
	if [ "$STAT_BSD" = 1 ]; then
		stat -f %d "$1"
	else
		stat -c %d "$1" 2>/dev/null
	fi
}

same_device() {
	_a="$(devof "$1" 2>/dev/null || true)"
	_b="$(devof "$2" 2>/dev/null || true)"
	[ -n "$_a" ] && [ "$_a" = "$_b" ]
}

relpath() {
	_from="$1"
	_to="$2"
	_prefix=""
	while :; do
		case "$_to/" in
		"$_from"/*) break ;;
		esac
		if [ "$_from" = "/" ]; then
			break
		fi
		_from="$(dirname "$_from")"
		_prefix="../$_prefix"
	done
	_rest="${_to#"$_from"}"
	_rest="${_rest#/}"
	printf '%s%s' "$_prefix" "$_rest"
}

copy_skills() {
	mkdir -p "$1"
	for _skill in $SKILLS; do
		cp -R "$SKILL_ROOT/skills/$_skill" "$1/$_skill"
	done
}

link_skills() {
	_dest="$1"
	_canon="$2"
	mkdir -p "$_dest"
	for _skill in $SKILLS; do
		_rel="$(relpath "$_dest" "$_canon/$_skill")"
		ln -s "$_rel" "$_dest/$_skill" || return 1
	done
}

clear_new_links() {
	for _skill in $SKILLS; do
		if [ -L "$1/$_skill" ]; then
			rm -f "$1/$_skill"
		fi
	done
}

pick_canonical() {
	_canon=""
	while IFS= read -r _dest; do
		case "$_dest" in
		*/.agents/skills) _canon="$_dest"; break ;;
		esac
	done <"$TMP_DIR/dests"
	if [ -z "$_canon" ]; then
		_canon="$(head -n 1 "$TMP_DIR/dests")"
	fi
	printf '%s\n' "$_canon"
}

install_skills() {
	_canon="$(pick_canonical)"
	step "Installing into $_canon"
	copy_skills "$_canon"
	done_ "Copied 7 skills into $_canon"
	while IFS= read -r _dest; do
		[ "$_dest" = "$_canon" ] && continue
		mkdir -p "$_dest"
		if same_device "$_canon" "$_dest" && link_skills "$_dest" "$_canon"; then
			done_ "Linked 7 skills into $_dest"
		else
			clear_new_links "$_dest"
			copy_skills "$_dest"
			done_ "Copied 7 skills into $_dest"
		fi
	done <"$TMP_DIR/dests"
}

summary() {
	_places="$(wc -l <"$TMP_DIR/dests" | tr -d ' ')"
	hline '├' '┤'
	row ""
	row "  ${BRIGHT}✓${OFF} ${BOLD}Specwright is installed.${OFF}"
	row ""
	row "  ${MID}Scope${OFF}    $SCOPE"
	row "  ${MID}Skills${OFF}   7 skills in $_places location(s)"
	row ""
	while IFS= read -r _dest; do
		row "  ${MID}·${OFF} $_dest"
	done <"$TMP_DIR/dests"
	row ""
	row "  ${BOLD}Your next step${OFF}"
	row "  Open the project in your agent and say what you want:"
	row "    start a spec for the refunds flow"
	row ""
	note "To update, run this installer again."
}

# -------------------------------------------------------------------- main --

main() {
	if [ "$LIST_ONLY" = 1 ]; then
		print_agents
		exit 0
	fi
	detect_platform
	resolve_target
	if [ -f "$0" ]; then
		SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
	else
		SCRIPT_DIR=""
	fi
	TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/specwright-install.XXXXXX")"
	screen_open
	collect_detected
	load_agent_args
	if [ "$INTERACTIVE" = 1 ]; then
		options_screen
	else
		apply_defaults
	fi

	section "Install Specwright"
	SKILL_ROOT=""
	if [ -n "${SPECWRIGHT_ROOT:-}" ]; then
		is_root "$SPECWRIGHT_ROOT" || die "SPECWRIGHT_ROOT is not a Specwright checkout" "$SPECWRIGHT_ROOT"
		SKILL_ROOT="$SPECWRIGHT_ROOT"
	elif [ -n "$SCRIPT_DIR" ]; then
		SKILL_ROOT="$(find_root_from "$SCRIPT_DIR" || true)"
	fi
	if [ -n "$SKILL_ROOT" ]; then
		note "Using the checkout at $SKILL_ROOT"
	else
		note "No local checkout; downloading $REPO@$REF"
		fetch_archive
		SKILL_ROOT="$(cat "$TMP_DIR/skill-root")"
	fi
	require_skills "$SKILL_ROOT"
	resolve_dests
	replace_existing
	install_skills
	summary
	screen_close
}

main "$@"
