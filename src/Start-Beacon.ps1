param(
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8765,
    [string]$PythonPath,
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

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
    param([string]$ExplicitPythonPath)

    if ($ExplicitPythonPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPythonPath)) {
            throw "The specified Python path was not found: $ExplicitPythonPath"
        }
        $candidate = @($ExplicitPythonPath)
        if (Test-PythonInvocationUsable -Invocation $candidate) {
            return $candidate
        }
        throw "The specified Python path could not be executed: $ExplicitPythonPath"
    }

    $envPythonPath = $env:SSL_PYTHON_PATH
    if (-not [string]::IsNullOrWhiteSpace($envPythonPath) -and (Test-Path -LiteralPath $envPythonPath)) {
        $candidate = @($envPythonPath)
        if (Test-PythonInvocationUsable -Invocation $candidate) {
            return $candidate
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidate = @($pythonCommand.Source)
        if (Test-PythonInvocationUsable -Invocation $candidate) {
            return $candidate
        }
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        try {
            & $pyCommand.Source -3 --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return @($pyCommand.Source, '-3')
            }
        } catch {
        }
    }

    $knownLocalVersions = @('Python314', 'Python313', 'Python312', 'Python311', 'Python310')
    foreach ($version in $knownLocalVersions) {
        $candidate = Join-Path $env:LocalAppData ("Programs\\Python\\{0}\\python.exe" -f $version)
        if (Test-Path -LiteralPath $candidate) {
            $invocation = @($candidate)
            if (Test-PythonInvocationUsable -Invocation $invocation) {
                return $invocation
            }
        }
    }

    $localPythonRoot = Join-Path $env:LocalAppData 'Programs\Python'
    if (Test-Path -LiteralPath $localPythonRoot) {
        $versionFolders = Get-ChildItem -Path $localPythonRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending
        $candidates = foreach ($folder in $versionFolders) {
            $pythonPath = Join-Path $folder.FullName 'python.exe'
            if (Test-Path -LiteralPath $pythonPath) {
                $invocation = @($pythonPath)
                if (Test-PythonInvocationUsable -Invocation $invocation) {
                    Get-Item -LiteralPath $pythonPath
                }
            }
        }
        if ($candidates) {
            return @($candidates[0].FullName)
        }
    }

    $codexRuntimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $codexRuntimePython) {
        $candidate = @($codexRuntimePython)
        if (Test-PythonInvocationUsable -Invocation $candidate) {
            return $candidate
        }
    }

    throw "Python 3 was not found automatically. Use -PythonPath with your local python.exe path to run ./src/serve_ui.py."
}

$pythonInvocation = @(Get-PythonInvocation -ExplicitPythonPath $PythonPath)
$serveScript = Join-Path $PSScriptRoot 'serve_ui.py'

if ($CheckOnly) {
    Write-Host "Beacon BOT launcher located Python via:"
    Write-Host ($pythonInvocation -join ' ')
    Write-Host "Server script:"
    Write-Host $serveScript
    return
}

Write-Host "Starting Beacon BOT UI on http://$BindHost`:$Port"
Write-Host "Press Ctrl+C to stop the server."

if ($pythonInvocation.Count -eq 1) {
    & $pythonInvocation[0] $serveScript --host $BindHost --port $Port
    return
}

& $pythonInvocation[0] $pythonInvocation[1] $serveScript --host $BindHost --port $Port
