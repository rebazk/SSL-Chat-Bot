param(
    [string]$QuestionsPath = 'eval/phase1_demo_questions.json',
    [string]$ResultsPath,
    [int]$SearchTop = 12,
    [int]$ShowTop = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'SslPipeline.ps1')

function Get-QuestionProperty {
    param(
        [Parameter(Mandatory = $true)]$Question,
        [Parameter(Mandatory = $true)][string]$Name,
        $DefaultValue
    )

    $property = $Question.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $DefaultValue
    }

    return $property.Value
}

function Convert-ToBoolean {
    param(
        $Value,
        [bool]$DefaultValue = $false
    )

    if ($null -eq $Value) {
        return $DefaultValue
    }

    if ($Value -is [bool]) {
        return [bool]$Value
    }

    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $DefaultValue
    }

    switch -Regex ($text.Trim().ToLowerInvariant()) {
        '^(true|yes|1)$' { return $true }
        '^(false|no|0)$' { return $false }
        default { return $DefaultValue }
    }
}

function Convert-ToStringArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [System.Array]) {
        return @($Value | ForEach-Object { [string]$_ })
    }

    return @([string]$Value)
}

function Get-DefaultResultsPath {
    param([Parameter(Mandatory = $true)][string]$ResolvedQuestionsPath)

    $fileName = [System.IO.Path]::GetFileNameWithoutExtension($ResolvedQuestionsPath)
    $relativePath = "eval/{0}_results.md" -f $fileName

    return (Join-ProjectPath -RelativePath $relativePath)
}

$chunksPath = Join-ProjectPath -RelativePath 'data/processed/chunks.jsonl'
$searchIndexPath = Get-SearchIndexCachePath
$resolvedQuestionsPath = Resolve-ProjectPath -Path $QuestionsPath
$resolvedResultsPath = if ([string]::IsNullOrWhiteSpace($ResultsPath)) {
    Get-DefaultResultsPath -ResolvedQuestionsPath $resolvedQuestionsPath
} else {
    Resolve-ProjectPath -Path $ResultsPath
}

if (-not (Test-Path -LiteralPath $chunksPath)) {
    throw "Missing chunk corpus. Run ./src/Build-Corpus.ps1 first."
}

if (-not (Test-Path -LiteralPath $resolvedQuestionsPath)) {
    throw "Missing question set: $resolvedQuestionsPath"
}

$searchIndex = Get-OrBuildChunkSearchIndex -ChunksPath $chunksPath -CachePath $searchIndexPath
$questions = Get-Content -LiteralPath $resolvedQuestionsPath -Raw -Encoding UTF8 | ConvertFrom-Json

$totalQuestions = 0
$expectedSupported = 0
$expectedUnsupported = 0
$actualSupported = 0
$citationRequiredCount = 0
$citationRequirementMetCount = 0
$supportExpectationMatchedCount = 0
$preferredSourceApplicableCount = 0
$preferredSourceHitCount = 0

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add('# Benchmark Results')
$lines.Add('')
$lines.Add(('Question set: `{0}`' -f $resolvedQuestionsPath))
$lines.Add(('Generated: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')))
$lines.Add('')

