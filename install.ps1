# Specwright installer for Windows: all seven skills, into the agents you choose.
#
#   irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1 | iex
#
# With arguments (PowerShell cannot pass them through a pipe):
#
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Project
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Agent cursor,claude-code -Yes
#
# No Node and no Python. Agent directories match `npx skills add`
# (vercel-labs/skills agents.ts). Every public skill is installed; there is
# no skill picker. Windows always copies. The agent table matches install.sh.
[CmdletBinding()]
param(
	[string[]] $Agent,
	[switch] $Global,
	[switch] $Project,
	[string] $Target = $env:SPECWRIGHT_TARGET,
	[switch] $Yes,
	[switch] $ListAgents,
	[switch] $Help
)

Set-StrictMode -Version 1.0
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Repo = if ($env:SPECWRIGHT_REPO) { $env:SPECWRIGHT_REPO } else { 'jonaskahn/specwright' }
$Ref = if ($env:SPECWRIGHT_REF) { $env:SPECWRIGHT_REF } else { 'main' }
$Skills = @('sw-start', 'sw-shape', 'sw-ingest', 'sw-spec', 'sw-plan', 'sw-review', 'sw-publish', 'sw-view')
if ($env:SPECWRIGHT_INSTALL_YES -eq '1') { $Yes = $true }

$script:Inner = 76
$script:Framed = $false
$script:FirstSection = $true
$script:Terminal = $false
try { $script:Terminal = -not [Console]::IsOutputRedirected } catch { }
$script:Color = $false
try { $script:Color = [bool]$Host.UI.SupportsVirtualTerminal } catch { $script:Color = $false }
if ($env:NO_COLOR) { $script:Color = $false }
if (-not $script:Terminal) { $script:Color = $false }
$script:Esc = [char]27
$script:Scope = 'global'
$script:Selected = @()
$script:Detected = @()
$script:Destinations = @()
$script:SkillRoot = ''
$script:Target = ''
$script:DownloadDir = ''

# Glyphs as code points so `irm | iex` cannot mangle a non-UTF8 decode.
$script:Block = [string][char]0x2588
$script:Rule = [string][char]0x2550
$script:Bar = [string][char]0x2551
$script:CornerTL = [string][char]0x2554
$script:CornerTR = [string][char]0x2557
$script:CornerBL = [string][char]0x255A
$script:CornerBR = [string][char]0x255D
$script:Side = [string][char]0x2502
$script:Bullet = [string][char]0x25B6
$script:Check = [string][char]0x2713
$script:Dot = [string][char]0x00B7
$script:Ellipsis = [string][char]0x2026
$script:Left = [string][char]0x2190
$script:Right = [string][char]0x2192

$script:Logo = @(
	'#######7######7 #######7 ######7',
	'##4====D##4==##7##4====D##4====D',
	'#######7######4D#####7  ##|     ',
	'A====##|##4===D ##4==D  ##|     ',
	'#######|##|     #######7A######7',
	'A======DA=D     A======D A=====D'
)
foreach ($pair in @(
		@('#', $script:Block), @('=', $script:Rule), @('|', $script:Bar),
		@('7', $script:CornerTR), @('4', $script:CornerTL),
		@('D', $script:CornerBR), @('A', $script:CornerBL)
	)) {
	$script:Logo = $script:Logo | ForEach-Object { $_.Replace($pair[0], $pair[1]) }
}

# Two rows, one third the height of the six-row SPEC letters.
# W is three peaks on a base. R kicks to the lower right.
# H is open at the bottom, with the crossbar in the middle, so it does not read as U.
$script:Wright = @(
	'b b b bub b dbu b b ubu',
	'bdbdb bud b udb bub  b '
)
$wrightMap = @{
	'b' = [string][char]0x2588
	'u' = [string][char]0x2580
	'd' = [string][char]0x2584
}
foreach ($token in @('b', 'u', 'd')) {
	$glyph = $wrightMap[$token]
	$script:Wright = $script:Wright | ForEach-Object { $_.Replace($token, $glyph) }
}

