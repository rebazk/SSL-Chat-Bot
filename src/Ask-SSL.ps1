param(
    [Parameter(Mandatory = $true)][string]$Question,
    [int]$Top = 5,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'SslPipeline.ps1')

$projectRoot = Get-ProjectRoot
$chunksPath = Join-ProjectPath -RelativePath 'data/processed/chunks.jsonl'
$searchIndexPath = Get-SearchIndexCachePath

if (-not (Test-Path -LiteralPath $chunksPath)) {
    throw "Missing chunk corpus. Run ./src/Build-Corpus.ps1 first."
}

if ($Top -lt 1) { $Top = 1 }
if ($Top -gt 25) { $Top = 25 }

$searchIndex = Get-OrBuildChunkSearchIndex -ChunksPath $chunksPath -CachePath $searchIndexPath
$recallTop = [Math]::Min([Math]::Max($Top, 12), 30)
$results = Search-Chunks -Question $Question -SearchIndex $searchIndex -Top $recallTop
$answer = Get-AnswerFromResults -Question $Question -Results $results

if ($Json) {
    $topResults = @(
        $results |
            Select-Object -First $Top |
            ForEach-Object {
                $snippet = Get-DisplaySnippetForQuestion -Question $Question -Text ([string]$_.chunk.text) -MaxLength 240 -SourceType ([string]$_.chunk.source_type)

                [pscustomobject]@{
                    score       = $_.score
                    citation    = $_.chunk.citation
                    source_id   = $_.chunk.source_id
                    title       = $_.chunk.title
                    source_type = $_.chunk.source_type
                    source_url  = $_.chunk.source_url
                    page_number = $_.chunk.page_number
                    snippet     = $snippet
                }
            }
    )

    [pscustomobject]@{
        question        = $Question
        answer          = $answer.answer
        supported       = [bool]$answer.supported
        citations       = @($answer.citations)
        top_results     = $topResults
        generated_at    = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    } | ConvertTo-Json -Depth 8

    return
}

Write-Host "Question: $Question"
Write-Host ""
Write-Host "Answer:"
Write-Host $answer.answer
Write-Host ""
if ($answer.citations.Count -gt 0) {
    Write-Host "Citations:"
    foreach ($citation in $answer.citations) {
        Write-Host "- $citation"
    }
    Write-Host ""
}
Write-Host "Top Retrieval Results:"
foreach ($result in ($results | Select-Object -First $Top)) {
    Write-Host ("- [{0}] {1}" -f $result.score, $result.chunk.citation)
}
