# Check Python and Node 24, and install Node into the user's own folder after consent.
#
# PowerShell, not Python, on purpose: the check has to run when Python is missing.
#
#   powershell -NoProfile -File runtime.ps1 check [-Json]    read only
#   powershell -NoProfile -File runtime.ps1 plan node|python  print what an install would do
#   powershell -NoProfile -File runtime.ps1 install node -Yes
#   powershell -NoProfile -File runtime.ps1 install python -Yes   (winget, no administrator rights)
#
# Exit codes: 0 ok, 1 a runtime is missing or too old, 2 usage or download failure,
# 3 consent missing. Nothing here changes PATH. The agent passes -Yes only after the user
# approves the exact plan in this session.
param(
    [Parameter(Position = 0)][string]$Command = '',
    [Parameter(Position = 1)][string]$Tool = '',
    [switch]$Yes,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
$NodeMajor = 24
$PyMajor = 3
$PyMinor = 10
$Pins = Join-Path $PSScriptRoot 'runtime-pins.tsv'
$HomeRoot = if ($env:SPECWRIGHT_HOME) { $env:SPECWRIGHT_HOME } else { Join-Path $env:USERPROFILE '.specwright' }
$RuntimeHome = Join-Path $HomeRoot 'runtime'

if ($env:SPECWRIGHT_RUNTIME_TEST_BASE) {
    # Test hook: a file:// folder that holds runtime-pins.tsv and the archives. Never a network URL.
    if (-not $env:SPECWRIGHT_RUNTIME_TEST_BASE.StartsWith('file://')) {
        [Console]::Error.WriteLine('error: SPECWRIGHT_RUNTIME_TEST_BASE must be a file:// location')
        exit 2
    }
    $Pins = Join-Path ([Uri]$env:SPECWRIGHT_RUNTIME_TEST_BASE).LocalPath 'runtime-pins.tsv'
}

function Stop-With([string]$Message, [int]$Code = 2) {
    [Console]::Error.WriteLine("error: $Message")
    exit $Code
}

function Show-Usage([int]$Code = 2) {
    Get-Content -LiteralPath $PSCommandPath -TotalCount 12 | Select-Object -Skip 1 | ForEach-Object { $_ -replace '^# ?', '' }
    exit $Code
}

function Get-Ver([string]$Text) {
    if ($Text -match '(\d+)\.(\d+)\.(\d+)') { return [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])" }
    return $null
}

function Find-Python {
    foreach ($candidate in @(@('python3'), @('python'), @('py', '-3'))) {
        $found = Get-Command $candidate[0] -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $found) { continue }
        # The Microsoft Store stubs exist on PATH but print a notice instead of running.
        try {
            $extra = @($candidate | Select-Object -Skip 1)
            $out = & $found.Source @extra -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $version = Get-Ver ([string]$out)
            if ($version -and $version.Major -eq $PyMajor) { return @{ Path = $found.Source; Version = $version } }
        } catch { continue }
    }
    return $null
}

function Find-Node {
    if (Test-Path -LiteralPath $RuntimeHome) {
        $own = Get-ChildItem -LiteralPath $RuntimeHome -Directory -Filter 'node-v*' | Sort-Object Name -Descending
        foreach ($folder in $own) {
            $exe = Join-Path $folder.FullName 'node.exe'
            if (Test-Path -LiteralPath $exe) { return $exe }
        }
    }
    $onPath = Get-Command node -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($onPath) { return $onPath.Source }
    return $null
}

function Invoke-Check {
    $python = Find-Python
    $nodePath = Find-Node
    $nodeVersion = $null
    $npmPath = $null
    if ($nodePath) {
        $nodeVersion = Get-Ver ([string](& $nodePath --version 2>$null))
        $npm = Join-Path (Split-Path -Parent $nodePath) 'npm.cmd'
        if (Test-Path -LiteralPath $npm) { $npmPath = $npm }
    }
    if (-not $npmPath) {
        $onPath = Get-Command npm -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($onPath) { $npmPath = $onPath.Source }
    }
    $pyOk = [bool]($python -and ($python.Version -ge [version]"$PyMajor.$PyMinor.0"))
    $nodeOk = [bool]($nodeVersion -and $nodeVersion.Major -ge $NodeMajor)
    $npmOk = [bool]$npmPath
    if ($Json) {
        [ordered]@{
            python = [ordered]@{ path = if ($python) { $python.Path } else { $null }; version = if ($python) { "$($python.Version)" } else { $null }; ok = $pyOk; need = ">=$PyMajor.$PyMinor" }
            node   = [ordered]@{ path = $nodePath; version = if ($nodeVersion) { "$nodeVersion" } else { $null }; ok = $nodeOk; need = ">=$NodeMajor" }
            npm    = [ordered]@{ path = $npmPath; version = $null; ok = $npmOk; need = 'bundled with Node' }
        } | ConvertTo-Json -Depth 3
    } else {
        $rows = @(
            @('python', $(if ($python) { "$($python.Version)" } else { '-' }), $pyOk, ">=$PyMajor.$PyMinor"),
            @('node', $(if ($nodeVersion) { "$nodeVersion" } else { '-' }), $nodeOk, ">=$NodeMajor"),
            @('npm', '-', $npmOk, 'bundled with Node')
        )
        foreach ($row in $rows) {
            $state = if ($row[2]) { 'ok' } else { 'missing or too old' }
            Write-Output "$($row[0]): $($row[1]) ($state; need $($row[3]))"
        }
    }
    if ($pyOk -and $nodeOk -and $npmOk) { exit 0 } else { exit 1 }
}