function Set-ThemeColors {
	# Phosphor green, the terminal kind. Dark screens get the bright tint; light
	# screens get a deeper one. SPECWRIGHT_THEME=light|dark overrides.
	$mode = 'either'
	if ($env:SPECWRIGHT_THEME) {
		$mode = $env:SPECWRIGHT_THEME
	} else {
		try {
			$personal = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' -ErrorAction Stop
			if ($personal.AppsUseLightTheme -eq 0) { $mode = 'dark' } else { $mode = 'light' }
		} catch {
			if ($env:OS -ne 'Windows_NT') {
				try {
					$style = & defaults read -g AppleInterfaceStyle 2>$null
					if ($style -match 'Dark') { $mode = 'dark' } else { $mode = 'light' }
				} catch { }
			}
		}
	}
	switch ($mode) {
		'dark' {
			$script:RgbBright = '57;255;70'
			$script:RgbLight = '40;220;64'
			$script:RgbMid = '32;190;56'
			$script:RgbNote = '150;255;160'
			$script:RgbSpec = '255;112;122'
			$script:RgbDanger = '184;140;128'
		}
		'light' {
			$script:RgbBright = '0;136;48'
			$script:RgbLight = '0;124;44'
			$script:RgbMid = '0;112;40'
			$script:RgbNote = '0;148;52'
			$script:RgbSpec = '204;42;74'
			$script:RgbDanger = '148;96;84'
		}
		default {
			$script:RgbBright = '0;160;56'
			$script:RgbLight = '0;148;52'
			$script:RgbMid = '0;136;48'
			$script:RgbNote = '0;172;60'
			$script:RgbSpec = '220;64;88'
			$script:RgbDanger = '160;112;100'
		}
	}
}
Set-ThemeColors

function Paint([string] $Text, [string] $Tone) {
	if (-not $script:Color) { return $Text }
	$rgb = switch ($Tone) {
		'bright' { $script:RgbBright }
		'rose' { $script:RgbLight }
		'mid' { $script:RgbMid }
		'dim' { $script:RgbMid }
		'note' { $script:RgbNote }
		'spec' { $script:RgbSpec }
		default { '' }
	}
	if (-not $rgb) {
		if ($Tone -eq 'bold') { return "$($script:Esc)[1m$Text$($script:Esc)[0m" }
		return $Text
	}
	return "$($script:Esc)[38;2;${rgb}m$Text$($script:Esc)[0m"
}

function Get-Visible([string] $Text) {
	return ($Text -replace "$($script:Esc)\[[0-9;]*m", '')
}

function Clip-Text([string] $Text) {
	$out = ''
	$vis = 0
	$i = 0
	while ($i -lt $Text.Length -and $vis -lt ($script:Inner - 1)) {
		if ($Text[$i] -eq $script:Esc) {
			$j = $Text.IndexOf('m', $i)
			if ($j -lt 0) { break }
			$out += $Text.Substring($i, $j - $i + 1)
			$i = $j + 1
			continue
		}
		$out += $Text[$i]
		$vis++
		$i++
	}
	return $out + $script:Ellipsis
}

function Format-Row([string] $Text) {
	if (-not $script:Framed) { return $Text }
	$visible = (Get-Visible $Text).Length
	if ($visible -gt $script:Inner) {
		$Text = Clip-Text $Text
		$visible = (Get-Visible $Text).Length
	}
	$pad = [Math]::Max(0, $script:Inner - $visible)
	return (Paint $script:Side 'bright') + $Text + (' ' * $pad) + (Paint $script:Side 'bright')
}

