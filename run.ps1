# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
# autokeys launcher for windows
#
#   .\run.ps1                     use the default settings file
#   .\run.ps1 path\to\config.yml  use a specific settings file
#
# The environment is created and kept in sync by uv on every run.
# =======================================================================================
param(
    [Parameter(Position = 0)] [string] $Settings,
    [Parameter(ValueFromRemainingArguments = $true)] [string[]] $Rest = @(),
    [switch] $Help
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ---------------------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------------------
$SrcDir = $PSScriptRoot
$CfgDir = if ($env:AUTOKEYS_CONFIG_DIR) { $env:AUTOKEYS_CONFIG_DIR } else { Join-Path $env:APPDATA 'autokeys' }

# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------
function Die ([string] $Message) {
    Write-Host 'xx ' -ForegroundColor Red -NoNewline
    Write-Host $Message
    exit 1
}

function Show-Usage {
    @"
usage: run.ps1 [settings-file]

  settings-file  path of the settings file, by default the first of
                 `$env:AUTOKEYS_CONFIG, $CfgDir\config.yml, .\config.yml
"@ | Write-Host
}

# first settings file that exists, from the most specific to the most generic
function Resolve-Settings {
    foreach ($candidate in @($env:AUTOKEYS_CONFIG, (Join-Path $CfgDir 'config.yml'), (Join-Path $SrcDir 'config.yml'))) {
        if ($candidate -and (Test-Path -PathType Leaf $candidate)) { return $candidate }
    }
    Die "no settings file found, create $CfgDir\config.yml (see config-sample.yml)"
}

# ---------------------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------------------
if ($Help) {
    Show-Usage
    exit 0
}

if (-not (Get-Command 'uv' -ErrorAction SilentlyContinue)) {
    $env:Path = "$(Join-Path $HOME '.local\bin');$env:Path"
    if (-not (Get-Command 'uv' -ErrorAction SilentlyContinue)) { Die 'uv not found, run setup.ps1 first' }
}

if ($Settings) {
    if (-not (Test-Path -PathType Leaf $Settings)) { Die "settings file not found: $Settings" }
} else {
    $Settings = Resolve-Settings
}

& uv run --project $SrcDir --no-dev autokeys $Settings @Rest
exit $LASTEXITCODE
# =======================================================================================
# End
# =======================================================================================