function Get-Pin {
    if (-not (Test-Path -LiteralPath $Pins)) { Stop-With "pins file missing: $Pins; reinstall this skill from a zip that includes _shared" }
    if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
        Stop-With "no pinned Node build for this Windows architecture"
    }
    $rows = Get-Content -LiteralPath $Pins | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { , ($_ -split "`t") }
    $base = ($rows | Where-Object { $_[0] -eq 'base' })[1]
    $row = $rows | Where-Object { $_[0] -eq 'win-x64' }
    if (-not $base -or -not $row) { Stop-With 'no pin for win-x64' }
    $archive = $row[1]
    return @{
        Archive = $archive
        Digest  = $row[2]
        Url     = "$base/$archive"
        Base    = $base
        Folder  = Join-Path $RuntimeHome ($archive -replace '\.zip$', '')
    }
}

function Invoke-PlanNode {
    $pin = Get-Pin
    Write-Output "Install Node $(($pin.Base -split '/v')[-1]) (the pinned release of Node $NodeMajor)."
    Write-Output "Download:   $($pin.Url)"
    Write-Output "Expect sha256 $($pin.Digest); the download is rejected before unpacking if it differs."
    Write-Output "Unpack to:  $($pin.Folder)"
    Write-Output 'No administrator rights, no PATH change, nothing outside that folder.'
    Write-Output 'To do it yourself instead: `winget install OpenJS.NodeJS`, `brew install node@24`, or `fnm install 24`.'
}

function Invoke-PlanPython {
    Write-Output "Python $PyMajor.$PyMinor or newer is needed to run the skill scripts."
    Write-Output 'Command:    winget install --id Python.Python.3.13 --scope user'
    Write-Output 'It installs for your own user, with no administrator rights.'
}

function Invoke-InstallNode {
    if (-not $Yes) { Stop-With "installing Node needs the user's approval; run with -Yes after it" 3 }
    $pin = Get-Pin
    if (Test-Path -LiteralPath $pin.Folder) { Write-Output "installed: $($pin.Folder)"; return }
    $source = $pin.Url
    if ($env:SPECWRIGHT_RUNTIME_TEST_BASE) {
        $source = (Join-Path ([Uri]$env:SPECWRIGHT_RUNTIME_TEST_BASE).LocalPath $pin.Archive)
    } elseif (-not $pin.Url.StartsWith('https://nodejs.org/dist/')) {
        Stop-With 'refusing a download outside the pinned nodejs.org location'
    }
    New-Item -ItemType Directory -Force -Path $RuntimeHome | Out-Null
    $work = Join-Path $RuntimeHome (".work." + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $work | Out-Null
    try {
        $archive = Join-Path $work $pin.Archive
        if ($env:SPECWRIGHT_RUNTIME_TEST_BASE) { Copy-Item -LiteralPath $source -Destination $archive }
        else { Invoke-WebRequest -UseBasicParsing -Uri $source -OutFile $archive }
        $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $pin.Digest) { Stop-With "the download does not match the pinned sha256 for $($pin.Archive)" }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
        try {
            foreach ($entry in $zip.Entries) {
                $name = $entry.FullName
                if ($name.StartsWith('/') -or $name.StartsWith('\') -or $name.Contains(':') -or (($name -split '[\\/]') -contains '..')) {
                    Stop-With "unsafe path in the archive: $name"
                }
            }
        } finally { $zip.Dispose() }
        $out = Join-Path $work 'unpacked'
        Expand-Archive -LiteralPath $archive -DestinationPath $out
        $roots = @(Get-ChildItem -LiteralPath $out)
        if ($roots.Count -ne 1 -or -not $roots[0].PSIsContainer) { Stop-With 'the archive does not hold one top-level folder' }
        Move-Item -LiteralPath $roots[0].FullName -Destination $pin.Folder
        Write-Output "installed: $($pin.Folder)"
    } finally {
        Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-InstallPython {
    if (-not $Yes) { Stop-With "installing Python needs the user's approval; run with -Yes after it" 3 }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Stop-With 'winget was not found; download Python 3.10 or newer from https://www.python.org/downloads/' 2
    }
    & winget install --id Python.Python.3.13 --scope user --exact
    exit $LASTEXITCODE
}

switch ($Command) {
    'check' { Invoke-Check }
    'plan' {
        switch ($Tool) { 'node' { Invoke-PlanNode } 'python' { Invoke-PlanPython } default { Show-Usage 2 } }
    }
    'install' {
        switch ($Tool) { 'node' { Invoke-InstallNode } 'python' { Invoke-InstallPython } default { Show-Usage 2 } }
    }
    { $_ -in @('-h', '--help', 'help') } { Show-Usage 0 }
    default { Show-Usage 2 }
}