function Write-Row([string] $Text) { Write-Host (Format-Row $Text) }
function Write-DangerRow([string] $Text) {
	$visible = (Get-Visible $Text).Length
	if ($visible -gt $script:Inner) { $Text = Clip-Text $Text; $visible = (Get-Visible $Text).Length }
	$pad = [Math]::Max(0, $script:Inner - $visible)
	$bar = $script:Side
	$wall = if ($script:Color) { "$($script:Esc)[38;2;$($script:RgbDanger)m$bar$($script:Esc)[0m" } else { $bar }
	Write-Host ($wall + $Text + (' ' * $pad) + $wall)
}
function Clear-Line { if ($script:Terminal) { Write-Host ("`r" + $script:Esc + "[2K") -NoNewline } }
function Write-Separator([string] $Left, [string] $Right) {
	$dash = [string][char]0x2500
	Write-Host (Paint ($Left + ($dash * $script:Inner) + $Right) 'bright')
}
function Write-Center([string] $Text, [string] $Tone) {
	$visible = (Get-Visible $Text).Length
	$left = [Math]::Max(0, [int](($script:Inner - $visible) / 2))
	Write-Row ((' ' * $left) + (Paint $Text $Tone))
}
function Write-Step([string] $Text) {
	if ($script:Terminal) {
		Write-Host (Format-Row ("  " + (Paint $script:Bullet 'bright') + " $Text")) -NoNewline
	} else {
		Write-Host "  > $Text"
	}
}
function Write-OK([string] $Text) { Clear-Line; Write-Row ("  " + (Paint $script:Check 'bright') + " $Text") }
function Write-Note([string] $Text) { Clear-Line; Write-Row ("  " + (Paint $script:Dot 'note') + " " + (Paint $Text 'note')) }
function Write-Lead([string] $Text) { Write-Row ("  " + (Paint $script:Bullet 'bright') + " $Text") }
function Write-Rule { Write-Separator ([string][char]0x251C) ([string][char]0x2524) }
function Write-Section([string] $Text) {
	if ($script:FirstSection) { $script:FirstSection = $false } else { Write-Rule }
	Write-Row ''
	Write-Row ("  " + (Paint $Text 'bold'))
	Write-Row ''
}
function Write-ScreenOpen {
	if (-not $script:Terminal) {
		Write-Host ''
		Write-Host '  SPECWRIGHT INSTALLER'
		Write-Host "  $Ref skills"
		Write-Host ''
		return
	}
	$script:Framed = $true
	Write-Separator ([string][char]0x250C) ([string][char]0x2510)
	Write-Row ''
	foreach ($line in $script:Logo) { Write-Center $line 'spec' }
	foreach ($line in $script:Wright) { Write-Center $line 'bright' }
	Write-Row ''
	Write-Center 'I N S T A L L E R' 'bright'
	Write-Row ''
	Write-Center "seven skills $($script:Dot) $Ref" 'rose'
	Write-Row ''
	Write-Separator ([string][char]0x251C) ([string][char]0x2524)
}
function Write-ScreenClose {
	if (-not $script:Framed) { return }
	$script:Framed = $false
	Write-Separator ([string][char]0x2514) ([string][char]0x2518)
}
function Fail([string] $Message, [string[]] $Detail) {
	Clear-Line
	Write-ScreenClose
	Write-Host ''
	if (-not $script:Terminal) {
		Write-Host "  ! $Message"
		foreach ($line in $Detail) { if ($line) { Write-Host "    $line" } }
		exit 1
	}
	$dash = [string][char]0x2500
	$danger = "$($script:Esc)[38;2;$($script:RgbDanger)m"
	$reset = "$($script:Esc)[0m"
	if ($script:Color) {
		Write-Host ($danger + [string][char]0x250C + ($dash * $script:Inner) + [string][char]0x2510 + $reset)
	} else {
		Write-Host ([string][char]0x250C + ($dash * $script:Inner) + [string][char]0x2510)
	}
	Write-DangerRow ''
	Write-DangerRow ("  " + $(if ($script:Color) { "$danger!$reset" } else { '!' }) + " " + (Paint $Message 'bold'))
	Write-DangerRow ''
	foreach ($line in $Detail) { if ($line) { Write-DangerRow "    $line" } }
	Write-DangerRow ''
	if ($script:Color) {
		Write-Host ($danger + [string][char]0x2514 + ($dash * $script:Inner) + [string][char]0x2518 + $reset)
	} else {
		Write-Host ([string][char]0x2514 + ($dash * $script:Inner) + [string][char]0x2518)
	}
	exit 1
}

if ($Help) {
	@"
Specwright installer

Usage: install.ps1 [options]

  -Agent <id>       install for this agent (repeatable, or comma-separated)
  -Global           install for all projects (the default)
  -Project          install into this project only
  -Target <path>    project directory (default: the current directory)
  -Yes              use the selected settings without prompting
  -ListAgents       print agent ids and skill directories, then exit
  -Help             this text

Every public skill is installed: $($Skills -join ' ').

Environment: SPECWRIGHT_REPO, SPECWRIGHT_REF, SPECWRIGHT_URL, SPECWRIGHT_ROOT,
SPECWRIGHT_TARGET, SPECWRIGHT_INSTALL_YES, NO_COLOR.
"@ | Write-Host
	exit 0
}

if ($Global -and $Project) { Fail 'choose either -Global or -Project' @() }
if ($Project) { $script:Scope = 'project' }
if ($Global) { $script:Scope = 'global' }

# --------------------------------------------------------------- agents ----
# Paths track vercel-labs/skills agents.ts. Keep this table in step with install.sh.

$AgentTable = @'
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
'@