foreach ($question in $questions) {
    $id = [string](Get-QuestionProperty -Question $question -Name 'id' -DefaultValue 'question')
    $category = [string](Get-QuestionProperty -Question $question -Name 'category' -DefaultValue 'uncategorized')
    $questionType = [string](Get-QuestionProperty -Question $question -Name 'question_type' -DefaultValue '')
    $instituteWorkflow = [string](Get-QuestionProperty -Question $question -Name 'institute_workflow' -DefaultValue '')
    $questionText = Repair-DisplayText -Text ([string](Get-QuestionProperty -Question $question -Name 'question' -DefaultValue ''))
    $referenceAnswer = Repair-DisplayText -Text ([string](Get-QuestionProperty -Question $question -Name 'reference_answer' -DefaultValue ''))
    $expectedBehavior = Repair-DisplayText -Text ([string](Get-QuestionProperty -Question $question -Name 'expected_behavior' -DefaultValue ''))
    $expectedSupport = [string](Get-QuestionProperty -Question $question -Name 'expected_support' -DefaultValue 'supported')
    $mustIncludeCitation = Convert-ToBoolean -Value (Get-QuestionProperty -Question $question -Name 'must_include_citation' -DefaultValue $true) -DefaultValue $true
    $preferredSources = @(Convert-ToStringArray -Value (Get-QuestionProperty -Question $question -Name 'preferred_sources' -DefaultValue @()))

    $results = Search-Chunks -Question $questionText -SearchIndex $searchIndex -Top ([Math]::Max($SearchTop, $ShowTop))
    $answer = Get-AnswerFromResults -Question $questionText -Results $results

    $totalQuestions++
    if ($expectedSupport -eq 'unsupported') {
        $expectedUnsupported++
    } else {
        $expectedSupported++
    }

    if ($answer.supported) {
        $actualSupported++
    }

    $actualSupport = if ($answer.supported) { 'supported' } else { 'unsupported' }
    $supportExpectationMatched = ($actualSupport -eq $expectedSupport)
    if ($supportExpectationMatched) {
        $supportExpectationMatchedCount++
    }

    $citationRequirementMet = if ($mustIncludeCitation) {
        $citationRequiredCount++
        @($answer.citations).Count -gt 0
    } else {
        $true
    }

    if ($citationRequirementMet) {
        if ($mustIncludeCitation) {
            $citationRequirementMetCount++
        }
    }

    $preferredSourceHit = $null
    if ($preferredSources.Count -gt 0) {
        $preferredSourceApplicableCount++
        $preferredSourceHit = @(
            $results |
            Select-Object -First $ShowTop |
            Where-Object { $preferredSources -contains $_.chunk.source_id }
        ).Count -gt 0

        if ($preferredSourceHit) {
            $preferredSourceHitCount++
        }
    }

    $lines.Add(('## {0}: {1}' -f $id, $questionText))
    $lines.Add('')
    $lines.Add(('Category: `{0}`' -f $category))
    if (-not [string]::IsNullOrWhiteSpace($questionType)) {
        $lines.Add(('Question type: `{0}`' -f $questionType))
    }
    if (-not [string]::IsNullOrWhiteSpace($instituteWorkflow)) {
        $lines.Add(('Institute workflow: `{0}`' -f $instituteWorkflow))
    }
    $lines.Add(('Expected support: `{0}`' -f $expectedSupport))
    $lines.Add(('Answer support status: `{0}`' -f $actualSupport))
    $lines.Add(('Citation requirement met: `{0}`' -f $(if ($citationRequirementMet) { 'yes' } else { 'no' })))
    $lines.Add(('Support expectation matched: `{0}`' -f $(if ($supportExpectationMatched) { 'yes' } else { 'no' })))
    if ($preferredSources.Count -gt 0) {
        $lines.Add(('Preferred source hit in top {0}: `{1}`' -f $ShowTop, $(if ($preferredSourceHit) { 'yes' } else { 'no' })))
    }
    $lines.Add('')

    if (-not [string]::IsNullOrWhiteSpace($expectedBehavior)) {
        $lines.Add('Expected behavior:')
        $lines.Add($expectedBehavior)
        $lines.Add('')
    }

    if (-not [string]::IsNullOrWhiteSpace($referenceAnswer)) {
        $lines.Add('Reference answer:')
        $lines.Add($referenceAnswer)
        $lines.Add('')
    }

    $lines.Add('Answer:')
    $lines.Add((Repair-DisplayText -Text $answer.answer))
    $lines.Add('')

    if (@($answer.citations).Count -gt 0) {
        $lines.Add('Citations:')
        foreach ($citation in $answer.citations) {
            $lines.Add(('- {0}' -f (Repair-DisplayText -Text $citation)))
        }
        $lines.Add('')
    }

    $lines.Add('Top retrieval results:')
    foreach ($result in ($results | Select-Object -First $ShowTop)) {
        $excerpt = Normalize-Whitespace -Text $result.chunk.text
        if ($excerpt.Length -gt 220) {
            $excerpt = $excerpt.Substring(0, 220).Trim() + '...'
        }
        $lines.Add(('- [{0}] {1} [{2}]: {3}' -f $result.score, (Repair-DisplayText -Text $result.chunk.citation), $result.chunk.source_id, (Repair-DisplayText -Text $excerpt)))
    }
    $lines.Add('')
}

$lines.Insert(4, 'Evaluation summary:')
$lines.Insert(5, ('- Total questions: `{0}`' -f $totalQuestions))
$lines.Insert(6, ('- Expected supported: `{0}`' -f $expectedSupported))
$lines.Insert(7, ('- Expected unsupported: `{0}`' -f $expectedUnsupported))
$lines.Insert(8, ('- Answers marked supported: `{0}`' -f $actualSupported))
$lines.Insert(9, ('- Citation requirement satisfied: `{0}/{1}`' -f $citationRequirementMetCount, [Math]::Max($citationRequiredCount, 1)))
$lines.Insert(10, ('- Support expectation matched: `{0}/{1}`' -f $supportExpectationMatchedCount, $totalQuestions))
if ($preferredSourceApplicableCount -gt 0) {
    $lines.Insert(11, ('- Preferred source hit in top {0}: `{1}/{2}`' -f $ShowTop, $preferredSourceHitCount, $preferredSourceApplicableCount))
    $lines.Insert(12, '')
} else {
    $lines.Insert(11, '')
}

$resultsDirectory = Split-Path -Parent $resolvedResultsPath
Ensure-Directory -Path $resultsDirectory
Set-Content -LiteralPath $resolvedResultsPath -Value $lines -Encoding UTF8
Write-Host "Wrote benchmark results to $resolvedResultsPath"
