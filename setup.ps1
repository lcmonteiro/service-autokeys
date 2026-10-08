# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
# autokeys installer for windows
#
#   local  : .\setup.ps1
#   remote : irm https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.ps1 | iex
#
# With options when installing remotely:
#
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/lcmonteiro/service-autokeys/main/setup.ps1))) -NoTool
#
# When piped the sources are downloaded to $AUTOKEYS_HOME, otherwise the checkout holding
# this script is used. Either way the environment is built with uv.
#
# Errors are thrown rather than exiting: under 'iex' an exit would close the user's shell.
# =======================================================================================
param(
    [string] $Ref       = $(if ($env:AUTOKEYS_REF)        { $env:AUTOKEYS_REF }        else { 'main' }),
    [string] $Dir       = $(if ($env:AUTOKEYS_HOME)       { $env:AUTOKEYS_HOME }       else { Join-Path $env:LOCALAPPDATA 'autokeys' }),
    [string] $ConfigDir = $(if ($env:AUTOKEYS_CONFIG_DIR) { $env:AUTOKEYS_CONFIG_DIR } else { Join-Path $env:APPDATA 'autokeys' }),
    [switch] $NoTool,
    [switch] $Help
)

# the script path is only known when run from a file, not when piped to iex
$AutokeysScript = $PSCommandPath