function Get-Home {
	if ($env:USERPROFILE) { return $env:USERPROFILE }
	if ($env:HOME) { return $env:HOME }
	return [Environment]::GetFolderPath('UserProfile')
}
function Get-Xdg {
	if ($env:XDG_CONFIG_HOME) { return $env:XDG_CONFIG_HOME }
	return Join-Path (Get-Home) '.config'
}
function Join-Rel([string] $Base, [string] $Rel) {
	$path = $Base
	foreach ($part in ($Rel -split '[\\/]' | Where-Object { $_ -ne '' })) {
		$path = Join-Path $path $part
	}
	return $path
}
function Get-Agents {
	$rows = @()
	foreach ($line in ($AgentTable -split "`n")) {
		$line = $line.Trim()
		if (-not $line) { continue }
		$part = $line.Split('|')
		$rows += [pscustomobject]@{
			Id = $part[0]; Name = $part[1]; Project = $part[2]; Global = $part[3]; Detect = $part[4]
		}
	}
	return $rows
}
$script:Agents = @(Get-Agents)
function Get-Agent([string] $Id) {
	foreach ($item in $script:Agents) { if ($item.Id -eq $Id) { return $item } }
	return $null
}

function Expand-Global([string] $Spec) {
	if ($Spec -eq '-') { return $null }
	if ($Spec.StartsWith('home:')) { return Join-Rel (Get-Home) $Spec.Substring(5) }
	if ($Spec.StartsWith('xdg:')) { return Join-Rel (Get-Xdg) $Spec.Substring(4) }
	if ($Spec.StartsWith('env:')) {
		$rest = $Spec.Substring(4)
		$colon = $rest.IndexOf(':')
		$var = $rest.Substring(0, $colon)
		$fallback = $rest.Substring($colon + 1)
		$val = [Environment]::GetEnvironmentVariable($var)
		if ($val) { return (Join-Path $val 'skills') }
		return Expand-Global $fallback
	}
	if ($Spec -eq 'openclaw') {
		foreach ($name in @('.openclaw', '.clawdbot', '.moltbot')) {
			$dir = Join-Path (Get-Home) $name
			if (Test-Path $dir) { return (Join-Path $dir 'skills') }
		}
		return (Join-Path (Join-Path (Get-Home) '.openclaw') 'skills')
	}
	if ($Spec -eq 'reasonix') {
		if ($env:REASONIX_HOME) { return (Join-Path $env:REASONIX_HOME 'skills') }
		if ($env:OS -eq 'Windows_NT' -and $env:APPDATA) {
			return (Join-Path (Join-Path $env:APPDATA 'reasonix') 'skills')
		}
		return (Join-Path (Join-Path (Get-Home) '.reasonix') 'skills')
	}
	Fail "bad agent path: $Spec" @()
}

function Test-Marker([string] $Mark) {
	if ($Mark.StartsWith('home:')) { return (Test-Path (Join-Rel (Get-Home) $Mark.Substring(5))) }
	if ($Mark.StartsWith('env:')) {
		$val = [Environment]::GetEnvironmentVariable($Mark.Substring(4))
		return [bool]($val -and (Test-Path $val))
	}
	if ($Mark.StartsWith('xdg:')) { return (Test-Path (Join-Rel (Get-Xdg) $Mark.Substring(4))) }
	if ($Mark.StartsWith('cwd:')) { return (Test-Path (Join-Rel $script:Target $Mark.Substring(4))) }
	if ($Mark.StartsWith('abs:')) { return (Test-Path $Mark.Substring(4)) }
	if ($Mark.StartsWith('app:')) { return (Test-Path $Mark.Substring(4)) }
	if ($Mark.StartsWith('appdata:')) {
		if (-not $env:APPDATA) { return $false }
		return (Test-Path (Join-Path $env:APPDATA $Mark.Substring(8)))
	}
	if ($Mark.StartsWith('flatpak:')) {
		if (-not $env:FLATPAK_XDG_CONFIG_HOME) { return $false }
		return (Test-Path (Join-Path $env:FLATPAK_XDG_CONFIG_HOME $Mark.Substring(8)))
	}
	if ($Mark.StartsWith('pkg:')) {
		$name = $Mark.Substring(4)
		$pkg = Join-Path $script:Target 'package.json'
		$agentDir = Join-Path $script:Target 'agent'
		if (-not (Test-Path $agentDir) -or -not (Test-Path $pkg)) { return $false }
		return [bool](Select-String -Path $pkg -Pattern ('"' + [regex]::Escape($name) + '"') -Quiet)
	}
	return $false
}

function Test-ProjectMarker([string] $Project) {
	if ($Project -eq '.agents/skills' -or $Project -eq 'skills') { return $false }
	$parent = $Project -replace '/[^/]+$', ''
	if ($parent -eq $Project -or -not $parent.StartsWith('.')) { return $false }
	return (Test-Path (Join-Rel $script:Target $parent))
}

