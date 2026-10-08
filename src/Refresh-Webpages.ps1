param(
    [string[]]$SourceId,
    [int]$TimeoutSeconds = 30,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pyScript = Join-Path $PSScriptRoot 'refresh_webpages.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing refresh script: $pyScript"
}

$argList = @()
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
$pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
}

if ($pyCmd) {
    $argList = @('-3', $pyScript)
} elseif ($pythonCmd) {
    $argList = @($pyScript)
} else {
    throw "Python was not found (tried py, python3, python). Install Python 3 or add it to PATH."
}

foreach ($id in $SourceId) {
    if (-not [string]::IsNullOrWhiteSpace($id)) {
        $argList += '--source-id'
        $argList += $id.Trim()
    }
}

$argList += '--timeout-seconds'
$argList += "$TimeoutSeconds"

if ($DryRun) {
    $argList += '--dry-run'
}

if ($pyCmd) {
    & py @argList
} else {
    & $pythonCmd.Source @argList
}

exit $LASTEXITCODE