& {
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ---------------------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------------------
$RepoUrl = if ($env:AUTOKEYS_REPO) { $env:AUTOKEYS_REPO } else { 'https://github.com/lcmonteiro/service-autokeys' }
$SrcDir  = $Dir
$CfgDir  = $ConfigDir
$BinDir  = Join-Path $HOME '.local\bin'

# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------
function Log  ([string] $Message) { Write-Host ':: ' -ForegroundColor Blue -NoNewline; Write-Host $Message }
function Warn ([string] $Message) { Write-Host '!! ' -ForegroundColor Yellow -NoNewline; Write-Host $Message }
function Die  ([string] $Message) { throw "autokeys setup: $Message" }
function Has  ([string] $Name)    { [bool] (Get-Command $Name -ErrorAction SilentlyContinue) }

# run a native command and fail on a non zero exit code
function Invoke-Native ([string] $Command, [string[]] $Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { Die "'$Command $($Arguments -join ' ')' failed ($LASTEXITCODE)" }
}

function Show-Usage {
    @"
usage: setup.ps1 [options]

  -Ref <git-ref>      branch, tag or commit to install (default: $Ref)
  -Dir <path>         where the sources live when downloaded (default: $SrcDir)
  -ConfigDir <path>   where the settings file lives (default: $CfgDir)
  -NoTool             only build the project environment, do not install the
                      'autokeys' command on the PATH
  -Help               show this help

environment: AUTOKEYS_REPO, AUTOKEYS_REF, AUTOKEYS_HOME, AUTOKEYS_CONFIG_DIR
"@ | Write-Host
}

# windows powershell 5.1 does not enable tls 1.2 by default, which github requires
function Enable-Tls12 {
    if ($PSVersionTable.PSVersion.Major -lt 6) {
        [Net.ServicePointManager]::SecurityProtocol = `
            [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    }
}

# ---------------------------------------------------------------------------------------
# uv
# ---------------------------------------------------------------------------------------
function Install-Uv {
    if (Has 'uv') {
        Log "uv found ($(uv --version))"
        return
    }
    Log 'installing uv'
    # the official installer, in its own process so its policy and exits stay there
    $powershell = (Get-Process -Id $PID).Path
    Invoke-Native $powershell @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
        'irm https://astral.sh/uv/install.ps1 | iex')
    # the installer updates the user PATH, make uv visible in this session right away
    $env:Path = "$BinDir;$(Join-Path $HOME '.cargo\bin');$env:Path"
    if (-not (Has 'uv')) { Die "uv installation failed, add $BinDir to your PATH and retry" }
    Log "uv installed ($(uv --version))"
}

# ---------------------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------------------
# the checkout holding this script, nothing when piped to iex
function Find-LocalSources {
    if (-not $AutokeysScript) { return $null }
    $here = Split-Path -Parent $AutokeysScript
    if (Test-Path (Join-Path $here 'pyproject.toml')) { return $here }
    return $null
}

function Get-Sources {
    if (Has 'git') {
        if (Test-Path (Join-Path $SrcDir '.git')) {
            Log "updating sources: $SrcDir ($Ref)"
            Invoke-Native 'git' @('-C', $SrcDir, 'fetch', '--quiet', '--depth', '1', 'origin', $Ref)
            Invoke-Native 'git' @('-C', $SrcDir, 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
        } else {
            Log "cloning sources: $SrcDir ($Ref)"
            if (Test-Path $SrcDir) { Remove-Item -Recurse -Force $SrcDir }
            New-Item -ItemType Directory -Force (Split-Path -Parent $SrcDir) | Out-Null
            Invoke-Native 'git' @('clone', '--quiet', '--depth', '1', '--branch', $Ref, $RepoUrl, $SrcDir)
        }
    } else {
        # no git, fall back to the source archive
        Log "downloading sources: $SrcDir ($Ref)"
        $temp = Join-Path ([IO.Path]::GetTempPath()) "autokeys-$([guid]::NewGuid())"
        New-Item -ItemType Directory -Force $temp | Out-Null
        try {
            $zip = Join-Path $temp 'sources.zip'
            Invoke-WebRequest -UseBasicParsing -Uri "$($RepoUrl -replace '\.git$', '')/archive/$Ref.zip" -OutFile $zip
            Expand-Archive -Path $zip -DestinationPath $temp
            # the archive holds a single top level folder named after the repository and ref
            $root = Get-ChildItem -Path $temp -Directory | Select-Object -First 1
            if (Test-Path $SrcDir) { Remove-Item -Recurse -Force $SrcDir }
            New-Item -ItemType Directory -Force (Split-Path -Parent $SrcDir) | Out-Null
            Move-Item -Path $root.FullName -Destination $SrcDir
        } finally {
            Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
        }
    }
    if (-not (Test-Path (Join-Path $SrcDir 'pyproject.toml'))) { Die "no pyproject.toml found in $SrcDir" }
}

# ---------------------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------------------
function Build-Environment {
    Log 'building the environment with uv'
    if (Test-Path (Join-Path $SrcDir 'uv.lock')) {
        Invoke-Native 'uv' @('sync', '--project', $SrcDir, '--frozen', '--no-dev')
    } else {
        Invoke-Native 'uv' @('sync', '--project', $SrcDir, '--no-dev')
    }
}

function Install-Command {
    if ($NoTool) { return }
    Log "installing the 'autokeys' command"
    Invoke-Native 'uv' @('tool', 'install', '--force', '--from', $SrcDir, 'autokeys')
}

# the settings hold credentials: only the current user may read them
function Protect-Path ([string] $Path) {
    if ($env:OS -ne 'Windows_NT') { return }
    $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    Invoke-Native 'icacls' @($Path, '/inheritance:r', '/grant:r', "${user}:(OI)(CI)F", '/Q') | Out-Null
}

function Install-Settings {
    $target = Join-Path $CfgDir 'config.yml'
    if (Test-Path $target) {
        Log "settings kept: $target"
        return
    }
    $sample = Join-Path $SrcDir 'config-sample.yml'
    if (-not (Test-Path $sample)) { return }
    Log "creating settings from sample: $target"
    New-Item -ItemType Directory -Force $CfgDir | Out-Null
    Protect-Path $CfgDir
    Copy-Item $sample $target
}

# ---------------------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------------------
if ($Help) {
    Show-Usage
    return
}

Enable-Tls12
Install-Uv
$local = Find-LocalSources
if ($local) {
    $SrcDir = $local
    Log "using local sources: $SrcDir"
} else {
    Get-Sources
}
Build-Environment
Install-Command
Install-Settings

$settings = Join-Path $CfgDir 'config.yml'
Write-Host @"

  autokeys is installed

    sources  : $SrcDir
    settings : $settings

  edit the settings and start the service with

    & '$(Join-Path $SrcDir 'run.ps1')'
"@
if (-not $NoTool) {
    Write-Host @"

  or, once $BinDir is on your PATH (open a new terminal)

    autokeys '$settings'
"@
}
Write-Host
}
# =======================================================================================
# End
# =======================================================================================