function Test-AgentInstalled($Item) {
	if ($Item.Detect -eq '-') { return $false }
	foreach ($mark in ($Item.Detect -split ';')) {
		if ($mark -and (Test-Marker $mark)) { return $true }
	}
	return (Test-ProjectMarker $Item.Project)
}

function Add-Agent([string] $Id) {
	$known = Get-Agent $Id
	if (-not $known) { Fail "unknown agent: $Id" @('run install.ps1 -ListAgents') }
	if ($script:Selected -notcontains $Id) { $script:Selected += $Id }
}

# --------------------------------------------------------------- source ----

function Test-Root([string] $Path) {
	return (Test-Path (Join-Rel $Path 'skills/sw-start/SKILL.md')) -and (Test-Path (Join-Rel $Path 'skills/sw-publish/SKILL.md'))
}
function Find-Root([string] $Start) {
	$dir = $Start
	for ($i = 0; $i -lt 8 -and $dir; $i++) {
		if (Test-Root $dir) { return $dir }
		$parent = Split-Path $dir -Parent
		if (-not $parent -or $parent -eq $dir) { break }
		$dir = $parent
	}
	return $null
}
function Save-Archive {
	$tar = Get-Command tar -ErrorAction SilentlyContinue
	if (-not $tar) { Fail 'tar is required to install Specwright' @('Install tar, then run this installer again.') }
	$url = if ($env:SPECWRIGHT_URL) { $env:SPECWRIGHT_URL } else { "https://github.com/$Repo/archive/refs/heads/$Ref.tar.gz" }
	$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("specwright-install." + [guid]::NewGuid().ToString('N').Substring(0, 8))
	New-Item -ItemType Directory -Path $temp -Force | Out-Null
	$bundle = Join-Path $temp 'src.tar.gz'
	$unpack = Join-Path $temp 'unpack'
	New-Item -ItemType Directory -Path $unpack -Force | Out-Null
	Write-Step "Downloading $Repo@$Ref"
	try {
		Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $bundle -TimeoutSec 60
	} catch {
		Fail 'download failed' @($url)
	}
	Write-OK "Downloaded $Repo@$Ref"
	Write-Lead 'Unpacking the source archive'
	& tar -xzf $bundle -C $unpack
	if ($LASTEXITCODE -ne 0) { Fail 'could not unpack the source archive' @() }
	$hit = Get-ChildItem -Path $unpack -Recurse -Filter SKILL.md | Where-Object { $_.FullName -replace '\\', '/' -match '/skills/sw-start/SKILL.md$' } | Select-Object -First 1
	if (-not $hit) { Fail 'the archive has no skills/sw-start/SKILL.md' @() }
	$root = Split-Path (Split-Path (Split-Path $hit.FullName -Parent) -Parent) -Parent
	if (-not (Test-Root $root)) { Fail 'the archive is not a Specwright checkout' @() }
	Write-OK "Unpacked $Repo@$Ref"
	$script:DownloadDir = $temp
	return $root
}

# -------------------------------------------------------------- the prompt --

