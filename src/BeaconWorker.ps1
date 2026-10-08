Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'SslPipeline.ps1')

$projectRoot = Get-ProjectRoot
$chunksPath = Join-ProjectPath -RelativePath 'data/processed/chunks.jsonl'
$searchIndexPath = Get-SearchIndexCachePath

if (-not (Test-Path -LiteralPath $chunksPath)) {
    throw "Missing chunk corpus. Run ./src/Build-Corpus.ps1 first."
}

$searchIndex = Get-OrBuildChunkSearchIndex -ChunksPath $chunksPath -CachePath $searchIndexPath

function Get-SafePublicSourceUrl {
    param([AllowNull()][string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return ''
    }

    try {
        $u = [uri]$Url.Trim()
        if (($u.Scheme -eq 'http' -or $u.Scheme -eq 'https') -and -not [string]::IsNullOrWhiteSpace($u.Host)) {
            return $Url.Trim()
        }
    } catch {
    }

    return ''
}

function ConvertTo-JsonLineSafe {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [int]$Depth = 8
    )

    try {
        $json = $Value | ConvertTo-Json -Depth $Depth -Compress
        $null = $json | ConvertFrom-Json -ErrorAction Stop
        return $json
    } catch {
        if ($Value.PSObject.Properties.Name -contains 'question') {
            $safePayload = [pscustomobject]@{
                question     = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$Value.question))
                answer       = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$Value.answer))
                supported    = [bool]$Value.supported
                citations    = @(
                    @($Value.citations) |
                        ForEach-Object { Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$_)) } |
                        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
                )
                top_results  = @(
                    @($Value.top_results) |
                        ForEach-Object {
                            [pscustomobject]@{
                                score       = $_.score
                                citation    = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$_.citation))
                                source_id   = Normalize-Whitespace -Text ([string]$_.source_id)
                                title       = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$_.title))
                                source_type = Normalize-Whitespace -Text ([string]$_.source_type)
                                source_url  = (Get-SafePublicSourceUrl -Url ([string]$_.source_url))
                                page_number = $_.page_number
                                snippet     = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$_.snippet))
                            }
                        }
                )
                generated_at = Normalize-Whitespace -Text ([string]$Value.generated_at)
            }

            try {
                $json = $safePayload | ConvertTo-Json -Depth $Depth -Compress
                $null = $json | ConvertFrom-Json -ErrorAction Stop
                return $json
            } catch {
            }
        }

        return (([pscustomobject]@{
                    error = 'Beacon BOT backend could not serialize a valid JSON response.'
                }) | ConvertTo-Json -Compress)
    }
}

function Get-TopResultPayload {
    param(
        [Parameter(Mandatory = $true)]$Results,
        [Parameter(Mandatory = $true)][string]$Question,
        [Parameter(Mandatory = $true)][int]$Top
    )

    return @(
        $Results |
            Select-Object -First $Top |
            ForEach-Object {
                $snippet = Get-DisplaySnippetForQuestion -Question $Question -Text ([string]$_.chunk.text) -MaxLength 240 -SourceType ([string]$_.chunk.source_type)

                [pscustomobject]@{
                    score       = $_.score
                    citation    = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$_.chunk.citation))
                    source_id   = $_.chunk.source_id
                    title       = Repair-DisplayText -Text (Normalize-Whitespace -Text ([string]$_.chunk.title))
                    source_type = $_.chunk.source_type
                    source_url  = (Get-SafePublicSourceUrl -Url ([string]$_.chunk.source_url))
                    page_number = $_.chunk.page_number
                    snippet     = $snippet
                }
            }
    )
}

while ($true) {
    $requestLine = [Console]::In.ReadLine()
    if ($null -eq $requestLine) {
        break
    }

    if ([string]::IsNullOrWhiteSpace($requestLine)) {
        continue
    }

    try {
        $request = $requestLine | ConvertFrom-Json
        $question = [string]$request.question
        $top = 5
        if ($null -ne $request.top -and "$($request.top)".Trim().Length -gt 0) {
            $top = [int]$request.top
        }

        if ($top -lt 1) { $top = 1 }
        if ($top -gt 25) { $top = 25 }

        if ([string]::IsNullOrWhiteSpace($question)) {
            throw "A non-empty question is required."
        }

        $recallTop = [Math]::Min([Math]::Max($top, 12), 30)
        $results = Search-Chunks -Question $question -SearchIndex $searchIndex -Top $recallTop
        $answer = Get-AnswerFromResults -Question $question -Results $results

        $payload = [pscustomobject]@{
            question     = $question
            answer       = $answer.answer
            supported    = [bool]$answer.supported
            citations    = @($answer.citations)
            top_results  = (Get-TopResultPayload -Results $results -Question $question -Top $top)
            generated_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        }

        [Console]::Out.WriteLine((ConvertTo-JsonLineSafe -Value $payload -Depth 8))
    } catch {
        $errorPayload = [pscustomobject]@{
            error = $_.Exception.Message
        }

        [Console]::Out.WriteLine((ConvertTo-JsonLineSafe -Value $errorPayload))
    }
}
