param(
    [string]$ResultsMd = "eval/manualscoring1_postfix_results.md",
    [string]$OutJson = "eval/llm_jury_manualscoring1_postfix.json",
    [string]$OutMd = "eval/llm_jury_manualscoring1_postfix.md",
    [string[]]$Models,
    [int]$JurySize = 3,
    [int]$Limit,
    [string[]]$Ids,
    [switch]$Mock
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Test-PythonInvocationUsable {
    param([Parameter(Mandatory = $true)][string[]]$Invocation)

    try {
        if ($Invocation.Count -eq 1) {
            & $Invocation[0] --version *> $null
        } else {
            & $Invocation[0] $Invocation[1] --version *> $null
        }
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-PythonInvocation {
    $explicitPython = $env:SSL_PYTHON_PATH
    if (-not [string]::IsNullOrWhiteSpace($explicitPython) -and (Test-Path -LiteralPath $explicitPython)) {
        $candidate = @($explicitPython)
        if (Test-PythonInvocationUsable -Invocation $candidate) { return $candidate }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidate = @($pythonCommand.Source)
        if (Test-PythonInvocationUsable -Invocation $candidate) { return $candidate }
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $candidate = @($pyCommand.Source, '-3')
        if (Test-PythonInvocationUsable -Invocation $candidate) { return $candidate }
    }

    $knownLocalVersions = @('Python314', 'Python313', 'Python312', 'Python311', 'Python310')
    foreach ($version in $knownLocalVersions) {
        $candidate = Join-Path $env:LocalAppData ("Programs\\Python\\{0}\\python.exe" -f $version)
        if (Test-Path -LiteralPath $candidate) {
            $invocation = @($candidate)
            if (Test-PythonInvocationUsable -Invocation $invocation) { return $invocation }
        }
    }

    $codexRuntimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $codexRuntimePython) {
        $candidate = @($codexRuntimePython)
        if (Test-PythonInvocationUsable -Invocation $candidate) { return $candidate }
    }

    throw "Python 3 was not found automatically. Set SSL_PYTHON_PATH to a local python.exe path."
}

$pythonInvocation = @(Get-PythonInvocation)
$scriptPath = Join-Path $repoRoot "src/llm_judge_jury.py"

$arguments = @(
    $scriptPath,
    "--results-md", $ResultsMd,
    "--out-json", $OutJson,
    "--out-md", $OutMd,
    "--jury-size", [string]$JurySize
)

if ($Mock) {
    $arguments += "--mock"
}
if ($PSBoundParameters.ContainsKey("Limit")) {
    $arguments += @("--limit", [string]$Limit)
}
if ($Models -and $Models.Count -gt 0) {
    $arguments += "--models"
    $arguments += $Models
}
if ($Ids -and $Ids.Count -gt 0) {
    $arguments += "--ids"
    $arguments += $Ids
}

if ($pythonInvocation.Count -eq 1) {
    & $pythonInvocation[0] @arguments
} else {
    & $pythonInvocation[0] $pythonInvocation[1] @arguments
}