function Read-Setup([string] $Prompt) {
	if ($script:Framed) {
		Write-Host ((Paint $script:Side 'bright') + "  " + (Paint $script:Bullet 'bright') + " $Prompt ") -NoNewline
		$value = Read-Host
		Write-Host ("`r" + $script:Esc + "[1A" + $script:Esc + "[2K") -NoNewline
		Write-Row ("  " + (Paint $script:Bullet 'bright') + " $Prompt " + $value)
	} else {
		$value = Read-Host "  > $Prompt"
	}
	if ($null -eq $value) { Fail 'Setup canceled: the terminal input closed.' @() }
	return $value.Trim()
}
function Clear-Choice([int] $Height) {
	Write-Host ("{0}[{1}A" -f $script:Esc, $Height) -NoNewline
	for ($i = 0; $i -lt $Height; $i++) { Write-Host ("`r{0}[2K" -f $script:Esc) }
	Write-Host ("{0}[{1}A" -f $script:Esc, $Height) -NoNewline
}
function Settle-Choice([int] $Height, [string] $Text) {
	Write-Host ("{0}[{1}A" -f $script:Esc, $Height) -NoNewline
	Write-Host ("`r{0}[2K{1}" -f $script:Esc, (Format-Row $Text))
	for ($i = 1; $i -lt $Height; $i++) { Write-Host ("`r{0}[1M" -f $script:Esc) -NoNewline }
}
function Write-Choice([string] $Prompt, [string[]] $Options, [int] $Pick) {
	Write-Row ("  " + (Paint $script:Bullet 'bright') + " $Prompt")
	$line = '  '
	for ($i = 0; $i -lt $Options.Count; $i++) {
		if ($i -eq $Pick) {
			$line += " " + $(if ($script:Color) { "$($script:Esc)[7m[ $($Options[$i]) ]$($script:Esc)[0m" } else { "[ $($Options[$i]) ]" })
		} else {
			$line += " " + (Paint "[$($Options[$i])]" 'dim')
		}
	}
	Write-Row $line
	Write-Row ('  ' + (Paint ($script:Left + '/' + $script:Right + ' to move ' + $script:Dot + ' Enter to pick ' + $script:Dot + ' q to cancel') 'dim'))
}
function Select-InstallOption([string] $Prompt, [string[]] $Options, [int] $Default = 0) {
	$pick = $Default
	if ($pick -lt 0) { $pick = 0 }
	if ($pick -ge $Options.Count) { $pick = $Options.Count - 1 }
	$height = 3
	if (-not $script:Terminal) {
		Write-Row ("  " + (Paint '>' 'bright') + " $Prompt")
		for ($i = 0; $i -lt $Options.Count; $i++) { Write-Row "    [$($i + 1)] $($Options[$i])" }
		$answer = Read-Setup "Choose 1-$($Options.Count)"
		if ($answer -eq '') { return $pick }
		if ($answer -match '^[0-9]+$' -and [int]$answer -ge 1 -and [int]$answer -le $Options.Count) {
			return ([int]$answer - 1)
		}
		return -1
	}
	try {
		while ($true) {
			Write-Choice $Prompt $Options $pick
			$key = [Console]::ReadKey($true)
			switch ([string]$key.Key) {
				'LeftArrow' { if ($pick -gt 0) { $pick-- } }
				'RightArrow' { if ($pick -lt $Options.Count - 1) { $pick++ } }
				'UpArrow' { if ($pick -gt 0) { $pick-- } }
				'DownArrow' { if ($pick -lt $Options.Count - 1) { $pick++ } }
				'Enter' { Settle-Choice $height ("  " + (Paint $script:Bullet 'bright') + " $Prompt " + (Paint $Options[$pick] 'bold')); return $pick }
				'Spacebar' { Settle-Choice $height ("  " + (Paint $script:Bullet 'bright') + " $Prompt " + (Paint $Options[$pick] 'bold')); return $pick }
				'Escape' { Settle-Choice $height ('  ' + (Paint ($script:Bullet + ' ' + $Prompt + ' (canceled)') 'dim')); return -1 }
				'Q' { Settle-Choice $height ('  ' + (Paint ($script:Bullet + ' ' + $Prompt + ' (canceled)') 'dim')); return -1 }
				default {
					$digit = [string]$key.KeyChar
					if ($digit -match '^[1-9]$' -and [int]$digit -le $Options.Count) { $pick = [int]$digit - 1 }
				}
			}
			Clear-Choice $height
		}
	} catch {
		Clear-Choice $height
		Write-Row ("  " + (Paint '>' 'bright') + " $Prompt")
		for ($i = 0; $i -lt $Options.Count; $i++) { Write-Row "    [$($i + 1)] $($Options[$i])" }
		$answer = Read-Setup "Choose 1-$($Options.Count)"
		if ($answer -eq '') { return $pick }
		if ($answer -match '^[0-9]+$' -and [int]$answer -ge 1 -and [int]$answer -le $Options.Count) {
			return ([int]$answer - 1)
		}
		return -1
	}
}

function Show-AgentIds {
	$line = '  '
	foreach ($item in $script:Agents) {
		$next = "$line$($item.Id) "
		if ((Get-Visible $next).Length -gt ($script:Inner - 2)) {
			Write-Row $line
			$line = "  $($item.Id) "
		} else {
			$line = $next
		}
	}
	if ($line.Trim()) { Write-Row $line }
}
function Read-AgentIds {
	while ($true) {
		Write-Note 'Comma-separated ids such as cursor, claude-code. Enter list to see every id.'
		$answer = Read-Setup 'Agent ids'
		if (-not $answer) { return $false }
		if ($answer -eq 'list') { Show-AgentIds; continue }
		$script:Selected = @()
		foreach ($tok in ($answer -split '[,\s]+' | Where-Object { $_ -ne '' })) { Add-Agent $tok }
		return ($script:Selected.Count -gt 0)
	}
}
function Read-DetectedChoice {
	for ($i = 0; $i -lt $script:Detected.Count; $i++) {
		Write-Row ("    $($i + 1)  $($script:Detected[$i])")
	}
	Write-Row ''
	$answer = Read-Setup 'Numbers or ids (* for all)'
	if (-not $answer) { return $false }
	if ($answer -eq '*' -or $answer -eq 'all') {
		$script:Selected = @($script:Detected)
		return $true
	}
	$script:Selected = @()
	foreach ($tok in ($answer -split '[,\s]+' | Where-Object { $_ -ne '' })) {
		if ($tok -match '^[0-9]+$') {
			$index = [int]$tok
			if ($index -lt 1 -or $index -gt $script:Detected.Count) { Fail "no detected agent numbered $tok" @() }
			Add-Agent $script:Detected[$index - 1]
		} else {
			Add-Agent $tok
		}
	}
	return ($script:Selected.Count -gt 0)
}

