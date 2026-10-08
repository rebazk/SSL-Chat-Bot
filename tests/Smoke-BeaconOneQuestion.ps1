# One-question smoke check for the retrieval + answer path (no UI server).
# Fails fast when the corpus or pipeline is broken. Intended for CI or pre-commit.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$ask = Join-Path $repoRoot 'src/Ask-SSL.ps1'

if (-not (Test-Path -LiteralPath $ask)) {
    throw "Missing Ask-SSL.ps1 at $ask"
}

$question = "Summarize SSL's work in the last five years."
$runner = (Get-Process -Id $PID).Path
$raw = & $runner -NoProfile -File $ask -Question $question -Json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Ask-SSL.ps1 failed: $raw"
}

$result = $raw | ConvertFrom-Json
if (-not $result.supported) {
    throw "Smoke question should be supported; got supported=$($result.supported). Answer: $($result.answer)"
}

if ([string]::IsNullOrWhiteSpace([string]$result.answer)) {
    throw 'Smoke question returned an empty answer.'
}

Write-Host "Smoke OK: synthesis-style question answered as supported."
