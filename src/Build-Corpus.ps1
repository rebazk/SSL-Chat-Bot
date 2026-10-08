Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'SslPipeline.ps1')

$projectRoot = Get-ProjectRoot
$manifestPath = Join-ProjectPath -RelativePath 'data/processed/sources_manifest.csv'
$documentsPath = Join-ProjectPath -RelativePath 'data/processed/documents.jsonl'
$chunksPath = Join-ProjectPath -RelativePath 'data/processed/chunks.jsonl'
$searchIndexPath = Get-SearchIndexCachePath

$manifest = Import-Csv -LiteralPath $manifestPath
$documents = New-Object System.Collections.Generic.List[object]

foreach ($row in $manifest) {
    $document = Get-SourceDocument -SourceRow $row
    if ($null -eq $document) { continue }
    $documents.Add($document)
}

$chunks = Get-ChunkRecords -Documents $documents

Write-JsonLines -Items $documents -Path $documentsPath
Write-JsonLines -Items $chunks -Path $chunksPath
$searchIndex = Get-ChunkSearchIndex -Chunks $chunks
Save-ChunkSearchIndexCache -SearchIndex $searchIndex -ChunksPath $chunksPath -CachePath $searchIndexPath | Out-Null

Write-Host "Wrote $($documents.Count) documents to $documentsPath"
Write-Host "Wrote $($chunks.Count) chunks to $chunksPath"
Write-Host "Wrote cached search index to $searchIndexPath"