# ---------------------------------------------------------------- install ---

if ($ListAgents) {
	foreach ($item in $script:Agents) {
		Write-Host ("{0}`t{1}`t{2}" -f $item.Id, $item.Project, $item.Global)
	}
	exit 0
}

if (-not $Target) { $Target = (Get-Location).Path }
if ($Target.StartsWith('~')) { $Target = (Get-Home) + $Target.Substring(1) }
if (-not (Test-Path $Target -PathType Container)) { Fail 'project directory does not exist' @($Target) }
$script:Target = (Resolve-Path $Target).Path

$interactive = $false
try { $interactive = $script:Terminal -and -not $Yes -and -not [Console]::IsInputRedirected } catch { $interactive = $false }

foreach ($item in $script:Agents) {
	if (Test-AgentInstalled $item) { $script:Detected += $item.Id }
}
if ($Agent) {
	foreach ($part in $Agent) {
		foreach ($tok in ($part -split '[,\s]+' | Where-Object { $_ -ne '' })) { Add-Agent $tok }
	}
}

Write-ScreenOpen
if ($interactive) {
	Write-Section 'Make it yours'
	Write-Row '  All seven skills install together. Pick a scope and the agents.'
	Write-Row ("  " + (Paint "Project: $script:Target" 'mid'))
	Write-Row ''
	if ($Global -or $Project) {
		Write-Note "Scope: $($script:Scope)"
	} else {
		$scopePick = Select-InstallOption 'Where should the skills go?' @('All projects', 'This project') 0
		if ($scopePick -lt 0) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 }
		if ($scopePick -eq 1) { $script:Scope = 'project' } else { $script:Scope = 'global' }
	}
	if ($script:Selected.Count -eq 0) {
		if ($script:Detected.Count -gt 0) {
			$which = Select-InstallOption 'Which agents?' @("All detected ($($script:Detected.Count))", "Choose$($script:Ellipsis)", "Enter ids$($script:Ellipsis)") 0
			if ($which -lt 0) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 }
			switch ($which) {
				0 { $script:Selected = @($script:Detected) }
				1 { if (-not (Read-DetectedChoice)) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 } }
				2 { if (-not (Read-AgentIds)) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 } }
			}
		} else {
			$which = Select-InstallOption 'No agents detected. Install where?' @('Universal', "Enter ids$($script:Ellipsis)") 0
			if ($which -lt 0) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 }
			switch ($which) {
				0 { $script:Selected = @('universal') }
				1 { if (-not (Read-AgentIds)) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 } }
			}
		}
	} else {
		Write-Note ("Agents: " + ($script:Selected -join ' '))
	}
	Write-Note ("Skills: " + ($Skills -join ' '))
	$ready = Select-InstallOption 'Ready to install?' @('Install', 'Cancel') 0
	if ($ready -ne 0) { Write-Note 'Setup canceled. Nothing was changed.'; exit 0 }
} else {
	Write-Section 'Use your selected settings'
	Write-Note 'Running without prompts. Use -Help to see setup options.'
	if ($script:Selected.Count -eq 0) {
		if ($script:Detected.Count -gt 0) {
			$script:Selected = @($script:Detected)
			Write-Note 'Agents: every detected agent'
		} else {
			$script:Selected = @('universal')
			Write-Note 'No agents detected; installing for universal'
		}
	} else {
		Write-Note ("Agents: " + ($script:Selected -join ' '))
	}
	Write-Note "Scope: $($script:Scope)"
}

