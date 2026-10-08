param(
    [string[]]$QuestionSets = @(
        "eval/phase2_eval_32_candidate.json",
        "eval/question_coverage_50.json"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Test-PythonInvocationHasTextMetricPackages {
    param([Parameter(Mandatory = $true)][string[]]$Invocation)

    try {
        if ($Invocation.Count -eq 1) {
            & $Invocation[0] -c 'import bert_score, rouge_score' *> $null
        } else {
            & $Invocation[0] $Invocation[1] -c 'import bert_score, rouge_score' *> $null
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
        if (Test-PythonInvocationHasTextMetricPackages -Invocation $candidate) {
            return $candidate
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidate = @($pythonCommand.Source)
        if (Test-PythonInvocationHasTextMetricPackages -Invocation $candidate) {
            return $candidate
        }
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        try {
            $candidate = @($pyCommand.Source, '-3')
            if (Test-PythonInvocationHasTextMetricPackages -Invocation $candidate) {
                return $candidate
            }
        } catch {
        }
    }

    $knownLocalVersions = @('Python314', 'Python313', 'Python312', 'Python311', 'Python310')
    foreach ($version in $knownLocalVersions) {
        $candidate = Join-Path $env:LocalAppData ("Programs\\Python\\{0}\\python.exe" -f $version)
        if (Test-Path -LiteralPath $candidate) {
            $invocation = @($candidate)
            if (Test-PythonInvocationHasTextMetricPackages -Invocation $invocation) {
                return $invocation
            }
        }
    }

    $codexRuntimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $codexRuntimePython) {
        $candidate = @($codexRuntimePython)
        if (Test-PythonInvocationHasTextMetricPackages -Invocation $candidate) {
            return $candidate
        }
    }

    throw "Python 3 with bert_score and rouge_score was not found automatically. Set SSL_PYTHON_PATH to a python.exe with requirements.txt installed."
}

function Invoke-PythonScript {
    param(
        [Parameter(Mandatory = $true)][string[]]$PythonInvocation,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    if ($PythonInvocation.Count -eq 1) {
        & $PythonInvocation[0] $ScriptPath @Arguments
        return
    }

    & $PythonInvocation[0] $PythonInvocation[1] $ScriptPath @Arguments
}

$pythonInvocation = @(Get-PythonInvocation)

foreach ($questionSet in $QuestionSets) {
    $questionPath = Join-Path $repoRoot $questionSet
    if (-not (Test-Path -LiteralPath $questionPath)) {
        throw "Missing question set: $questionSet"
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($questionSet)
    $resultsMd = "eval/{0}_results.md" -f $baseName
    $metricsJson = "eval/text_metrics_{0}.json" -f $baseName

    Write-Host ""
    Write-Host "== Running benchmark for $questionSet =="
    & (Join-Path $repoRoot "src/Run-Demo.ps1") -QuestionsPath $questionSet

    Write-Host "== Computing text metrics for $resultsMd =="
    $metricsScript = Join-Path $repoRoot "src/eval_text_metrics.py"
    if ($questionSet -eq "eval/question_coverage_50.json") {
        $metricArgs = @('--results-md', $resultsMd, '--out-json', $metricsJson, '--reference-json', 'eval/phase2_eval_32_candidate.json', 'eval/question_coverage_50_extra_references_18.json')
        Invoke-PythonScript -PythonInvocation $pythonInvocation -ScriptPath $metricsScript -Arguments $metricArgs
    } else {
        $metricArgs = @('--results-md', $resultsMd, '--out-json', $metricsJson)
        Invoke-PythonScript -PythonInvocation $pythonInvocation -ScriptPath $metricsScript -Arguments $metricArgs
    }
}

Write-Host ""
Write-Host "Done. Outputs written to eval/text_metrics_*.json"
