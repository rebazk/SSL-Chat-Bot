# Project Metrics Snapshot

This file summarizes the current project status after the Phase 1 baseline and the broader 50-question coverage expansion. These are project-status metrics, not assigned rubric grades.

## Corpus Metrics

- Indexed sources: `20`
- Indexed PDFs: `15`
- Indexed webpage snapshots: `5`
- Exact duplicates skipped: `1`
- Searchable chunks: `2354`

Sources:

- [sources_manifest.csv](../data/processed/sources_manifest.csv)
- [documents.jsonl](../data/processed/documents.jsonl)
- [chunks.jsonl](../data/processed/chunks.jsonl)

## Official 10-Question Benchmark

- Total questions: `10`
- Expected supported: `10`
- Expected unsupported: `0`
- Answers marked supported: `10`
- Citation requirement satisfied: `10/10`
- Support expectation matched: `10/10`
- Preferred source hit in top 5: `10/10`

Sources:

- [phase1_demo_questions.json](phase1_demo_questions.json)
- [phase1_demo_answers.md](phase1_demo_answers.md)
- [phase1_demo_questions_results.md](phase1_demo_questions_results.md)

## 50-Question Coverage Benchmark

- Total questions: `50`
- Expected supported: `49`
- Expected unsupported: `1`
- Answers marked supported: `49`
- Citation requirement satisfied: `49/49`
- Support expectation matched: `50/50`
- Preferred source hit in top 5: `50/50`

Sources:

- [question_coverage_50.json](question_coverage_50.json)
- [question_coverage_50_summary.md](question_coverage_50_summary.md)
- [question_coverage_50_results.md](question_coverage_50_results.md)

## All-PDF Coverage Benchmark

- Total questions: `53`
- Expected supported: `52`
- Expected unsupported: `1`
- Answers marked supported: `52`
- Citation requirement satisfied: `52/52`
- Support expectation matched: `53/53`
- Preferred source hit in top 5: `53/53`

Sources:

- [question_coverage_all_pdfs.json](question_coverage_all_pdfs.json)
- [question_coverage_all_pdfs_results.md](question_coverage_all_pdfs_results.md)

## Responsible-AI Evaluation Checks

The benchmark runner now checks the three behaviors emphasized in the project outline:

- answers should be supported by retrieved evidence
- sources should be clearly cited
- the system should refuse when reliable information is unavailable

In practical terms, the results files report:

- expected supported vs unsupported status
- actual answer/refusal status
- whether citations were present when required
- whether preferred sources appeared in the top retrieval results

Implementation source:

- [Run-Demo.ps1](../src/Run-Demo.ps1)

## Current Quality Notes

- Direct factual and report-specific questions are the strongest category.
- Community-report retrieval improved materially after targeted source and evidence boosts for the `Community-Led` report.
- Broad synthesis prompts are still weaker than direct factual lookup.
- Some PDF extraction noise remains, even when the answer is grounded correctly.
- Live webpage refresh exists, but local snapshots remain the reliable fallback when public-site requests are reset.
- The current benchmark set is back to full preferred-source coverage on the official 10, the broader 50-question set, and the all-PDF set.
- The migration-paper citation gap was resolved by indexing a stable fallback extraction for sparse PDF text during search-index construction.
- The annual-budget refusal behavior remains correct and now aligns with the benchmark's preferred-source expectations.

Sources:

- [question_coverage_50_results.md](question_coverage_50_results.md)
- [phase1_demo_questions_results.md](phase1_demo_questions_results.md)
- [failure_analysis.md](../docs/failure_analysis.md)