Write-Section 'Install Specwright'
$scriptDir = ''
if ($PSCommandPath) { $scriptDir = Split-Path $PSCommandPath -Parent }
elseif ($PSScriptRoot) { $scriptDir = $PSScriptRoot }
if ($env:SPECWRIGHT_ROOT) {
	if (-not (Test-Root $env:SPECWRIGHT_ROOT)) { Fail 'SPECWRIGHT_ROOT is not a Specwright checkout' @($env:SPECWRIGHT_ROOT) }
	$script:SkillRoot = $env:SPECWRIGHT_ROOT
} elseif ($scriptDir) {
	$found = Find-Root $scriptDir
	if ($found) { $script:SkillRoot = $found }
}
if ($script:SkillRoot) {
	Write-Note "Using the checkout at $($script:SkillRoot)"
} else {
	Write-Note "No local checkout; downloading $Repo@$Ref"
	$script:SkillRoot = Save-Archive
}
foreach ($skill in $Skills) {
	$path = Join-Rel $script:SkillRoot "skills/$skill/SKILL.md"
	if (-not (Test-Path $path)) { Fail "missing skill: $skill" @($path) }
}

$raw = @()
foreach ($id in $script:Selected) {
	$item = Get-Agent $id
	if ($script:Scope -eq 'global') {
		$dest = Expand-Global $item.Global
		if (-not $dest) { Write-Note "$id is project-only; skipped"; continue }
	} else {
		$dest = Join-Rel $script:Target $item.Project
	}
	$raw += $dest.TrimEnd('\', '/')
}
$script:Destinations = @($raw | Select-Object -Unique)
if ($script:Destinations.Count -eq 0) {
	Fail 'no install location for the selected agents' @(
		'Project-only agents cannot take a global install.',
		'Pick another agent, or rerun with -Project.'
	)
}

function Test-SpecwrightSkill([string] $Path, [string] $Skill) {
	$item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
	if (-not $item) { return $false }
	$reparse = [IO.FileAttributes]::ReparsePoint
	if (($item.Attributes -band $reparse) -and -not (Test-Path -LiteralPath $Path)) { return $true }
	$skillMd = Join-Path $Path 'SKILL.md'
	if (-not (Test-Path -LiteralPath $skillMd)) { return $false }
	foreach ($line in (Get-Content -LiteralPath $skillMd -TotalCount 30)) {
		if ($line -eq "name: $Skill") { return $true }
	}
	return $false
}
$previous = @()
foreach ($dest in $script:Destinations) {
	foreach ($skill in $Skills) {
		$path = Join-Path $dest $skill
		if (-not (Test-Path -LiteralPath $path)) { continue }
		if (-not (Test-SpecwrightSkill $path $skill)) {
			Fail 'refusing to replace a folder that is not a Specwright skill' @(
				$path,
				"That folder has no matching name: $skill in SKILL.md."
			)
		}
		$item = Get-Item -LiteralPath $path -Force
		$reparse = [IO.FileAttributes]::ReparsePoint
		if (-not ($item.Attributes -band $reparse)) {
			$source = (Resolve-Path -LiteralPath (Join-Rel $script:SkillRoot "skills/$skill")).Path
			if ($item.FullName -eq $source) { Fail 'refusing to delete the skill source' @($path) }
		}
		$previous += $path
	}
}
if ($previous.Count -gt 0) {
	Write-Note "Replacing $($previous.Count) existing Specwright skill folder(s)"
	foreach ($path in $previous) {
		$item = Get-Item -LiteralPath $path -Force
		if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
			Remove-Item -LiteralPath $path -Force
		} else {
			Remove-Item -LiteralPath $path -Recurse -Force
		}
	}
	Write-OK 'Removed the previous install'
}

foreach ($dest in $script:Destinations) {
	Write-Step "Installing into $dest"
	New-Item -ItemType Directory -Force -Path $dest | Out-Null
	foreach ($skill in $Skills) {
		Copy-Item -Recurse -Path (Join-Rel $script:SkillRoot "skills/$skill") -Destination (Join-Path $dest $skill)
	}
	Write-OK "Copied 7 skills into $dest"
}

Write-Rule
Write-OK (Paint 'Specwright is installed.' 'bold')
Write-Row ''
Write-Row ("  " + (Paint 'Scope' 'mid') + "    $($script:Scope)")
Write-Row ("  " + (Paint 'Skills' 'mid') + "   7 skills in $($script:Destinations.Count) location(s)")
Write-Row ''
foreach ($dest in $script:Destinations) { Write-Row ("  " + (Paint $script:Dot 'mid') + " $dest") }
Write-Row ''
Write-Row (Paint '  Your next step' 'bold')
Write-Row '  Open the project in your agent and say what you want:'
Write-Row '    start a spec for the refunds flow'
Write-Row ''
Write-Note 'To update, run this installer again.'
Write-ScreenClose
if ($script:DownloadDir) { Remove-Item -Recurse -Force $script:DownloadDir -ErrorAction SilentlyContinue }
